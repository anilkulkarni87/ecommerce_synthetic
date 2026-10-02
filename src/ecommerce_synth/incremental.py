"""Incremental data generation module.

Allows generating new synthetic records for a subsequent time window (e.g.
"yesterday's data" or next N days) and appending them to an existing dataset
run to simulate streaming / daily batch ETL loads.
"""

from __future__ import annotations

import json
import random
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import polars as pl
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .config import DateRangeConfig, GenerationConfig, TierConfig, load_config
from .generators.clickstream_generator import ClickstreamGenerator
from .generators.customer_generator import CustomerGenerator
from .generators.email_generator import EmailGenerator
from .generators.experiment_generator import ExperimentGenerator
from .generators.fraud_generator import FraudGenerator
from .generators.loyalty_generator import LoyaltyGenerator
from .generators.order_generator import OrderGenerator
from .generators.review_generator import ReviewGenerator
from .generators.support_generator import SupportGenerator
from .persona import CustomerPersona, PersonaEngine
from .utils.writer import write_manifest, write_parquet

console = Console()


class IncrementalGenerator:
    """Manages incremental synthetic data generation for pipeline testing."""

    def __init__(
        self,
        base_dir: Path | str,
        days: int = 1,
        daily_batches: bool = False,
        seed: int | None = None,
        append: bool = True,
    ):
        self.base_dir = Path(base_dir)
        self.days = max(1, days)
        self.daily_batches = daily_batches
        self.append = append

        if not self.base_dir.exists():
            raise FileNotFoundError(f"Base dataset directory not found: {self.base_dir}")

        manifest_path = self.base_dir / "_manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"Missing _manifest.json in {self.base_dir}")

        with open(manifest_path) as f:
            self.manifest: dict[str, Any] = json.load(f)

        self.tier_name = self.manifest.get("tier", "small")
        self.seed = seed if seed is not None else (self.manifest.get("seed", 42) + 1000)

        # Base date range
        date_range_raw = self.manifest.get("date_range", {})
        start_str = date_range_raw.get("start", "2023-01-01")
        end_str = date_range_raw.get("end", "2024-12-31")

        self.base_start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
        self.base_end_date = datetime.strptime(end_str, "%Y-%m-%d").date()

    def run(self) -> dict[str, pl.DataFrame]:
        """Execute incremental generation.

        Returns:
            Dictionary of updated cumulative DataFrames (or delta DataFrames).
        """
        start_time = time.time()

        console.print(
            Panel(
                f"[bold cyan]Incremental Generation Mode[/bold cyan]\n"
                f"Base Directory: [bold]{self.base_dir}[/bold]\n"
                f"Tier: [green]{self.tier_name.upper()}[/green]\n"
                f"Base End Date: [yellow]{self.base_end_date}[/yellow]\n"
                f"Days to Generate: [magenta]{self.days}[/magenta] "
                f"({'Daily Batches' if self.daily_batches else 'Single Batch'})",
                border_style="cyan",
            )
        )

        # Load existing core tables
        existing_data = self._load_existing_tables()

        if self.daily_batches:
            return self._run_daily_batches(existing_data, start_time)
        else:
            inc_start = self.base_end_date + timedelta(days=1)
            inc_end = inc_start + timedelta(days=self.days - 1)
            return self._run_batch(
                existing_data=existing_data,
                start_date=inc_start,
                end_date=inc_end,
                batch_name=f"incremental_{inc_start.strftime('%Y%m%d')}_{inc_end.strftime('%Y%m%d')}",
                start_time=start_time,
            )

    def _load_existing_tables(self) -> dict[str, pl.DataFrame]:
        """Load parquet tables present in the base directory."""
        tables: dict[str, pl.DataFrame] = {}
        for p in self.base_dir.glob("*.parquet"):
            name = p.stem
            tables[name] = pl.read_parquet(p)
        return tables

    def _run_daily_batches(
        self,
        existing_data: dict[str, pl.DataFrame],
        start_time: float,
    ) -> dict[str, pl.DataFrame]:
        """Run day-by-day incremental batches."""
        current_data = existing_data
        all_deltas: list[dict[str, pl.DataFrame]] = []

        for day_idx in range(self.days):
            current_day = self.base_end_date + timedelta(days=day_idx + 1)
            console.print(f"\n[bold green]Generating Daily Batch {day_idx + 1}/{self.days}: {current_day}[/bold green]")
            batch_name = f"batches/day_{day_idx + 1}_{current_day.strftime('%Y%m%d')}"

            delta = self._generate_slice(
                existing_data=current_data,
                start_date=current_day,
                end_date=current_day,
                days_count=1,
            )

            # Write daily delta
            delta_dir = self.base_dir / batch_name
            delta_dir.mkdir(parents=True, exist_ok=True)
            for name, df in delta.items():
                write_parquet(df, delta_dir, f"{name}.parquet")

            # Merge into cumulative dataset
            current_data = self._merge_data(current_data, delta)
            all_deltas.append(delta)

        # Update base tables and manifest
        if self.append:
            self._save_cumulative(current_data, self.base_end_date + timedelta(days=self.days), start_time)

        return current_data

    def _run_batch(
        self,
        existing_data: dict[str, pl.DataFrame],
        start_date: date,
        end_date: date,
        batch_name: str,
        start_time: float,
    ) -> dict[str, pl.DataFrame]:
        """Run single incremental batch covering the full date range."""
        delta = self._generate_slice(
            existing_data=existing_data,
            start_date=start_date,
            end_date=end_date,
            days_count=self.days,
        )

        # Write delta batch files
        delta_dir = self.base_dir / batch_name
        delta_dir.mkdir(parents=True, exist_ok=True)
        console.print(f"\n[bold]Writing delta batch files to {delta_dir}...[/bold]")
        for name, df in delta.items():
            write_parquet(df, delta_dir, f"{name}.parquet")

        # Merge with existing
        cumulative_data = self._merge_data(existing_data, delta)

        if self.append:
            self._save_cumulative(cumulative_data, end_date, start_time)

        return cumulative_data

    def _generate_slice(
        self,
        existing_data: dict[str, pl.DataFrame],
        start_date: date,
        end_date: date,
        days_count: int,
    ) -> dict[str, pl.DataFrame]:
        """Generate a delta slice of data for the given date range."""
        config = load_config(
            tier_name=self.tier_name,
            seed=self.seed,
            output_dir=self.base_dir,
        )

        # Override date range
        config.date_range = DateRangeConfig(start=start_date, end=end_date)

        # Scale target volumes proportionally to duration
        # Baseline is 730 days (2 years)
        baseline_days = 730
        fraction = max(0.001, days_count / baseline_days)

        scaled_tier = TierConfig(
            customers=max(1, int(config.tier.customers * fraction * 0.2)),  # 20% organic new signups
            online_orders=max(2, int(config.tier.online_orders * fraction)),
            instore_transactions=max(2, int(config.tier.instore_transactions * fraction)),
            clickstream_events=max(10, int(config.tier.clickstream_events * fraction)),
            emails_sent=max(5, int(config.tier.emails_sent * fraction)),
            loyalty_members=max(1, int(config.tier.loyalty_members * fraction * 0.2)),
            support_tickets=max(1, int(config.tier.support_tickets * fraction)),
            ab_experiments=max(1, int(config.tier.ab_experiments * fraction)),
        )
        config.tier = scaled_tier

        # Reconstruct personas for existing customers
        existing_customers = existing_data.get("customers", pl.DataFrame())
        existing_addresses = existing_data.get("addresses", pl.DataFrame())
        products = existing_data.get("products", pl.DataFrame())
        stores = existing_data.get("stores", pl.DataFrame())

        # Persona engine for existing customers
        persona_engine = PersonaEngine(config, random.Random(self.seed))
        reconstructed_personas: dict[str, CustomerPersona] = {}
        for idx, row in enumerate(existing_customers.iter_rows(named=True)):
            cid = row["customer_id"]
            # Assign deterministic persona
            reconstructed_personas[cid] = persona_engine.assign(idx, len(existing_customers))

        # Generate new customers for this slice (organic growth)
        cust_gen = CustomerGenerator(config)
        new_cust_result = cust_gen.generate()
        delta_customers = new_cust_result["customers"]
        delta_addresses = new_cust_result["addresses"]

        # Merge personas
        new_personas = delta_customers.__dict__.get("_personas", {})
        all_personas = {**reconstructed_personas, **new_personas}

        combined_customers = pl.concat([existing_customers, delta_customers])
        combined_customers.__dict__["_personas"] = all_personas

        combined_addresses = pl.concat([existing_addresses, delta_addresses])

        # Generate new orders for this time window
        order_gen = OrderGenerator(config)
        order_res = order_gen.generate(
            customers=combined_customers,
            addresses=combined_addresses,
            products=products,
            stores=stores,
        )

        delta_orders_online = order_res["orders_online"]
        delta_items_online = order_res["order_items_online"]
        delta_orders_instore = order_res["orders_instore"]
        delta_items_instore = order_res["order_items_instore"]
        delta_instore_accounts = order_res.get("instore_accounts", pl.DataFrame())

        # Clickstream in this window
        click_gen = ClickstreamGenerator(config)
        delta_clickstream = click_gen.generate(
            customers=combined_customers,
            products=products,
        )

        # Email in this window
        email_gen = EmailGenerator(config)
        email_res = email_gen.generate(customers=combined_customers)
        delta_campaigns = email_res["email_campaigns"]
        delta_email_events = email_res["email_events"]

        # Loyalty transactions for new orders
        loyalty_gen = LoyaltyGenerator(config)
        loyalty_res = loyalty_gen.generate(
            customers=combined_customers,
            orders_online=delta_orders_online,
            orders_instore=delta_orders_instore,
        )
        delta_loyalty_members = loyalty_res["loyalty_members"]
        delta_loyalty_txns = loyalty_res["loyalty_transactions"]

        # Reviews for recent orders
        review_gen = ReviewGenerator(config)
        delta_reviews = review_gen.generate(
            customers=combined_customers,
            products=products,
            orders_online=delta_orders_online,
        )

        # Support tickets
        support_gen = SupportGenerator(config)
        delta_support = support_gen.generate(
            customers=combined_customers,
            orders_online=delta_orders_online,
            orders_instore=delta_orders_instore,
        )

        # Experiments
        exp_gen = ExperimentGenerator(config)
        exp_res = exp_gen.generate(
            customers=combined_customers,
            orders_online=delta_orders_online,
        )
        delta_exp = exp_res["experiments"]
        delta_assignments = exp_res["experiment_assignments"]

        # Fraud flags
        fraud_gen = FraudGenerator(config)
        delta_fraud = fraud_gen.generate(
            customers=combined_customers,
            orders_online=delta_orders_online,
            orders_instore=delta_orders_instore,
            clickstream=delta_clickstream,
        )

        delta_dict: dict[str, pl.DataFrame] = {
            "customers": delta_customers,
            "addresses": delta_addresses,
            "orders_online": delta_orders_online,
            "order_items_online": delta_items_online,
            "orders_instore": delta_orders_instore,
            "order_items_instore": delta_items_instore,
            "instore_accounts": delta_instore_accounts,
            "clickstream": delta_clickstream,
            "email_campaigns": delta_campaigns,
            "email_events": delta_email_events,
            "loyalty_members": delta_loyalty_members,
            "loyalty_transactions": delta_loyalty_txns,
            "reviews": delta_reviews,
            "support_tickets": delta_support,
            "experiments": delta_exp,
            "experiment_assignments": delta_assignments,
            "fraud_flags": delta_fraud,
        }

        return delta_dict

    def _merge_data(
        self,
        base_data: dict[str, pl.DataFrame],
        delta_data: dict[str, pl.DataFrame],
    ) -> dict[str, pl.DataFrame]:
        """Concatenate delta frames into base frames."""
        merged: dict[str, pl.DataFrame] = {}
        all_keys = set(base_data.keys()).union(set(delta_data.keys()))

        for k in all_keys:
            base_df = base_data.get(k)
            delta_df = delta_data.get(k)

            if base_df is not None and delta_df is not None:
                # Avoid duplicates for dimensional tables if empty delta
                if delta_df.height == 0:
                    merged[k] = base_df
                else:
                    merged[k] = pl.concat([base_df, delta_df])
            elif base_df is not None:
                merged[k] = base_df
            elif delta_df is not None:
                merged[k] = delta_df

        return merged

    def _save_cumulative(
        self,
        cumulative_data: dict[str, pl.DataFrame],
        new_end_date: date,
        start_time: float,
    ) -> None:
        """Overwrite base parquet files with updated cumulative tables and refresh manifest."""
        console.print(f"\n[bold cyan]Appending to cumulative files in {self.base_dir}...[/bold cyan]")
        file_stats: list[dict[str, Any]] = []

        for name, df in cumulative_data.items():
            stats = write_parquet(df, self.base_dir, f"{name}.parquet")
            file_stats.append(stats)

        elapsed = time.time() - start_time

        # Update manifest
        date_range = {
            "start": str(self.base_start_date),
            "end": str(new_end_date),
        }

        history = self.manifest.get("incremental_history", [])
        history.append({
            "run_at": datetime.now().isoformat(),
            "days_added": self.days,
            "new_end_date": str(new_end_date),
            "daily_batches": self.daily_batches,
        })

        write_manifest(
            output_dir=self.base_dir,
            tier_name=self.tier_name,
            seed=self.seed,
            date_range=date_range,
            file_stats=file_stats,
            generation_time=elapsed,
            fraud_rate=self.manifest.get("fraud_rate", 0.02),
            is_incremental=True,
            incremental_state={"history": history},
        )

        console.print(f"\n[green]✓ Incremental run complete and appended to {self.base_dir}![/green]")
