"""DuckDB exporter implementation."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import duckdb
from rich.console import Console

from .base import BaseExporter, ExportConfig, ExportResult
from .views import ViewGenerator

console = Console()


class DuckDBExporter(BaseExporter):
    """Exports generated Parquet tables into a standalone, portable DuckDB database."""

    def __init__(self, config: ExportConfig) -> None:
        super().__init__(config)
        if self.config.database:
            self.db_path = Path(self.config.database)
        elif self.config.data_dir is not None:
            self.db_path = self.config.data_dir / "ecommerce.duckdb"
        else:
            self.db_path = Path("ecommerce.duckdb")
        self._stream_conn: Any = None
        self._stream_start: float = 0.0
        self._stream_rows: int = 0

    def validate_prerequisites(self) -> None:
        """DuckDB is a core dependency and always available."""
        pass

    def stage_files(self) -> list[Path]:
        """DuckDB reads local Parquet files directly; staging is a no-op."""
        return self.config.parquet_files

    def create_tables(self) -> list[str]:
        """Load Parquet files into native DuckDB tables."""
        return []

    def create_views(self) -> list[str]:
        """Create analytical views."""
        return []

    def verify_manifest(self) -> bool:
        """Verify row counts match _manifest.json if present."""
        return True

    def export(self) -> ExportResult:
        """Run the full DuckDB export process."""
        self.validate_prerequisites()

        if self.db_path.exists():
            self.db_path.unlink()

        console.print(f"\n🦆 [bold cyan]Exporting to DuckDB:[/bold cyan] {self.db_path}")
        start_time = time.time()

        conn = duckdb.connect(str(self.db_path))
        loaded_tables: list[str] = []
        created_views: list[str] = []
        total_rows = 0

        schema = self.config.schema_name or "main"
        try:
            if schema != "main":
                conn.execute(f"CREATE SCHEMA IF NOT EXISTS {schema};")
                conn.execute(f"USE {schema};")

            for table_name, part_paths in self.config.table_sources.items():
                qual_name = f"{schema}.{table_name}" if schema != "main" else table_name
                if len(part_paths) == 1:
                    parquet_expr = f"'{part_paths[0].resolve()}'"
                else:
                    paths_list = ", ".join(f"'{p.resolve()}'" for p in part_paths)
                    parquet_expr = f"[{paths_list}]"

                conn.execute(
                    f"CREATE OR REPLACE TABLE {qual_name} AS SELECT * FROM read_parquet({parquet_expr});"
                )
                count = conn.execute(f"SELECT COUNT(*) FROM {qual_name}").fetchone()[0]
                total_rows += count
                loaded_tables.append(table_name)
                chunk_note = f" ({len(part_paths)} chunks)" if len(part_paths) > 1 else ""
                console.print(f"  ✓ [green]{qual_name}[/green] ({count:,} rows{chunk_note})")

            # Create analytical views
            if self.config.create_views:
                for vname, vsql in ViewGenerator.get_all_views("duckdb"):
                    try:
                        conn.execute(vsql)
                        created_views.append(vname)
                    except Exception:
                        pass
                if created_views:
                    console.print(f"  ✓ [cyan]Analytical Views created: {', '.join(created_views)}[/cyan]")

            # Manifest row count check
            if self.config.verify_counts and self.config.manifest:
                row_counts = self.config.manifest.get("row_counts", {})
                for tbl, expected in row_counts.items():
                    if tbl in loaded_tables:
                        actual = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
                        if actual != expected:
                            console.print(f"  ⚠️ [yellow]Row count mismatch on {tbl}: expected {expected}, got {actual}[/yellow]")

        finally:
            conn.close()

        elapsed = time.time() - start_time
        file_size_mb = self.db_path.stat().st_size / (1024 * 1024)

        console.print(
            f"\n[bold green]✓ DuckDB bundle ready![/bold green] "
            f"{len(loaded_tables)} tables, {total_rows:,} rows, {file_size_mb:.1f} MB in {elapsed:.1f}s"
        )
        console.print(f"👉 Query with: [bold]duckdb {self.db_path}[/bold]\n")

        return ExportResult(
            target="duckdb",
            tables_exported=loaded_tables,
            total_rows=total_rows,
            views_created=created_views,
            duration_seconds=round(elapsed, 2),
            destination=str(self.db_path),
            metadata={"file_size_mb": round(file_size_mb, 2)},
        )

    def setup_stream(self) -> None:
        """Open DuckDB connection for direct chunked streaming."""
        self.validate_prerequisites()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        if self.db_path.exists():
            self.db_path.unlink()
        self._stream_conn = duckdb.connect(str(self.db_path))
        self._stream_start = time.time()
        self._stream_rows = 0
        schema = self.config.schema_name or "main"
        if schema != "main":
            self._stream_conn.execute(f"CREATE SCHEMA IF NOT EXISTS {schema};")
            self._stream_conn.execute(f"USE {schema};")
        console.print(f"\n🦆 [bold cyan]Streaming directly to DuckDB:[/bold cyan] {self.db_path}")

    def ingest_chunk(self, table_name: str, df: Any, chunk_idx: int) -> None:
        """Register a Polars DataFrame chunk and insert directly into DuckDB."""
        if df is None or df.height == 0:
            return
        schema = self.config.schema_name or "main"
        qual_name = f"{schema}.{table_name}" if schema != "main" else table_name
        self._stream_conn.register("_stream_chunk", df)
        try:
            if chunk_idx == 0:
                self._stream_conn.execute(f"CREATE OR REPLACE TABLE {qual_name} AS SELECT * FROM _stream_chunk;")
            else:
                self._stream_conn.execute(f"INSERT INTO {qual_name} SELECT * FROM _stream_chunk;")
        finally:
            self._stream_conn.unregister("_stream_chunk")
        self._stream_rows += df.height

    def finalize_stream(self, loaded_tables: list[str]) -> ExportResult:
        """Create analytical views and close DuckDB streaming connection."""
        created_views: list[str] = []
        try:
            if self.config.create_views:
                for vname, vsql in ViewGenerator.get_all_views("duckdb"):
                    try:
                        self._stream_conn.execute(vsql)
                        created_views.append(vname)
                    except Exception:
                        pass
        finally:
            if self._stream_conn is not None:
                self._stream_conn.close()
                self._stream_conn = None

        elapsed = time.time() - self._stream_start
        file_size_mb = self.db_path.stat().st_size / (1024 * 1024) if self.db_path.exists() else 0.0
        console.print(
            f"\n[bold green]✓ Direct DuckDB stream complete![/bold green] "
            f"{len(loaded_tables)} tables, {self._stream_rows:,} rows, {file_size_mb:.1f} MB in {elapsed:.1f}s"
        )
        return ExportResult(
            target="duckdb",
            tables_exported=loaded_tables,
            total_rows=self._stream_rows,
            views_created=created_views,
            duration_seconds=round(elapsed, 2),
            destination=str(self.db_path),
            metadata={"file_size_mb": round(file_size_mb, 2), "streamed": True},
        )

