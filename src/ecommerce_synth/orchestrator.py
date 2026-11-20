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
from .generators.fulfillment_generator import FulfillmentGenerator
from .generators.loyalty_generator import LoyaltyGenerator
from .generators.marketing_generator import MarketingGenerator
from .generators.order_generator import OrderGenerator
from .generators.product_generator import ProductGenerator
from .generators.review_generator import ReviewGenerator
from .generators.store_generator import StoreGenerator
from .generators.support_generator import SupportGenerator
from .utils.writer import ChunkedParquetWriter, write_manifest, write_parquet

console = Console()


class Orchestrator:
    """Coordinates all generators and manages the generation pipeline."""

    def __init__(self, config: GenerationConfig, stream_exporter: Any = None):
        self.config = config
        self.stream_exporter = stream_exporter
        self.data: dict[str, pl.DataFrame] = {}
        self.file_stats: list[dict[str, Any]] = []
        self.streamed_tables: list[str] = []

    def run(self, only: list[str] | None = None) -> dict[str, pl.DataFrame]:
        """Execute the full generation pipeline.

        Args:
            only: Optional list of domain names to generate. If None, all
                  domains are generated.
        """
        start_time = time.time()

        # Display run info
        self._print_header()

        if self.stream_exporter is not None:
            self.stream_exporter.setup_stream()

        # 1. Products (fixed dimension, no deps)
        console.print("\n[bold]Phase 1: Dimensions[/bold]")
        self._generate_and_write(
            "products", ProductGenerator, {}, only
        )

        # 2. Stores (fixed dimension, no deps)
        self._generate_and_write(
            "stores", StoreGenerator, {}, only
        )

        # 2b. Paid Media & MMM (ad_campaigns, ad_spend_daily)
        self._generate_and_write(
            "marketing", MarketingGenerator, {}, only
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

        # Extend identity_ground_truth with cross-channel POS accounts when --identity-noise > 0
        if "identity_ground_truth" in self.data and "instore_accounts" in self.data:
            gt_df = self.data["identity_ground_truth"]
            ia_df = self.data["instore_accounts"]
            instore_to_cust = ia_df.__dict__.get("_instore_to_customer", {})
            cid_to_true = dict(zip(
                gt_df["customer_id"].to_list(),
                gt_df["true_entity_id"].to_list(),
            ))
            pos_gt_rows: list[dict] = []
            for acct_id in ia_df["instore_account_id"].to_list():
                linked_cid = instore_to_cust.get(acct_id)
                if linked_cid:
                    pos_gt_rows.append({
                        "record_type": "instore_account",
                        "customer_id": None,
                        "instore_account_id": acct_id,
                        "true_entity_id": cid_to_true.get(linked_cid, linked_cid),
                        "is_duplicate": True,
                        "noise_type": "pos_cross_channel",
                    })
                else:
                    pos_gt_rows.append({
                        "record_type": "instore_account",
                        "customer_id": None,
                        "instore_account_id": acct_id,
                        "true_entity_id": acct_id,
                        "is_duplicate": False,
                        "noise_type": "pos_only",
                    })
            if pos_gt_rows:
                pos_gt_df = pl.DataFrame(pos_gt_rows).cast({
                    "record_type": pl.Utf8,
                    "customer_id": pl.Utf8,
                    "instore_account_id": pl.Utf8,
                    "true_entity_id": pl.Utf8,
                    "is_duplicate": pl.Boolean,
                    "noise_type": pl.Utf8,
                })
                combined_gt = pl.concat([gt_df, pos_gt_df])
                self.data["identity_ground_truth"] = combined_gt
                if self.stream_exporter is None:
                    gt_stats = write_parquet(
                        combined_gt,
                        self.config.output_dir,
                        "identity_ground_truth.parquet",
                        chunk_size=getattr(self.config, "chunk_size", None),
                    )
                    self.file_stats = [
                        s for s in self.file_stats if s.get("table_name") != "identity_ground_truth"
                    ] + [gt_stats]

        # 4b. Fulfillment & Inventory (shipments, returns, inventory_snapshots)
        self._generate_and_write(
            "fulfillment", FulfillmentGenerator, {
                "orders_online": self.data.get("orders_online", pl.DataFrame()),
                "order_items_online": self.data.get("order_items_online", pl.DataFrame()),
                "stores": self.data.get("stores", pl.DataFrame()),
                "products": self.data.get("products", pl.DataFrame()),
            }, only
        )

        # 5. Clickstream (depends on customers, products, orders_online, ad_campaigns)
        console.print("\n[bold]Phase 4: Clickstream[/bold]")
        self._generate_and_write(
            "clickstream", ClickstreamGenerator, {
                "customers": self.data["customers"],
                "products": self.data["products"],
                "orders_online": self.data.get("orders_online", pl.DataFrame()),
                "ad_campaigns": self.data.get("ad_campaigns", pl.DataFrame()),
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

        # Finalize stream or write local manifest
        elapsed = time.time() - start_time
        if self.stream_exporter is not None:
            self.stream_exporter.finalize_stream(self.streamed_tables)
            return self.data

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
            regions=self.config.regions,
            chunk_size=self.config.chunk_size,
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
        """Generate data for a domain, write to Parquet (chunked if large), store in self.data."""

        # Check if this domain is in the 'only' filter
        if only and domain not in only:
            # Still need some domains for downstream dependencies
            required_deps = {"products", "stores", "customers", "orders"}
            if domain not in required_deps:
                return

        gen = generator_cls(self.config)
        chunk_size = getattr(self.config, "chunk_size", 500_000)

        # Streaming chunked generator path (keeps RAM bounded at 50M+ rows)
        if hasattr(gen, "iter_generate"):
            if self.stream_exporter is not None:
                chunk_idx = 0
                total_rows = 0
                last_chunk = None
                for chunk_df in gen.iter_generate(chunk_size=chunk_size, **deps):
                    self.stream_exporter.ingest_chunk(domain, chunk_df, chunk_idx)
                    total_rows += chunk_df.height
                    last_chunk = chunk_df
                    chunk_idx += 1
                self.streamed_tables.append(domain)
                console.print(f"  ✓ [green]Streamed {domain}[/green] — {total_rows:,} rows ({chunk_idx} chunks)")
                self.data[domain] = last_chunk if (chunk_idx == 1 and last_chunk is not None) else pl.DataFrame()
                return

            writer = ChunkedParquetWriter(self.config.output_dir, domain)
            last_chunk = None
            for chunk_df in gen.iter_generate(chunk_size=chunk_size, **deps):
                writer.write_chunk(chunk_df)
                last_chunk = chunk_df
            stats = writer.finalize()
            self.file_stats.append(stats)
            if stats["chunks"] == 1 and last_chunk is not None:
                self.data[domain] = last_chunk
            else:
                self.data[domain] = pl.DataFrame()
            return

        result = gen.generate(**deps)

        def _persist_or_stream(name: str, df: pl.DataFrame) -> None:
            self.data[name] = df
            if hasattr(df, '__dict__') and '_personas' in df.__dict__:
                self.data[name].__dict__['_personas'] = df.__dict__['_personas']

            if self.stream_exporter is not None:
                chunk_idx = 0
                if df.height == 0:
                    self.stream_exporter.ingest_chunk(name, df, 0)
                else:
                    for offset in range(0, df.height, chunk_size):
                        self.stream_exporter.ingest_chunk(name, df.slice(offset, chunk_size), chunk_idx)
                        chunk_idx += 1
                self.streamed_tables.append(name)
                console.print(f"  ✓ [green]Streamed {name}[/green] — {df.height:,} rows")
            else:
                stats = write_parquet(
                    df, self.config.output_dir, f"{name}.parquet", chunk_size=chunk_size
                )
                self.file_stats.append(stats)

        if isinstance(result, dict):
            for name, df in result.items():
                _persist_or_stream(name, df)
        else:
            _persist_or_stream(domain, result)

    def _print_header(self) -> None:
        """Print run configuration."""
        table = Table(title="Generation Configuration", show_header=False)
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")
        table.add_row("Tier", self.config.tier_name.upper())
        table.add_row("Seed", str(self.config.seed))
        table.add_row("Regions", ", ".join(self.config.regions))
        table.add_row("Chunk Size", f"{self.config.chunk_size:,} rows")
        table.add_row("Date Range", f"{self.config.date_range.start} → {self.config.date_range.end}")
        table.add_row("Output", str(self.config.output_dir))
        table.add_row("Fraud Rate", f"{self.config.fraud_rate:.1%}")
        if self.config.identity_noise > 0:
            table.add_row("Identity Noise", f"{self.config.identity_noise:.1%}")
        if self.config.compliance_mode:
            table.add_row("Compliance Mode", "Enabled (GDPR/CCPA Consent)")
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
