"""Parquet writer and chunked persistence utilities."""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import polars as pl
from rich.console import Console

console = Console()


def get_table_parquet_paths(data_dir: Path, table_name: str) -> list[Path]:
    """Return sorted list of Parquet file paths for a table (single file or chunked directory)."""
    single_file = data_dir / f"{table_name}.parquet"
    if single_file.exists():
        return [single_file]
    chunk_dir = data_dir / table_name
    if chunk_dir.is_dir():
        return sorted(chunk_dir.glob("part-*.parquet"))
    return []


def read_table_parquet(data_dir: Path, table_name: str) -> pl.DataFrame | None:
    """Read a table from either a single .parquet file or a chunked directory."""
    single_file = data_dir / f"{table_name}.parquet"
    if single_file.exists():
        return pl.read_parquet(single_file)
    chunk_dir = data_dir / table_name
    if chunk_dir.is_dir():
        parts = sorted(chunk_dir.glob("part-*.parquet"))
        if parts:
            return pl.read_parquet(chunk_dir / "*.parquet")
    return None


def write_parquet(
    df: pl.DataFrame,
    output_dir: Path,
    filename: str,
    *,
    compression: str = "snappy",
    chunk_size: int | None = None,
) -> dict[str, Any]:
    """Write a Polars DataFrame to Parquet (single file or chunked parts) and return stats."""
    output_dir.mkdir(parents=True, exist_ok=True)
    table_name = filename.replace(".parquet", "")

    # If chunk_size is set and DataFrame exceeds it, slice and write as chunked directory
    if chunk_size and chunk_size > 0 and df.height > chunk_size:
        writer = ChunkedParquetWriter(output_dir, table_name, compression=compression)
        for offset in range(0, df.height, chunk_size):
            writer.write_chunk(df.slice(offset, chunk_size))
        return writer.finalize()

    filepath = output_dir / filename
    df.write_parquet(filepath, compression=compression)

    size_bytes = filepath.stat().st_size
    size_mb = size_bytes / (1024 * 1024)

    console.print(
        f"  ✓ [green]{filename}[/green] — "
        f"{df.height:,} rows, {size_mb:.1f} MB"
    )

    return {
        "filename": filename,
        "table_name": table_name,
        "rows": df.height,
        "columns": df.width,
        "size_bytes": size_bytes,
        "size_mb": round(size_mb, 2),
        "chunks": 1,
        "is_chunked": False,
    }


class ChunkedParquetWriter:
    """Streams DataFrame chunks to disk as Parquet part files with bounded memory."""

    def __init__(
        self,
        output_dir: Path,
        table_name: str,
        *,
        compression: str = "snappy",
    ) -> None:
        self.output_dir = output_dir
        self.table_name = table_name
        self.compression = compression
        self.chunk_dir = output_dir / table_name
        if self.chunk_dir.exists():
            shutil.rmtree(self.chunk_dir)
        self.chunk_dir.mkdir(parents=True, exist_ok=True)

        self.chunk_idx = 0
        self.total_rows = 0
        self.total_bytes = 0
        self.columns = 0

    def write_chunk(self, df: pl.DataFrame) -> None:
        """Persist a single chunk DataFrame to part-NNNNN.parquet."""
        if df.height == 0:
            return
        self.columns = df.width
        part_path = self.chunk_dir / f"part-{self.chunk_idx:05d}.parquet"
        df.write_parquet(part_path, compression=self.compression)
        self.total_rows += df.height
        self.total_bytes += part_path.stat().st_size
        self.chunk_idx += 1

    def finalize(self) -> dict[str, Any]:
        """Finalize chunked write; collapse to single file if only 1 chunk was written."""
        if self.chunk_idx == 1:
            single_src = self.chunk_dir / "part-00000.parquet"
            single_dst = self.output_dir / f"{self.table_name}.parquet"
            shutil.move(str(single_src), str(single_dst))
            shutil.rmtree(self.chunk_dir, ignore_errors=True)
            size_mb = self.total_bytes / (1024 * 1024)
            console.print(
                f"  ✓ [green]{self.table_name}.parquet[/green] — "
                f"{self.total_rows:,} rows, {size_mb:.1f} MB"
            )
            return {
                "filename": f"{self.table_name}.parquet",
                "table_name": self.table_name,
                "rows": self.total_rows,
                "columns": self.columns,
                "size_bytes": self.total_bytes,
                "size_mb": round(size_mb, 2),
                "chunks": 1,
                "is_chunked": False,
            }

        size_mb = self.total_bytes / (1024 * 1024)
        console.print(
            f"  ✓ [green]{self.table_name}/[/green] ({self.chunk_idx} chunks) — "
            f"{self.total_rows:,} rows, {size_mb:.1f} MB"
        )
        return {
            "filename": f"{self.table_name}/",
            "table_name": self.table_name,
            "rows": self.total_rows,
            "columns": self.columns,
            "size_bytes": self.total_bytes,
            "size_mb": round(size_mb, 2),
            "chunks": self.chunk_idx,
            "is_chunked": True,
        }


def write_manifest(
    output_dir: Path,
    tier_name: str,
    seed: int,
    date_range: dict[str, str],
    file_stats: list[dict[str, Any]],
    generation_time: float,
    fraud_rate: float,
    is_incremental: bool = False,
    incremental_state: dict[str, Any] | None = None,
    regions: list[str] | None = None,
    chunk_size: int | None = None,
) -> None:
    """Write the _manifest.json file."""

    row_counts = {}
    file_sizes_mb = {}
    chunk_counts = {}
    for fs in file_stats:
        name = fs.get("table_name") or fs["filename"].replace(".parquet", "").rstrip("/")
        row_counts[name] = fs["rows"]
        file_sizes_mb[name] = fs["size_mb"]
        if fs.get("is_chunked"):
            chunk_counts[name] = fs.get("chunks", 1)

    manifest: dict[str, Any] = {
        "generator_version": "1.1.0",
        "tier": tier_name,
        "seed": seed,
        "generated_at": datetime.now().isoformat(),
        "date_range": date_range,
        "is_incremental": is_incremental,
        "fraud_rate": fraud_rate,
        "regions": regions or ["US"],
        "chunk_size": chunk_size,
        "row_counts": row_counts,
        "file_sizes_mb": file_sizes_mb,
        "generation_time_seconds": round(generation_time, 2),
    }

    if chunk_counts:
        manifest["chunk_counts"] = chunk_counts

    if incremental_state:
        manifest["incremental_state"] = incremental_state

    manifest_path = output_dir / "_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2, default=str)

    console.print(f"  ✓ [blue]_manifest.json[/blue]")
