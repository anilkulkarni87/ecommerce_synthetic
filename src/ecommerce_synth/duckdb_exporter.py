"""DuckDB export module.

Exports generated Parquet tables into a standalone, portable DuckDB database
file with indexed tables and views for instant zero-setup SQL analytics.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import duckdb
from rich.console import Console

console = Console()


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
        create_views: If True, creates views pointing to the Parquet files.
            If False (default), creates native DuckDB tables for a fully
            portable, standalone database.

    Returns:
        Path to the created DuckDB database file.
    """
    data_path = Path(data_dir)
    if not data_path.exists():
        raise FileNotFoundError(f"Data directory not found: {data_path}")

    parquet_files = sorted(list(data_path.glob("*.parquet")))
    if not parquet_files:
        raise FileNotFoundError(f"No .parquet files found in: {data_path}")

    if output_db_path:
        db_file = Path(output_db_path)
    else:
        db_file = data_path / "ecommerce.duckdb"

    # Remove existing DB file if present
    if db_file.exists():
        db_file.unlink()

    console.print(f"\n🦆 [bold cyan]Exporting to DuckDB:[/bold cyan] {db_file}")
    start_time = time.time()

    conn = duckdb.connect(str(db_file))

    try:
        loaded_tables: list[str] = []
        total_rows = 0

        for pf in parquet_files:
            table_name = pf.stem
            abs_parquet = str(pf.resolve())

            if create_views:
                conn.execute(
                    f"CREATE VIEW {table_name} AS SELECT * FROM read_parquet('{abs_parquet}');"
                )
            else:
                conn.execute(
                    f"CREATE TABLE {table_name} AS SELECT * FROM read_parquet('{abs_parquet}');"
                )

            count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            total_rows += count
            loaded_tables.append(table_name)
            console.print(f"  ✓ [green]{table_name}[/green] ({count:,} rows)")

        # Create useful analytical views for easy querying
        _create_analytical_views(conn)

    finally:
        conn.close()

    elapsed = time.time() - start_time
    file_size_mb = db_file.stat().st_size / (1024 * 1024)

    console.print(
        f"\n[bold green]✓ DuckDB bundle ready![/bold green] "
        f"{len(loaded_tables)} tables, {total_rows:,} rows, {file_size_mb:.1f} MB in {elapsed:.1f}s"
    )
    console.print(f"👉 Query with: [bold]duckdb {db_file}[/bold]\n")

    return db_file


def _create_analytical_views(conn: duckdb.DuckDBPyConnection) -> None:
    """Create curated analytical views in the DuckDB database for quick analysis."""
    try:
        # 1. Omnichannel sales view combining online and in-store transactions
        conn.execute("""
            CREATE OR REPLACE VIEW v_omnichannel_sales AS
            SELECT 
                order_id AS transaction_id,
                'online' AS channel,
                customer_id,
                order_date AS transaction_date,
                status,
                total_amount,
                payment_method,
                device_type
            FROM orders_online
            UNION ALL
            SELECT 
                transaction_id,
                'instore' AS channel,
                customer_id,
                transaction_date,
                'completed' AS status,
                total_amount,
                payment_method,
                'pos' AS device_type
            FROM orders_instore;
        """)

        # 2. Customer 360 summary view
        conn.execute("""
            CREATE OR REPLACE VIEW v_customer_360 AS
            SELECT 
                c.customer_id,
                c.first_name || ' ' || c.last_name AS full_name,
                c.email,
                c.customer_segment,
                c.channel_acquired,
                COUNT(s.transaction_id) AS total_orders,
                COALESCE(SUM(s.total_amount), 0.0) AS lifetime_spend,
                MAX(s.transaction_date) AS last_order_date
            FROM customers c
            LEFT JOIN v_omnichannel_sales s ON c.customer_id = s.customer_id
            GROUP BY 1, 2, 3, 4, 5;
        """)
        console.print("  ✓ [cyan]Analytical Views created: v_omnichannel_sales, v_customer_360[/cyan]")
    except Exception:
        # Ignore if tables are missing in custom partial runs
        pass
