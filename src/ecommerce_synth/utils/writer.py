"""Parquet writer utilities."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import polars as pl
from rich.console import Console

console = Console()


def write_parquet(
    df: pl.DataFrame,
    output_dir: Path,
    filename: str,
    *,
    compression: str = "snappy",
) -> dict[str, Any]:
    """Write a Polars DataFrame to Parquet and return stats."""

    output_dir.mkdir(parents=True, exist_ok=True)
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
        "rows": df.height,
        "columns": df.width,
        "size_bytes": size_bytes,
        "size_mb": round(size_mb, 2),
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
) -> None:
    """Write the _manifest.json file."""

    row_counts = {}
    file_sizes_mb = {}
    for fs in file_stats:
        name = fs["filename"].replace(".parquet", "")
        row_counts[name] = fs["rows"]
        file_sizes_mb[name] = fs["size_mb"]

    manifest = {
        "generator_version": "1.0.0",
        "tier": tier_name,
        "seed": seed,
        "generated_at": datetime.now().isoformat(),
        "date_range": date_range,
        "is_incremental": is_incremental,
        "fraud_rate": fraud_rate,
        "row_counts": row_counts,
        "file_sizes_mb": file_sizes_mb,
        "generation_time_seconds": round(generation_time, 2),
    }

    if incremental_state:
        manifest["incremental_state"] = incremental_state

    manifest_path = output_dir / "_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2, default=str)

    console.print(f"  ✓ [blue]_manifest.json[/blue]")
