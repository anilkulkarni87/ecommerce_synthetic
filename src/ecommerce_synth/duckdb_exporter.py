"""DuckDB export module (backward-compatible wrapper).

Exports generated Parquet tables into a standalone, portable DuckDB database
file with indexed tables and views for instant zero-setup SQL analytics.
"""

from __future__ import annotations

from pathlib import Path

from .exporters.base import ExportConfig
from .exporters.duckdb import DuckDBExporter


def export_to_duckdb(
    data_dir: Path | str,
    output_db_path: Path | str | None = None,
    create_views: bool = False,
) -> Path:
    """Export Parquet datasets to a self-contained DuckDB database.

    Args:
        data_dir: Path to directory containing the .parquet files.
        output_db_path: Path to target .duckdb file. If None, saves as
            'ecommerce.duckdb' inside data_dir.
        create_views: Legacy flag; analytical views are created automatically.

    Returns:
        Path to the created DuckDB database file.
    """
    config = ExportConfig(
        target="duckdb",
        data_dir=data_dir,
        database=str(output_db_path) if output_db_path else None,
        create_views=True,
    )
    exporter = DuckDBExporter(config)
    result = exporter.export()
    return Path(result.destination)
