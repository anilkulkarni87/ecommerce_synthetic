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
) -> None:
    """Generate synthetic ecommerce data at the specified volume tier."""

    console.print(f"\n🛒 [bold]Ecommerce Synthetic Data Generator[/bold] v{__version__}\n")

    if incremental:
        inc_gen = IncrementalGenerator(
            base_dir=incremental,
            days=days,
            daily_batches=daily_batches,
            seed=seed,
        )
        inc_gen.run()
        if duckdb:
            from .duckdb_exporter import export_to_duckdb
            export_to_duckdb(incremental)
        return

    config = load_config(
        tier_name=tier,
        seed=seed,
        output_dir=output,
        fraud_rate=fraud_rate,
    )

    only_list = [s.strip() for s in only.split(",")] if only else None

    orchestrator = Orchestrator(config)
    orchestrator.run(only=only_list)

    if duckdb:
        from .duckdb_exporter import export_to_duckdb
        export_to_duckdb(config.output_dir)


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
    """Validate referential integrity across all 19 generated tables."""

    import polars as pl

    path = Path(data_dir)
    if not path.exists():
        console.print(f"[red]Error: Directory not found: {data_dir}[/red]")
        raise typer.Exit(1)

    manifest_path = path / "_manifest.json"
    if manifest_path.exists():
        with open(manifest_path) as f:
            manifest = json.load(f)
        console.print(f"Validating [bold]{manifest.get('tier', 'unknown').upper()}[/bold] tier dataset")
        console.print(f"Generated at: {manifest.get('generated_at', 'unknown')}\n")

    errors: list[str] = []
    checks_passed = 0

    def load(name: str) -> pl.DataFrame | None:
        fp = path / f"{name}.parquet"
        if fp.exists():
            return pl.read_parquet(fp)
        return None

    # Load all 19 datasets
    customers = load("customers")
    addresses = load("addresses")
    products = load("products")
    stores = load("stores")
    instore_accounts = load("instore_accounts")
    orders_online = load("orders_online")
    order_items_online = load("order_items_online")
    orders_instore = load("orders_instore")
    order_items_instore = load("order_items_instore")
    clickstream = load("clickstream")
    email_campaigns = load("email_campaigns")
    email_events = load("email_events")
    loyalty_members = load("loyalty_members")
    loyalty_txns = load("loyalty_transactions")
    reviews = load("reviews")
    support_tickets = load("support_tickets")
    experiments = load("experiments")
    experiment_assignments = load("experiment_assignments")
    fraud_flags = load("fraud_flags")

    # Helper function for checking FK
    def check_fk(
        source_df: pl.DataFrame | None,
        source_col: str,
        target_ids: set,
        rel_desc: str,
        allow_null: bool = False,
    ) -> None:
        nonlocal checks_passed
        if source_df is None or len(target_ids) == 0:
            return

        if allow_null:
            filtered = source_df.filter(pl.col(source_col).is_not_null())
            if filtered.height == 0:
                checks_passed += 1
                console.print(f"  ✓ {rel_desc} (0 non-null values)")
                return
            orphans = filtered.filter(~pl.col(source_col).is_in(target_ids))
        else:
            orphans = source_df.filter(~pl.col(source_col).is_in(target_ids))

        if orphans.height > 0:
            errors.append(f"  ✗ {orphans.height} {rel_desc} reference invalid IDs")
        else:
            checks_passed += 1
            console.print(f"  ✓ {rel_desc}")

    # Primary key sets
    customer_ids = set(customers["customer_id"].to_list()) if customers is not None else set()
    address_ids = set(addresses["address_id"].to_list()) if addresses is not None else set()
    product_ids = set(products["product_id"].to_list()) if products is not None else set()
    store_ids = set(stores["store_id"].to_list()) if stores is not None else set()
    instore_account_ids = set(instore_accounts["instore_account_id"].to_list()) if instore_accounts is not None else set()
    online_order_ids = set(orders_online["order_id"].to_list()) if orders_online is not None else set()
    instore_order_ids = set(orders_instore["transaction_id"].to_list()) if orders_instore is not None else set()
    all_order_ids = online_order_ids.union(instore_order_ids)
    loyalty_ids = set(loyalty_members["loyalty_id"].to_list()) if loyalty_members is not None else set()
    campaign_ids = set(email_campaigns["campaign_id"].to_list()) if email_campaigns is not None else set()
    experiment_ids = set(experiments["experiment_id"].to_list()) if experiments is not None else set()

    console.print(f"[bold cyan]Core Dimensions Loaded:[/bold cyan]")
    if customers is not None:
        console.print(f"  Customers: {len(customer_ids):,}")
    if products is not None:
        console.print(f"  Products: {len(product_ids):,}")
    if stores is not None:
        console.print(f"  Stores: {len(store_ids):,}")

    console.print(f"\n[bold cyan]Validating Foreign Keys & Referential Integrity across 19 Tables:[/bold cyan]")

    # 1. Addresses
    check_fk(addresses, "customer_id", customer_ids, "Addresses → Customers FK")

    # 2. In-Store Accounts
    check_fk(instore_accounts, "store_id", store_ids, "In-Store Accounts → Stores FK")
    check_fk(instore_accounts, "customer_id", customer_ids, "In-Store Accounts → Customers FK (optional)", allow_null=True)

    # 3. Online Orders & Line Items
    check_fk(orders_online, "customer_id", customer_ids, "Online Orders → Customers FK")
    check_fk(orders_online, "shipping_address_id", address_ids, "Online Orders → Shipping Addresses FK", allow_null=True)
    check_fk(orders_online, "billing_address_id", address_ids, "Online Orders → Billing Addresses FK", allow_null=True)
    check_fk(order_items_online, "order_id", online_order_ids, "Online Order Items → Online Orders FK")
    check_fk(order_items_online, "product_id", product_ids, "Online Order Items → Products FK")

    # 4. In-Store Orders & Line Items
    check_fk(orders_instore, "store_id", store_ids, "In-Store Orders → Stores FK")
    check_fk(orders_instore, "customer_id", customer_ids, "In-Store Orders → Customers FK (optional)", allow_null=True)
    check_fk(orders_instore, "instore_account_id", instore_account_ids, "In-Store Orders → In-Store Accounts FK (optional)", allow_null=True)
    check_fk(order_items_instore, "transaction_id", instore_order_ids, "In-Store Order Items → In-Store Orders FK")
    check_fk(order_items_instore, "product_id", product_ids, "In-Store Order Items → Products FK")

    # 5. Clickstream
    check_fk(clickstream, "customer_id", customer_ids, "Clickstream Events → Customers FK (optional)", allow_null=True)
    check_fk(clickstream, "product_id", product_ids, "Clickstream Events → Products FK (optional)", allow_null=True)

    # 6. Email Marketing
    check_fk(email_events, "customer_id", customer_ids, "Email Events → Customers FK")
    check_fk(email_events, "campaign_id", campaign_ids, "Email Events → Campaigns FK")

    # 7. Loyalty Program
    check_fk(loyalty_members, "customer_id", customer_ids, "Loyalty Members → Customers FK")
    check_fk(loyalty_members, "preferred_store_id", store_ids, "Loyalty Members → Preferred Stores FK", allow_null=True)
    check_fk(loyalty_txns, "loyalty_id", loyalty_ids, "Loyalty Transactions → Loyalty Members FK")

    # 8. Product Reviews
    check_fk(reviews, "product_id", product_ids, "Reviews → Products FK")
    check_fk(reviews, "customer_id", customer_ids, "Reviews → Customers FK")
    check_fk(reviews, "order_id", online_order_ids, "Reviews → Online Orders FK (optional)", allow_null=True)

    # 9. Support Tickets
    check_fk(support_tickets, "customer_id", customer_ids, "Support Tickets → Customers FK")
    check_fk(support_tickets, "order_id", all_order_ids, "Support Tickets → Orders FK (optional)", allow_null=True)

    # 10. A/B Testing Experiments
    check_fk(experiment_assignments, "experiment_id", experiment_ids, "Experiment Assignments → Experiments FK")
    check_fk(experiment_assignments, "customer_id", customer_ids, "Experiment Assignments → Customers FK")
    check_fk(experiment_assignments, "conversion_order_id", online_order_ids, "Experiment Assignments → Conversion Orders FK (optional)", allow_null=True)

    # 11. Fraud Flags
    check_fk(fraud_flags, "customer_id", customer_ids, "Fraud Flags → Customers FK")

    # Summary
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
