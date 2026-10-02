"""Orchestrator — coordinates generators in dependency order.

Runs the full generation pipeline following the topological dependency
DAG to ensure referential integrity across all 19 output files.
"""

from __future__ import annotations

import time
from typing import Any

import polars as pl
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .config import GenerationConfig
from .generators.clickstream_generator import ClickstreamGenerator
from .generators.customer_generator import CustomerGenerator
from .generators.email_generator import EmailGenerator
from .generators.experiment_generator import ExperimentGenerator
from .generators.fraud_generator import FraudGenerator
from .generators.loyalty_generator import LoyaltyGenerator
from .generators.order_generator import OrderGenerator
from .generators.product_generator import ProductGenerator
from .generators.review_generator import ReviewGenerator
from .generators.store_generator import StoreGenerator
from .generators.support_generator import SupportGenerator
from .utils.writer import write_manifest, write_parquet

console = Console()


class Orchestrator:
    """Coordinates all generators and manages the generation pipeline."""

    def __init__(self, config: GenerationConfig):
        self.config = config
        self.data: dict[str, pl.DataFrame] = {}
        self.file_stats: list[dict[str, Any]] = []

    def run(self, only: list[str] | None = None) -> dict[str, pl.DataFrame]:
        """Execute the full generation pipeline.

        Args:
            only: Optional list of domain names to generate. If None, all
                  domains are generated.
        """
        start_time = time.time()

        # Display run info
        self._print_header()

        # 1. Products (fixed dimension, no deps)
        console.print("\n[bold]Phase 1: Dimensions[/bold]")
        self._generate_and_write(
            "products", ProductGenerator, {}, only
        )

        # 2. Stores (fixed dimension, no deps)
        self._generate_and_write(
            "stores", StoreGenerator, {}, only
        )

        # 3. Customers + Addresses (no deps)
        console.print("\n[bold]Phase 2: Customers[/bold]")
        self._generate_and_write(
            "customers", CustomerGenerator, {}, only
        )

        # 4. Orders (depends on customers, addresses, products, stores)
        console.print("\n[bold]Phase 3: Transactions[/bold]")
        self._generate_and_write(
            "orders", OrderGenerator, {
                "customers": self.data["customers"],
                "addresses": self.data["addresses"],
                "products": self.data["products"],
                "stores": self.data["stores"],
            }, only
        )

        # 5. Clickstream (depends on customers, products)
        console.print("\n[bold]Phase 4: Clickstream[/bold]")
        self._generate_and_write(
            "clickstream", ClickstreamGenerator, {
                "customers": self.data["customers"],
                "products": self.data["products"],
            }, only
        )

        # 6. Email (depends on customers)
        console.print("\n[bold]Phase 5: Email[/bold]")
        self._generate_and_write(
            "email", EmailGenerator, {
                "customers": self.data["customers"],
            }, only
        )

        # 7. Loyalty (depends on customers, orders)
        console.print("\n[bold]Phase 6: Loyalty[/bold]")
        self._generate_and_write(
            "loyalty", LoyaltyGenerator, {
                "customers": self.data["customers"],
                "orders_online": self.data.get("orders_online", pl.DataFrame()),
                "orders_instore": self.data.get("orders_instore", pl.DataFrame()),
            }, only
        )

        # 8. Reviews (depends on customers, products, orders)
        console.print("\n[bold]Phase 7: Reviews[/bold]")
        self._generate_and_write(
            "reviews", ReviewGenerator, {
                "customers": self.data["customers"],
                "products": self.data["products"],
                "orders_online": self.data.get("orders_online", pl.DataFrame()),
            }, only
        )

        # 9. Support Tickets (depends on customers, orders)
        console.print("\n[bold]Phase 8: Support[/bold]")
        self._generate_and_write(
            "support_tickets", SupportGenerator, {
                "customers": self.data["customers"],
                "orders_online": self.data.get("orders_online", pl.DataFrame()),
                "orders_instore": self.data.get("orders_instore", pl.DataFrame()),
            }, only
        )

        # 10. A/B Experiments (depends on customers, orders)
        console.print("\n[bold]Phase 9: Experiments[/bold]")
        self._generate_and_write(
            "experiments", ExperimentGenerator, {
                "customers": self.data["customers"],
                "orders_online": self.data.get("orders_online", pl.DataFrame()),
            }, only
        )

        # 11. Fraud Flags (post-processing, depends on everything)
        console.print("\n[bold]Phase 10: Fraud Detection[/bold]")
        self._generate_and_write(
            "fraud_flags", FraudGenerator, {
                "customers": self.data["customers"],
                "orders_online": self.data.get("orders_online", pl.DataFrame()),
                "orders_instore": self.data.get("orders_instore", pl.DataFrame()),
                "clickstream": self.data.get("clickstream", pl.DataFrame()),
            }, only
        )

        # Write manifest
        elapsed = time.time() - start_time
        console.print(f"\n[bold]Writing manifest...[/bold]")
        write_manifest(
            output_dir=self.config.output_dir,
            tier_name=self.config.tier_name,
            seed=self.config.seed,
            date_range={
                "start": str(self.config.date_range.start),
                "end": str(self.config.date_range.end),
            },
            file_stats=self.file_stats,
            generation_time=elapsed,
            fraud_rate=self.config.fraud_rate,
        )

        self._print_summary(elapsed)
        return self.data

    def _generate_and_write(
        self,
        domain: str,
        generator_cls: type,
        deps: dict[str, Any],
        only: list[str] | None,
    ) -> None:
        """Generate data for a domain, write to Parquet, store in self.data."""

        # Check if this domain is in the 'only' filter
        if only and domain not in only:
            # Still need some domains for downstream dependencies
            required_deps = {"products", "stores", "customers", "orders"}
            if domain not in required_deps:
                return

        gen = generator_cls(self.config)
        result = gen.generate(**deps)

        if isinstance(result, dict):
            for name, df in result.items():
                self.data[name] = df
                # Transfer persona metadata if present
                if hasattr(df, '__dict__') and '_personas' in df.__dict__:
                    self.data[name].__dict__['_personas'] = df.__dict__['_personas']

                stats = write_parquet(df, self.config.output_dir, f"{name}.parquet")
                self.file_stats.append(stats)
        else:
            self.data[domain] = result
            # Transfer persona metadata if present
            if hasattr(result, '__dict__') and '_personas' in result.__dict__:
                self.data[domain].__dict__['_personas'] = result.__dict__['_personas']

            stats = write_parquet(result, self.config.output_dir, f"{domain}.parquet")
            self.file_stats.append(stats)

    def _print_header(self) -> None:
        """Print run configuration."""
        table = Table(title="Generation Configuration", show_header=False)
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")
        table.add_row("Tier", self.config.tier_name.upper())
        table.add_row("Seed", str(self.config.seed))
        table.add_row("Date Range", f"{self.config.date_range.start} → {self.config.date_range.end}")
        table.add_row("Output", str(self.config.output_dir))
        table.add_row("Fraud Rate", f"{self.config.fraud_rate:.1%}")
        table.add_row("Target Customers", f"{self.config.tier.customers:,}")
        table.add_row("Target Online Orders", f"{self.config.tier.online_orders:,}")
        table.add_row("Target In-Store Txns", f"{self.config.tier.instore_transactions:,}")
        table.add_row("Target Clickstream", f"{self.config.tier.clickstream_events:,}")
        console.print(Panel(table, border_style="blue"))

    def _print_summary(self, elapsed: float) -> None:
        """Print generation summary."""
        table = Table(title="Generation Complete ✓")
        table.add_column("File", style="cyan")
        table.add_column("Rows", justify="right", style="green")
        table.add_column("Size", justify="right", style="yellow")

        total_rows = 0
        total_size = 0.0
        for fs in self.file_stats:
            table.add_row(
                fs["filename"],
                f"{fs['rows']:,}",
                f"{fs['size_mb']:.1f} MB",
            )
            total_rows += fs["rows"]
            total_size += fs["size_mb"]

        table.add_section()
        table.add_row(
            "[bold]TOTAL[/bold]",
            f"[bold]{total_rows:,}[/bold]",
            f"[bold]{total_size:.1f} MB[/bold]",
        )

        console.print(Panel(table, border_style="green"))
        console.print(f"⏱  Generated in [bold]{elapsed:.1f}s[/bold]")
        console.print(f"📁 Output: [link=file://{self.config.output_dir}]{self.config.output_dir}[/link]")
