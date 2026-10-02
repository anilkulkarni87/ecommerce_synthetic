"""Business KPI and statistical profiler for synthetic ecommerce datasets.

Analyzes generated Parquet datasets and generates executive-grade
performance dashboards in the terminal or exportable HTML reports.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import polars as pl
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


class DatasetProfiler:
    """Computes business and operational metrics across the synthetic dataset."""

    def __init__(self, data_dir: Path | str):
        self.data_dir = Path(data_dir)
        if not self.data_dir.exists():
            raise FileNotFoundError(f"Data directory not found: {self.data_dir}")

        self.tables = self._load_tables()
        self.manifest = self._load_manifest()

    def _load_manifest(self) -> dict[str, Any]:
        manifest_path = self.data_dir / "_manifest.json"
        if manifest_path.exists():
            with open(manifest_path) as f:
                return json.load(f)
        return {}

    def _load_tables(self) -> dict[str, pl.DataFrame]:
        tables: dict[str, pl.DataFrame] = {}
        for p in self.data_dir.glob("*.parquet"):
            tables[p.stem] = pl.read_parquet(p)
        return tables

    def profile(self) -> dict[str, Any]:
        """Compute all metrics and return a structured dictionary."""
        metrics: dict[str, Any] = {}

        # 1. Financial & Omnichannel Revenue
        orders_online = self.tables.get("orders_online", pl.DataFrame())
        orders_instore = self.tables.get("orders_instore", pl.DataFrame())

        online_rev = float(orders_online["total_amount"].sum()) if orders_online.height > 0 else 0.0
        instore_rev = float(orders_instore["total_amount"].sum()) if orders_instore.height > 0 else 0.0
        total_gmv = online_rev + instore_rev

        online_orders_cnt = orders_online.height
        instore_orders_cnt = orders_instore.height
        total_orders_cnt = online_orders_cnt + instore_orders_cnt

        online_aov = (online_rev / online_orders_cnt) if online_orders_cnt > 0 else 0.0
        instore_aov = (instore_rev / instore_orders_cnt) if instore_orders_cnt > 0 else 0.0
        overall_aov = (total_gmv / total_orders_cnt) if total_orders_cnt > 0 else 0.0

        online_disc = float(orders_online["discount_amount"].sum()) if "discount_amount" in orders_online.columns else 0.0
        instore_disc = float(orders_instore["discount_amount"].sum()) if "discount_amount" in orders_instore.columns else 0.0

        metrics["financials"] = {
            "total_gmv": total_gmv,
            "online_revenue": online_rev,
            "instore_revenue": instore_rev,
            "online_share_pct": (online_rev / total_gmv * 100) if total_gmv > 0 else 0.0,
            "instore_share_pct": (instore_rev / total_gmv * 100) if total_gmv > 0 else 0.0,
            "online_orders": online_orders_cnt,
            "instore_orders": instore_orders_cnt,
            "total_orders": total_orders_cnt,
            "online_aov": online_aov,
            "instore_aov": instore_aov,
            "overall_aov": overall_aov,
            "total_discounts": online_disc + instore_disc,
        }

        # 2. Customers & Omnichannel Behavior
        customers = self.tables.get("customers", pl.DataFrame())
        instore_accounts = self.tables.get("instore_accounts", pl.DataFrame())

        total_customers = customers.height
        active_customers = customers.filter(pl.col("is_active")).height if "is_active" in customers.columns else 0

        # Segment breakdown
        segments: dict[str, int] = {}
        if "customer_segment" in customers.columns and customers.height > 0:
            for row in customers.group_by("customer_segment").len().iter_rows(named=True):
                segments[row["customer_segment"]] = row["len"]

        # Omnichannel customers (online customer who also shopped in-store or has in-store account)
        online_cids = set(orders_online["customer_id"].drop_nulls().to_list()) if orders_online.height > 0 else set()
        instore_cids = set(orders_instore["customer_id"].drop_nulls().to_list()) if orders_instore.height > 0 else set()
        if instore_accounts.height > 0 and "customer_id" in instore_accounts.columns:
            instore_cids.update(instore_accounts["customer_id"].drop_nulls().to_list())

        omnichannel_cids = online_cids.intersection(instore_cids)
        omnichannel_count = len(omnichannel_cids)
        omnichannel_pct = (omnichannel_count / total_customers * 100) if total_customers > 0 else 0.0

        metrics["customers"] = {
            "total_customers": total_customers,
            "active_customers": active_customers,
            "active_pct": (active_customers / total_customers * 100) if total_customers > 0 else 0.0,
            "segments": segments,
            "omnichannel_customers": omnichannel_count,
            "omnichannel_pct": omnichannel_pct,
        }

        # 3. Clickstream Funnel
        clickstream = self.tables.get("clickstream", pl.DataFrame())
        if clickstream.height > 0 and "event_type" in clickstream.columns:
            event_counts = {}
            for row in clickstream.group_by("event_type").len().iter_rows(named=True):
                event_counts[row["event_type"]] = row["len"]

            total_events = clickstream.height
            total_sessions = clickstream["session_id"].n_unique() if "session_id" in clickstream.columns else 0
            purchases = event_counts.get("purchase", 0)
            checkouts = event_counts.get("begin_checkout", 0)
            cart_adds = event_counts.get("add_to_cart", 0)

            conv_rate = (purchases / total_sessions * 100) if total_sessions > 0 else 0.0
            abandon_rate = ((cart_adds - purchases) / cart_adds * 100) if cart_adds > 0 else 0.0

            metrics["funnel"] = {
                "total_events": total_events,
                "total_sessions": total_sessions,
                "cart_adds": cart_adds,
                "checkouts": checkouts,
                "purchases": purchases,
                "conversion_rate_pct": conv_rate,
                "cart_abandonment_pct": max(0.0, abandon_rate),
            }
        else:
            metrics["funnel"] = None

        # 4. Loyalty Program
        loyalty = self.tables.get("loyalty_members", pl.DataFrame())
        loyalty_txns = self.tables.get("loyalty_transactions", pl.DataFrame())

        if loyalty.height > 0:
            loyalty_count = loyalty.height
            pen_pct = (loyalty_count / total_customers * 100) if total_customers > 0 else 0.0
            tiers = {}
            for row in loyalty.group_by("tier").len().iter_rows(named=True):
                tiers[row["tier"]] = row["len"]

            total_earned = float(loyalty_txns.filter(pl.col("points") > 0)["points"].sum()) if loyalty_txns.height > 0 else 0.0
            total_redeemed = abs(float(loyalty_txns.filter(pl.col("points") < 0)["points"].sum())) if loyalty_txns.height > 0 else 0.0

            metrics["loyalty"] = {
                "members": loyalty_count,
                "penetration_pct": pen_pct,
                "tiers": tiers,
                "points_earned": int(total_earned),
                "points_redeemed": int(total_redeemed),
            }
        else:
            metrics["loyalty"] = None

        # 5. Product Categories
        items_online = self.tables.get("order_items_online", pl.DataFrame())
        products = self.tables.get("products", pl.DataFrame())

        if items_online.height > 0 and products.height > 0:
            joined = items_online.join(products, on="product_id", how="left")
            cat_summary = (
                joined.group_by("category")
                .agg([
                    pl.col("line_total").sum().alias("revenue"),
                    pl.col("quantity").sum().alias("units"),
                ])
                .sort("revenue", descending=True)
                .head(5)
            )
            metrics["top_categories"] = cat_summary.to_dicts()
        else:
            metrics["top_categories"] = []

        # 6. Fraud & Security
        fraud = self.tables.get("fraud_flags", pl.DataFrame())
        if fraud.height > 0:
            fraud_count = fraud.height
            confirmed = fraud.filter(pl.col("is_confirmed_fraud")).height
            avg_risk = float(fraud["risk_score"].mean()) if "risk_score" in fraud.columns else 0.0
            type_breakdown = {}
            for row in fraud.group_by("fraud_type").len().iter_rows(named=True):
                type_breakdown[row["fraud_type"]] = row["len"]

            metrics["fraud"] = {
                "flagged_events": fraud_count,
                "confirmed_fraud": confirmed,
                "confirmed_pct": (confirmed / fraud_count * 100) if fraud_count > 0 else 0.0,
                "avg_risk_score": avg_risk,
                "type_breakdown": type_breakdown,
            }
        else:
            metrics["fraud"] = None

        # 7. Customer Support
        tickets = self.tables.get("support_tickets", pl.DataFrame())
        if tickets.height > 0:
            csat_series = tickets["satisfaction_score"].drop_nulls()
            avg_csat = float(csat_series.mean()) if csat_series.len() > 0 else 0.0
            categories = {}
            for row in tickets.group_by("category").len().iter_rows(named=True):
                categories[row["category"]] = row["len"]

            metrics["support"] = {
                "total_tickets": tickets.height,
                "avg_csat": avg_csat,
                "categories": categories,
            }
        else:
            metrics["support"] = None

        return metrics

    def display_dashboard(self) -> None:
        """Render a formatted KPI dashboard to the terminal."""
        m = self.profile()
        fin = m["financials"]
        cust = m["customers"]
        funnel = m["funnel"]
        loyalty = m["loyalty"]
        fraud = m["fraud"]
        support = m["support"]

        tier_str = self.manifest.get("tier", "unknown").upper()
        date_str = f"{self.manifest.get('date_range', {}).get('start', '')} → {self.manifest.get('date_range', {}).get('end', '')}"

        console.print(
            Panel(
                f"[bold cyan]Omnichannel Performance & Executive Profiler[/bold cyan]\n"
                f"Dataset: [bold]{self.data_dir}[/bold] | Tier: [green]{tier_str}[/green] | Window: [yellow]{date_str}[/yellow]",
                border_style="cyan",
            )
        )

        # Financial Summary Table
        fin_table = Table(title="💰 Revenue & Commercial Economics", show_header=True)
        fin_table.add_column("Channel", style="cyan")
        fin_table.add_column("Orders", justify="right", style="green")
        fin_table.add_column("Revenue (GMV)", justify="right", style="bold yellow")
        fin_table.add_column("Share", justify="right", style="magenta")
        fin_table.add_column("AOV", justify="right", style="blue")

        fin_table.add_row(
            "Online Web Store",
            f"{fin['online_orders']:,}",
            f"${fin['online_revenue']:,.2f}",
            f"{fin['online_share_pct']:.1f}%",
            f"${fin['online_aov']:.2f}",
        )
        fin_table.add_row(
            "In-Store Retail POS",
            f"{fin['instore_orders']:,}",
            f"${fin['instore_revenue']:,.2f}",
            f"{fin['instore_share_pct']:.1f}%",
            f"${fin['instore_aov']:.2f}",
        )
        fin_table.add_section()
        fin_table.add_row(
            "[bold]OMNICHANNEL TOTAL[/bold]",
            f"[bold]{fin['total_orders']:,}[/bold]",
            f"[bold]${fin['total_gmv']:,.2f}[/bold]",
            "100.0%",
            f"[bold]${fin['overall_aov']:.2f}[/bold]",
        )
        console.print(fin_table)

        # Customer & Omnichannel Table
        cust_table = Table(title="👥 Customer Health & Omnichannel Behavior", show_header=True)
        cust_table.add_column("Metric", style="cyan")
        cust_table.add_column("Value", justify="right", style="green")
        cust_table.add_column("Benchmark / Detail", style="dim")

        cust_table.add_row("Total Customers", f"{cust['total_customers']:,}", "All registered accounts")
        cust_table.add_row("Active Customers", f"{cust['active_customers']:,}", f"{cust['active_pct']:.1f}% activity rate")
        cust_table.add_row(
            "Omnichannel Shoppers",
            f"{cust['omnichannel_customers']:,}",
            f"[bold magenta]{cust['omnichannel_pct']:.1f}%[/bold magenta] cross-channel shopper overlap",
        )
        for seg, count in cust.get("segments", {}).items():
            cust_table.add_row(f"Segment: {seg.capitalize()}", f"{count:,}", f"{(count / cust['total_customers'] * 100):.1f}% of base")
        console.print(cust_table)

        # Funnel & Digital Engagement
        if funnel:
            fun_table = Table(title="🌐 Web Funnel & Digital Conversion", show_header=True)
            fun_table.add_column("Funnel Stage", style="cyan")
            fun_table.add_column("Count", justify="right", style="green")
            fun_table.add_column("Conversion / Drop-off", justify="right", style="yellow")

            fun_table.add_row("Total Sessions", f"{funnel['total_sessions']:,}", "100.0%")
            fun_table.add_row("Added to Cart", f"{funnel['cart_adds']:,}", f"{(funnel['cart_adds'] / funnel['total_sessions'] * 100):.1f}% of sessions")
            fun_table.add_row("Began Checkout", f"{funnel['checkouts']:,}", f"{(funnel['checkouts'] / funnel['total_sessions'] * 100):.1f}% of sessions")
            fun_table.add_row("Completed Purchase", f"{funnel['purchases']:,}", f"[bold green]{funnel['conversion_rate_pct']:.2f}%[/bold green] conversion rate")
            fun_table.add_section()
            fun_table.add_row("Cart Abandonment Rate", f"{funnel['cart_abandonment_pct']:.1f}%", "[dim]Industry avg: 65-75%[/dim]")
            console.print(fun_table)

        # Top Product Categories
        if m["top_categories"]:
            cat_table = Table(title="📦 Top Product Categories by Sales", show_header=True)
            cat_table.add_column("Category", style="cyan")
            cat_table.add_column("Revenue", justify="right", style="green")
            cat_table.add_column("Units Sold", justify="right", style="yellow")
            for cat in m["top_categories"]:
                cat_table.add_row(cat["category"], f"${cat['revenue']:,.2f}", f"{cat['units']:,}")
            console.print(cat_table)

        # Fraud & Risk Diagnostic
        if fraud:
            fraud_table = Table(title="🛡️ Fraud & Risk Diagnostic", show_header=True)
            fraud_table.add_column("Attack Type / Indicator", style="cyan")
            fraud_table.add_column("Incidents", justify="right", style="yellow")
            fraud_table.add_column("Metrics", style="green")

            fraud_table.add_row("Total Flags", f"{fraud['flagged_events']:,}", f"Avg Risk: {fraud['avg_risk_score']:.2f}")
            fraud_table.add_row("Confirmed Fraud Labels", f"{fraud['confirmed_fraud']:,}", f"{fraud['confirmed_pct']:.1f}% verified ground-truth")
            fraud_table.add_section()
            for ftype, count in fraud.get("type_breakdown", {}).items():
                fraud_table.add_row(f"Pattern: {ftype}", f"{count:,}", "Anomaly signature detected")
            console.print(fraud_table)

        console.print(f"[bold green]✓ Profiling complete for {self.data_dir}[/bold green]\n")

    def export_html(self, output_path: Path | str) -> Path:
        """Export an executive HTML report."""
        m = self.profile()
        fin = m["financials"]
        cust = m["customers"]
        funnel = m["funnel"]
        fraud = m["fraud"]

        out_path = Path(output_path)
        tier_str = self.manifest.get("tier", "unknown").upper()
        date_str = f"{self.manifest.get('date_range', {}).get('start', '')} to {self.manifest.get('date_range', {}).get('end', '')}"

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Ecommerce Synthetic Profiler Report</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: #0f172a; color: #f8fafc; padding: 30px; margin: 0; }}
        .container {{ max-width: 1100px; margin: 0 auto; }}
        h1 {{ color: #38bdf8; margin-bottom: 5px; }}
        .subtitle {{ color: #94a3b8; font-size: 15px; margin-bottom: 30px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .card {{ background: #1e293b; border-radius: 12px; padding: 20px; border: 1px solid #334155; }}
        .card-label {{ color: #94a3b8; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px; }}
        .card-value {{ font-size: 28px; font-weight: 700; color: #f8fafc; margin-top: 8px; }}
        .card-sub {{ font-size: 12px; color: #38bdf8; margin-top: 4px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #334155; font-size: 14px; }}
        th {{ color: #94a3b8; font-weight: 600; text-transform: uppercase; font-size: 12px; }}
        .badge {{ background: #0284c7; color: white; padding: 4px 8px; border-radius: 6px; font-size: 11px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🛒 Ecommerce Synthetic Dataset Profiler</h1>
        <div class="subtitle">Dataset Tier: <span class="badge">{tier_str}</span> | Time Window: {date_str}</div>

        <div class="grid">
            <div class="card">
                <div class="card-label">Total GMV (Revenue)</div>
                <div class="card-value">${fin['total_gmv']:,.2f}</div>
                <div class="card-sub">{fin['total_orders']:,} total orders</div>
            </div>
            <div class="card">
                <div class="card-label">Online AOV</div>
                <div class="card-value">${fin['online_aov']:.2f}</div>
                <div class="card-sub">${fin['online_revenue']:,.2f} ({fin['online_share_pct']:.1f}% share)</div>
            </div>
            <div class="card">
                <div class="card-label">In-Store AOV</div>
                <div class="card-value">${fin['instore_aov']:.2f}</div>
                <div class="card-sub">${fin['instore_revenue']:,.2f} ({fin['instore_share_pct']:.1f}% share)</div>
            </div>
            <div class="card">
                <div class="card-label">Omnichannel Shoppers</div>
                <div class="card-value">{cust['omnichannel_pct']:.1f}%</div>
                <div class="card-sub">{cust['omnichannel_customers']:,} crossover customers</div>
            </div>
        </div>

        <div class="card" style="margin-bottom: 30px;">
            <div class="card-label">Channel Revenue Breakdown</div>
            <table>
                <thead><tr><th>Channel</th><th>Orders</th><th>Revenue</th><th>Share</th><th>AOV</th></tr></thead>
                <tbody>
                    <tr><td>Online Web</td><td>{fin['online_orders']:,}</td><td>${fin['online_revenue']:,.2f}</td><td>{fin['online_share_pct']:.1f}%</td><td>${fin['online_aov']:.2f}</td></tr>
                    <tr><td>In-Store POS</td><td>{fin['instore_orders']:,}</td><td>${fin['instore_revenue']:,.2f}</td><td>{fin['instore_share_pct']:.1f}%</td><td>${fin['instore_aov']:.2f}</td></tr>
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>"""
        with open(out_path, "w") as f:
            f.write(html_content)

        console.print(f"  ✓ Exported HTML report to [bold]{out_path}[/bold]")
        return out_path
