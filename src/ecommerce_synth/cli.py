"""CLI entry point for the Ecommerce Synthetic Data Generator."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from . import __version__
from .config import load_config
from .incremental import IncrementalGenerator
from .orchestrator import Orchestrator

app = typer.Typer(
    name="ecommerce-synth",
    help="🛒 Realistic Ecommerce Synthetic Data Generator",
    add_completion=False,
)
console = Console()


@app.command()
def generate(
    tier: str = typer.Option("small", help="Volume tier: small, medium, large, xl"),
    output: str = typer.Option(None, help="Output directory path"),
    seed: int = typer.Option(42, help="Random seed for reproducibility"),
    fraud_rate: float = typer.Option(None, help="Fraud injection rate (0.0-1.0)"),
    only: str = typer.Option(None, help="Comma-separated list of domains to generate"),
    incremental: str = typer.Option(None, "--incremental", help="Path to existing dataset directory for incremental generation"),
    days: int = typer.Option(1, "--days", help="Number of days of incremental data to generate"),
    daily_batches: bool = typer.Option(False, "--daily-batches", help="Simulate sequential daily batches"),
    duckdb: bool = typer.Option(False, "--duckdb", help="Also export all tables to a standalone ecommerce.duckdb database"),
    export_target: str = typer.Option(None, "--export", "-e", help="Auto-export to target: duckdb, databricks, snowflake, bigquery"),
    catalog: str = typer.Option(None, "--catalog", help="Target catalog/database name"),
    schema: str = typer.Option(None, "--schema", "-s", help="Target schema/dataset name"),
    warehouse: str = typer.Option(None, "--warehouse", "-w", help="Target warehouse ID/name"),
    project: str = typer.Option(None, "--project", "-p", help="Target GCP project ID for BigQuery"),
    dataset: str = typer.Option(None, "--dataset", "-d", help="Target BigQuery dataset name"),
) -> None:
    """Generate synthetic ecommerce data at the specified volume tier."""

    console.print(f"\n🛒 [bold]Ecommerce Synthetic Data Generator[/bold] v{__version__}\n")

    target_dir = None

    if incremental:
        inc_gen = IncrementalGenerator(
            base_dir=incremental,
            days=days,
            daily_batches=daily_batches,
            seed=seed,
        )
        inc_gen.run()
        target_dir = Path(incremental)
    else:
        config = load_config(
            tier_name=tier,
            seed=seed,
            output_dir=output,
            fraud_rate=fraud_rate,
        )

        only_list = [s.strip() for s in only.split(",")] if only else None

        orchestrator = Orchestrator(config)
        orchestrator.run(only=only_list)
        target_dir = config.output_dir

    # Handle post-generation exports
    target_to_export = export_target or ("duckdb" if duckdb else None)
    if target_to_export and target_dir:
        export_cmd(
            data_dir=str(target_dir),
            target=target_to_export,
            catalog=catalog,
            schema=schema,
            warehouse=warehouse,
            project=project,
            dataset=dataset,
        )


@app.command()
def info(
    tier: str = typer.Option("small", help="Volume tier to show info for"),
) -> None:
    """Display information about a volume tier."""

    config = load_config(tier_name=tier)

    table = Table(title=f"Tier: {tier.upper()}")
    table.add_column("Domain", style="cyan")
    table.add_column("Target Rows", justify="right", style="green")

    table.add_row("Customers", f"{config.tier.customers:,}")
    table.add_row("Online Orders", f"{config.tier.online_orders:,}")
    table.add_row("In-Store Transactions", f"{config.tier.instore_transactions:,}")
    table.add_row("Clickstream Events", f"{config.tier.clickstream_events:,}")
    table.add_row("Emails Sent", f"{config.tier.emails_sent:,}")
    table.add_row("Loyalty Members", f"{config.tier.loyalty_members:,}")
    table.add_row("Support Tickets", f"{config.tier.support_tickets:,}")
    table.add_row("A/B Experiments", f"{config.tier.ab_experiments:,}")
    table.add_row("Products (fixed)", f"{config.product_count:,}")
    table.add_row("Stores (fixed)", f"{config.store_count:,}")

    console.print(table)


@app.command()
def validate(
    data_dir: str = typer.Argument(help="Path to generated data directory"),
) -> None:
    """Validate referential integrity across all generated Parquet files."""
    import polars as pl

    path = Path(data_dir)
    console.print(f"\n🔍 [bold]Validating referential integrity in:[/bold] {path}\n")

    manifest_file = path / "_manifest.json"
    if not manifest_file.exists():
        console.print("[red]Error: _manifest.json not found in output directory[/red]")
        raise typer.Exit(1)

    with open(manifest_file) as f:
        manifest = json.load(f)

    console.print(f"  Tier: [cyan]{manifest.get('tier', 'unknown')}[/cyan]")
    console.print(f"  Generated: {manifest.get('generated_at', 'unknown')}")
    console.print(f"  Seed: {manifest.get('seed', 'unknown')}\n")

    errors: list[str] = []
    checks_passed = 0

    def check(name: str, fn) -> None:
        nonlocal checks_passed
        try:
            passed, detail = fn()
            if passed:
                checks_passed += 1
                console.print(f"  ✓ [green]{name}[/green]: {detail}")
            else:
                errors.append(f"FAIL: {name} — {detail}")
                console.print(f"  ✗ [red]{name}[/red]: {detail}")
        except Exception as e:
            errors.append(f"ERROR: {name} — {e}")
            console.print(f"  ✗ [red]{name}[/red]: {e}")

    # Load tables helper
    tables: dict[str, pl.DataFrame] = {}

    def get_table(name: str) -> pl.DataFrame | None:
        if name not in tables:
            f = path / f"{name}.parquet"
            if f.exists():
                tables[name] = pl.read_parquet(f)
            else:
                return None
        return tables[name]

    # --- Customer & Address Checks ---
    def check_addresses_customer_fk():
        addr = get_table("addresses")
        cust = get_table("customers")
        if addr is None or cust is None:
            return True, "skipped (files not found)"
        diff = set(addr["customer_id"].to_list()) - set(cust["customer_id"].to_list())
        return len(diff) == 0, f"0 orphan customer_ids ({addr.height} addresses checked)"
    check("addresses.customer_id -> customers.customer_id", check_addresses_customer_fk)

    def check_customer_default_addresses():
        addr = get_table("addresses")
        if addr is None:
            return True, "skipped"
        defaults = addr.filter(pl.col("is_default") == True)
        by_type = defaults.group_by(["customer_id", "address_type"]).len()
        max_defaults = by_type["len"].max() if by_type.height > 0 else 0
        return max_defaults <= 1, f"max {max_defaults} default address per customer/type"
    check("customers default address uniqueness", check_customer_default_addresses)

    # --- Online Orders Checks ---
    def check_orders_customer_fk():
        ord_df = get_table("orders_online")
        cust = get_table("customers")
        if ord_df is None or cust is None:
            return True, "skipped"
        diff = set(ord_df["customer_id"].to_list()) - set(cust["customer_id"].to_list())
        return len(diff) == 0, f"0 orphan customer_ids ({ord_df.height} orders checked)"
    check("orders_online.customer_id -> customers.customer_id", check_orders_customer_fk)

    def check_orders_address_fk():
        ord_df = get_table("orders_online")
        addr = get_table("addresses")
        if ord_df is None or addr is None:
            return True, "skipped"
        addr_ids = set(addr["address_id"].to_list())
        diff_ship = set(ord_df["shipping_address_id"].to_list()) - addr_ids
        diff_bill = set(ord_df["billing_address_id"].to_list()) - addr_ids
        return len(diff_ship) == 0 and len(diff_bill) == 0, f"0 orphan shipping/billing address_ids"
    check("orders_online address FKs -> addresses.address_id", check_orders_address_fk)

    def check_order_items_fk():
        items = get_table("order_items_online")
        ord_df = get_table("orders_online")
        prod = get_table("products")
        if items is None or ord_df is None or prod is None:
            return True, "skipped"
        diff_order = set(items["order_id"].to_list()) - set(ord_df["order_id"].to_list())
        diff_prod = set(items["product_id"].to_list()) - set(prod["product_id"].to_list())
        return len(diff_order) == 0 and len(diff_prod) == 0, f"0 orphan order_ids, 0 orphan product_ids ({items.height} items)"
    check("order_items_online FKs -> orders & products", check_order_items_fk)

    def check_order_totals():
        ord_df = get_table("orders_online")
        items = get_table("order_items_online")
        if ord_df is None or items is None:
            return True, "skipped"
        item_sums = items.group_by("order_id").agg(pl.col("line_total").sum().alias("calc_subtotal"))
        joined = ord_df.join(item_sums, on="order_id", how="left")
        diff = (joined["subtotal"] - joined["calc_subtotal"]).abs().max()
        return diff < 0.05, f"max subtotal discrepancy: ${diff:.4f}"
    check("orders_online subtotal == sum(line_total)", check_order_totals)

    # --- In-Store Orders Checks ---
    def check_instore_store_fk():
        ord_df = get_table("orders_instore")
        stores = get_table("stores")
        if ord_df is None or stores is None:
            return True, "skipped"
        diff = set(ord_df["store_id"].to_list()) - set(stores["store_id"].to_list())
        return len(diff) == 0, f"0 orphan store_ids ({ord_df.height} POS txns)"
    check("orders_instore.store_id -> stores.store_id", check_instore_store_fk)

    def check_instore_customer_fk():
        ord_df = get_table("orders_instore")
        cust = get_table("customers")
        if ord_df is None or cust is None:
            return True, "skipped"
        known = ord_df.filter(pl.col("customer_id").is_not_null())
        if known.height == 0:
            return True, "all guest purchases"
        diff = set(known["customer_id"].to_list()) - set(cust["customer_id"].to_list())
        return len(diff) == 0, f"0 orphan customer_ids ({known.height} identified POS txns)"
    check("orders_instore.customer_id -> customers.customer_id", check_instore_customer_fk)

    def check_instore_items_fk():
        items = get_table("order_items_instore")
        ord_df = get_table("orders_instore")
        prod = get_table("products")
        if items is None or ord_df is None or prod is None:
            return True, "skipped"
        diff_txn = set(items["transaction_id"].to_list()) - set(ord_df["transaction_id"].to_list())
        diff_prod = set(items["product_id"].to_list()) - set(prod["product_id"].to_list())
        return len(diff_txn) == 0 and len(diff_prod) == 0, f"0 orphan transaction_ids, 0 orphan product_ids"
    check("order_items_instore FKs -> orders & products", check_instore_items_fk)

    # --- Loyalty Checks ---
    def check_loyalty_fk():
        loy = get_table("loyalty_members")
        cust = get_table("customers")
        if loy is None or cust is None:
            return True, "skipped"
        diff = set(loy["customer_id"].to_list()) - set(cust["customer_id"].to_list())
        return len(diff) == 0, f"0 orphan customer_ids ({loy.height} loyalty members)"
    check("loyalty_members.customer_id -> customers.customer_id", check_loyalty_fk)

    def check_loyalty_txns_fk():
        txns = get_table("loyalty_transactions")
        loy = get_table("loyalty_members")
        if txns is None or loy is None:
            return True, "skipped"
        diff = set(txns["loyalty_id"].to_list()) - set(loy["loyalty_id"].to_list())
        return len(diff) == 0, f"0 orphan loyalty_ids ({txns.height} loyalty txns)"
    check("loyalty_transactions.loyalty_id -> loyalty_members.loyalty_id", check_loyalty_txns_fk)

    # --- Support Tickets Checks ---
    def check_support_fk():
        tickets = get_table("support_tickets")
        cust = get_table("customers")
        if tickets is None or cust is None:
            return True, "skipped"
        diff = set(tickets["customer_id"].to_list()) - set(cust["customer_id"].to_list())
        return len(diff) == 0, f"0 orphan customer_ids ({tickets.height} tickets)"
    check("support_tickets.customer_id -> customers.customer_id", check_support_fk)

    # --- Reviews Checks ---
    def check_reviews_fk():
        rev = get_table("reviews")
        cust = get_table("customers")
        prod = get_table("products")
        if rev is None or cust is None or prod is None:
            return True, "skipped"
        diff_cust = set(rev["customer_id"].to_list()) - set(cust["customer_id"].to_list())
        diff_prod = set(rev["product_id"].to_list()) - set(prod["product_id"].to_list())
        return len(diff_cust) == 0 and len(diff_prod) == 0, f"0 orphan customers, 0 orphan products"
    check("reviews FKs -> customers & products", check_reviews_fk)

    # --- Experiment Assignments Checks ---
    def check_experiments_fk():
        assign = get_table("experiment_assignments")
        exp = get_table("experiments")
        cust = get_table("customers")
        if assign is None or exp is None or cust is None:
            return True, "skipped"
        diff_exp = set(assign["experiment_id"].to_list()) - set(exp["experiment_id"].to_list())
        diff_cust = set(assign["customer_id"].to_list()) - set(cust["customer_id"].to_list())
        return len(diff_exp) == 0 and len(diff_cust) == 0, f"0 orphan experiments, 0 orphan customers"
    check("experiment_assignments FKs -> experiments & customers", check_experiments_fk)

    # --- Fraud Flags Checks ---
    def check_fraud_fk():
        fraud = get_table("fraud_flags")
        cust = get_table("customers")
        if fraud is None or cust is None:
            return True, "skipped"
        diff = set(fraud["customer_id"].to_list()) - set(cust["customer_id"].to_list())
        return len(diff) == 0, f"0 orphan customer_ids ({fraud.height} flags)"
    check("fraud_flags.customer_id -> customers.customer_id", check_fraud_fk)

    console.print()
    if errors:
        for e in errors:
            console.print(f"[red]{e}[/red]")
        console.print(f"\n[red]Validation failed with {len(errors)} error(s)[/red]")
        raise typer.Exit(1)
    else:
        console.print(f"[bold green]✓ All {checks_passed} referential integrity checks passed across all tables![/bold green]")


@app.command()
def preview(
    data_dir: str = typer.Argument(help="Path to generated data directory"),
    table: str = typer.Argument(help="Table name to preview (e.g. customers, orders_online)"),
    limit: int = typer.Option(5, "--limit", "-n", help="Number of rows to display"),
) -> None:
    """Preview rows and schema of a generated Parquet file."""
    import polars as pl

    path = Path(data_dir)
    table_name = table.replace(".parquet", "")
    file_path = path / f"{table_name}.parquet"

    if not file_path.exists():
        console.print(f"[red]Error: Table file not found: {file_path}[/red]")
        available = [p.stem for p in path.glob("*.parquet")]
        if available:
            console.print(f"[yellow]Available tables: {', '.join(sorted(available))}[/yellow]")
        raise typer.Exit(1)

    df = pl.read_parquet(file_path)
    file_size_kb = file_path.stat().st_size / 1024
    size_str = f"{file_size_kb / 1024:.2f} MB" if file_size_kb >= 1024 else f"{file_size_kb:.1f} KB"

    console.print(f"\n📊 [bold cyan]{table_name}.parquet[/bold cyan] ({df.height:,} rows, {df.width} columns, {size_str})\n")

    sample_df = df.head(limit)
    out_table = Table(title=f"Sample Data (First {min(limit, df.height)} of {df.height:,} rows)")

    for col in sample_df.columns:
        out_table.add_column(col, style="cyan", overflow="fold")

    for row in sample_df.iter_rows():
        out_table.add_row(*[str(val) if val is not None else "[dim]NULL[/dim]" for val in row])

    console.print(out_table)


@app.command(name="inspect")
def inspect_cmd(
    data_dir: str = typer.Argument(help="Path to generated data directory"),
    table: str = typer.Argument(help="Table name to inspect (e.g. customers, orders_online)"),
    limit: int = typer.Option(5, "--limit", "-n", help="Number of rows to display"),
) -> None:
    """Alias for preview."""
    preview(data_dir=data_dir, table=table, limit=limit)


@app.command(name="export-duckdb")
def export_duckdb_cmd(
    data_dir: str = typer.Argument(help="Path to generated data directory"),
    output: str = typer.Option(None, "--output", "-o", help="Target .duckdb file path"),
    views: bool = typer.Option(False, "--views", help="Create views pointing to Parquet instead of copying tables"),
) -> None:
    """Export Parquet tables into a standalone, portable DuckDB database."""
    from .duckdb_exporter import export_to_duckdb

    export_to_duckdb(data_dir=data_dir, output_db_path=output, create_views=views)


@app.command(name="export")
def export_cmd(
    data_dir: str = typer.Argument(help="Path to generated data directory"),
    target: str = typer.Option("duckdb", "--target", "-t", help="Target warehouse: duckdb, databricks, snowflake, bigquery"),
    catalog: str = typer.Option(None, "--catalog", help="Databricks catalog name or Snowflake database"),
    schema: str = typer.Option(None, "--schema", "-s", help="Schema or dataset name"),
    database: str = typer.Option(None, "--database", help="Snowflake database or custom DuckDB file path"),
    warehouse: str = typer.Option(None, "--warehouse", "-w", help="Snowflake warehouse or Databricks SQL Warehouse ID"),
    project: str = typer.Option(None, "--project", "-p", help="Google Cloud project ID for BigQuery"),
    dataset: str = typer.Option(None, "--dataset", "-d", help="BigQuery dataset name"),
    stage: str = typer.Option(None, "--stage", "--volume", help="Target stage or UC volume name"),
    profile: str = typer.Option(None, "--profile", help="Connection profile name (Databricks profile or Snowflake connection)"),
    role: str = typer.Option(None, "--role", help="Role name (Snowflake role)"),
    authenticator: str = typer.Option(None, "--authenticator", help="Authenticator method (e.g. externalbrowser for Snowflake SSO)"),
    views: bool = typer.Option(True, "--views/--no-views", help="Create analytical views"),
    verify: bool = typer.Option(True, "--verify/--no-verify", help="Verify row counts against manifest"),
) -> None:
    """Export generated Parquet dataset to DuckDB, Databricks, Snowflake, or BigQuery."""
    from .exporters import (
        BigQueryExporter,
        DatabricksExporter,
        DuckDBExporter,
        ExportConfig,
        SnowflakeExporter,
    )

    t = target.lower().strip()
    extra_params = {}
    if profile:
        extra_params["profile"] = profile
    if role:
        extra_params["role"] = role
    if authenticator:
        extra_params["authenticator"] = authenticator

    config = ExportConfig(
        target=t,
        data_dir=data_dir,
        catalog=catalog,
        schema_name=schema,
        database=database,
        warehouse=warehouse,
        project=project,
        dataset=dataset,
        stage_or_volume=stage,
        create_views=views,
        verify_counts=verify,
        extra_params=extra_params,
    )

    if t == "duckdb":
        exporter = DuckDBExporter(config)
    elif t == "databricks":
        exporter = DatabricksExporter(config)
    elif t == "snowflake":
        exporter = SnowflakeExporter(config)
    elif t == "bigquery":
        exporter = BigQueryExporter(config)
    else:
        console.print(
            f"[red]Error: Unknown export target '{target}'. "
            f"Valid targets: duckdb, databricks, snowflake, bigquery[/red]"
        )
        raise typer.Exit(1)

    try:
        exporter.export()
    except (ImportError, ValueError, RuntimeError) as e:
        from rich.markup import escape
        console.print(f"\n[red]Export Error:[/red] {escape(str(e))}")
        raise typer.Exit(1)


@app.command()
def profile(
    data_dir: str = typer.Argument(help="Path to generated data directory"),
    html: str = typer.Option(None, "--html", help="Path to export an executive HTML report"),
) -> None:
    """Analyze dataset and display an executive KPI performance dashboard."""
    from .profiler import DatasetProfiler

    p = DatasetProfiler(data_dir)
    p.display_dashboard()
    if html:
        p.export_html(html)


@app.command()
def stream(
    data_dir: str = typer.Argument(help="Path to generated data directory"),
    sources: str = typer.Option("clickstream,orders", "--sources", "-s", help="Comma-separated event sources (clickstream, orders, orders_online, orders_instore)"),
    speed: float = typer.Option(100.0, "--speed", help="Playback speed multiplier relative to simulated time (0 = instant)"),
    interval_ms: int = typer.Option(None, "--interval-ms", help="Fixed interval in milliseconds between events"),
    limit: int = typer.Option(None, "--limit", "-n", help="Maximum number of events to emit"),
    event_type: str = typer.Option(None, "--event-type", help="Filter by specific event type (e.g. purchase, add_to_cart)"),
    webhook: str = typer.Option(None, "--webhook", help="HTTP Webhook URL to POST JSON events to"),
    output: str = typer.Option(None, "--output", "-o", help="Append events to a .jsonl file"),
    json_lines: bool = typer.Option(False, "--json", help="Emit raw NDJSON / JSON Lines to stdout"),
    loop: bool = typer.Option(False, "--loop", help="Loop continuously"),
) -> None:
    """Stream events in chronological order to stdout, a file, or HTTP webhook."""
    from .streamer import EventStreamer

    source_list = [s.strip() for s in sources.split(",")] if sources else None

    streamer = EventStreamer(
        data_dir=data_dir,
        sources=source_list,
        event_type=event_type,
        limit=limit,
    )
    streamer.stream(
        speed=speed,
        interval_ms=interval_ms,
        webhook_url=webhook,
        output_file=output,
        raw_json=json_lines,
        loop=loop,
    )


@app.command()
def version() -> None:
    """Show version information."""
    console.print(f"ecommerce-synth v{__version__}")


if __name__ == "__main__":
    app()
