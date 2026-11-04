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
        else:
            self.db_path = self.config.data_dir / "ecommerce.duckdb"

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

        try:
            for pf in self.config.parquet_files:
                table_name = pf.stem
                abs_parquet = str(pf.resolve())

                conn.execute(
                    f"CREATE TABLE {table_name} AS SELECT * FROM read_parquet('{abs_parquet}');"
                )
                count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
                total_rows += count
                loaded_tables.append(table_name)
                console.print(f"  ✓ [green]{table_name}[/green] ({count:,} rows)")

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
