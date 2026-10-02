"""A/B test experiment and assignment generator.

Generates:
- experiments: ~20 experiments per year across various types
- experiment_assignments: Customer → variant assignments with conversion tracking

Treatment variants have a configurable lift (0-15%) to make A/B analysis
exercises realistic. Conversion is tracked against real online orders.
"""

from __future__ import annotations

from datetime import timedelta

import polars as pl

from ..persona import CustomerPersona
from ..utils.temporal import random_date_in_range
from .base import BaseGenerator


EXPERIMENT_NAMES = {
    "ui": [
        "Checkout Flow v2", "New Product Page Layout", "Homepage Hero Banner Test",
        "Mobile Nav Redesign", "Cart Sidebar vs Full Page", "Search Results Grid vs List",
        "Quick View Modal Test", "Dark Mode Toggle", "Add to Cart Animation",
        "Product Image Zoom Style", "Review Display Format", "Filter Panel Position",
    ],
    "pricing": [
        "Free Shipping Threshold $50 vs $75", "Dynamic Pricing Test", "Bundle Discount Structure",
        "Price Anchoring Display", "Subscription Pricing Tiers", "Tiered Discount Test",
        "First Order Discount Amount", "Member vs Non-Member Pricing",
    ],
    "email": [
        "Subject Line Emoji Test", "Send Time Optimization", "Email Frequency Test",
        "Abandoned Cart Timing", "Welcome Series Length", "Personalization Level Test",
        "CTA Button Color", "Email Template Layout",
    ],
    "recommendation": [
        "Collaborative vs Content Filtering", "Cross-Sell Placement Test",
        "Personalized vs Trending Recs", "Recommendation Widget Size",
        "Recently Viewed vs Similar Items", "AI-Powered vs Rule-Based Recs",
    ],
    "shipping": [
        "Free Shipping Badge Placement", "Delivery Estimate Display",
        "Express Shipping Upsell", "Shipping Insurance Opt-in",
        "Carbon Neutral Shipping Option", "Delivery Date Promise Test",
    ],
}

EXPERIMENT_STATUSES = ["draft", "running", "concluded"]


class ExperimentGenerator(BaseGenerator):
    """Generate A/B test experiments and assignments."""

    def generate(
        self,
        *,
        customers: pl.DataFrame,
        orders_online: pl.DataFrame,
        **deps,
    ) -> dict[str, pl.DataFrame]:
        n_experiments = self.config.tier.ab_experiments
        personas: dict[str, CustomerPersona] = customers.__dict__.get("_personas", {})
        customer_ids = customers["customer_id"].to_list()

        # Build order lookup for conversion tracking
        orders_by_customer: dict[str, list[dict]] = {}
        if orders_online.height > 0:
            for row in orders_online.select(["order_id", "customer_id", "order_date", "total_amount"]).to_dicts():
                cid = row["customer_id"]
                orders_by_customer.setdefault(cid, []).append(row)

        experiments: list[dict] = []
        assignments: list[dict] = []

        exp_types = list(EXPERIMENT_NAMES.keys())

        for i in range(n_experiments):
            exp_type = self.rng.choice(exp_types)
            exp_name = self.rng.choice(EXPERIMENT_NAMES[exp_type])

            # Experiment duration: 2-8 weeks
            start = random_date_in_range(
                self.rng,
                self.config.date_range.start,
                self.config.date_range.end - timedelta(days=60),
            )
            duration_days = self.rng.randint(14, 56)
            end = min(start + timedelta(days=duration_days), self.config.date_range.end)

            # Status based on dates
            if end < self.config.date_range.end - timedelta(days=14):
                status = "concluded"
            elif start > self.config.date_range.end - timedelta(days=7):
                status = "draft"
            else:
                status = "running"

            # Traffic percentage: 10-100%
            traffic_pct = self.rng.choice([0.10, 0.20, 0.25, 0.50, 0.75, 1.0])

            exp_id = f"EXP-{i + 1:03d}"

            experiments.append({
                "experiment_id": exp_id,
                "experiment_name": exp_name,
                "experiment_type": exp_type,
                "start_date": start,
                "end_date": end,
                "status": status,
                "traffic_pct": traffic_pct,
            })

            # Generate assignments for this experiment
            # Number of participants based on traffic % and customer count
            n_participants = int(len(customer_ids) * traffic_pct * 0.8)
            n_participants = min(n_participants, len(customer_ids))

            if n_participants <= 0:
                continue

            participants = self.rng.sample(customer_ids, n_participants)

            # Treatment lift: 0-15% improvement
            treatment_lift = self.rng.uniform(0.0, 0.15)
            has_treatment_b = self.rng.random() < 0.3  # 30% have 3 variants

            # Base conversion rate
            base_conversion = self.rng.uniform(0.02, 0.08)

            for cid in participants:
                persona = personas.get(cid)

                # Assign variant
                if has_treatment_b:
                    variant = self.rng.choice(["control", "treatment_a", "treatment_b"])
                else:
                    variant = self.rng.choice(["control", "treatment_a"])

                assigned_at = random_date_in_range(self.rng, start, end)

                # Conversion: treatment has higher rate
                if variant == "control":
                    conv_rate = base_conversion
                elif variant == "treatment_a":
                    conv_rate = base_conversion * (1 + treatment_lift)
                else:
                    conv_rate = base_conversion * (1 + treatment_lift * 0.5)

                # Persona adjustment
                if persona:
                    conv_rate *= (persona.browse_to_buy / 0.03) if persona.browse_to_buy > 0 else 0.5

                converted = self.rng.random() < min(conv_rate, 0.5)

                conversion_order_id = None
                conversion_value = None

                if converted:
                    # Link to a real order if possible
                    cust_orders = orders_by_customer.get(cid, [])
                    matching_orders = [
                        o for o in cust_orders
                        if hasattr(o["order_date"], 'date') and o["order_date"].date() >= start
                        or (not hasattr(o["order_date"], 'date') and o["order_date"] >= start)
                    ]
                    if matching_orders:
                        order = self.rng.choice(matching_orders)
                        conversion_order_id = order["order_id"]
                        conversion_value = order["total_amount"]
                    else:
                        conversion_value = round(self.rng.uniform(25, 300), 2)

                assignments.append({
                    "assignment_id": self._uuid(),
                    "experiment_id": exp_id,
                    "customer_id": cid,
                    "variant": variant,
                    "assigned_at": assigned_at,
                    "converted": converted,
                    "conversion_order_id": conversion_order_id,
                    "conversion_value": conversion_value,
                })

        exp_df = pl.DataFrame(experiments).cast({
            "start_date": pl.Date,
            "end_date": pl.Date,
            "traffic_pct": pl.Float64,
        }) if experiments else pl.DataFrame(schema={
            "experiment_id": pl.Utf8, "experiment_name": pl.Utf8,
            "experiment_type": pl.Utf8, "start_date": pl.Date,
            "end_date": pl.Date, "status": pl.Utf8, "traffic_pct": pl.Float64,
        })

        assign_df = pl.DataFrame(assignments).cast({
            "assigned_at": pl.Date,
            "converted": pl.Boolean,
            "conversion_value": pl.Float64,
        }) if assignments else pl.DataFrame(schema={
            "assignment_id": pl.Utf8, "experiment_id": pl.Utf8,
            "customer_id": pl.Utf8, "variant": pl.Utf8,
            "assigned_at": pl.Date, "converted": pl.Boolean,
            "conversion_order_id": pl.Utf8, "conversion_value": pl.Float64,
        })

        return {
            "experiments": exp_df,
            "experiment_assignments": assign_df,
        }
