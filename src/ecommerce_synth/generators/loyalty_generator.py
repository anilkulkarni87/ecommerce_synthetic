"""Loyalty program generator.

Generates:
- loyalty_members: Enrolled customers with tiers and point balances
- loyalty_transactions: Point earn/redeem/expire/bonus events

Points system:
- Earn: 1 point per $1 spent (online + in-store)
- Tier bonuses: Silver 1.25x, Gold 1.5x, Platinum 2x
- Redeem: 100 points = $1 off
- Expiry: Unused points expire after 12 months
"""

from __future__ import annotations

from datetime import date, timedelta

import polars as pl

from ..persona import CustomerPersona
from ..utils.temporal import random_date_in_range
from .base import BaseGenerator


TIER_THRESHOLDS = {
    "Bronze": (0, 999),
    "Silver": (1000, 4999),
    "Gold": (5000, 14999),
    "Platinum": (15000, float("inf")),
}

TIER_MULTIPLIERS = {
    "Bronze": 1.0,
    "Silver": 1.25,
    "Gold": 1.5,
    "Platinum": 2.0,
}


class LoyaltyGenerator(BaseGenerator):
    """Generate loyalty program members and transactions."""

    def generate(
        self,
        *,
        customers: pl.DataFrame,
        orders_online: pl.DataFrame,
        orders_instore: pl.DataFrame,
        **deps,
    ) -> dict[str, pl.DataFrame]:
        personas: dict[str, CustomerPersona] = customers.__dict__.get("_personas", {})
        target_members = self.config.tier.loyalty_members

        # Identify eligible customers (those with a loyalty tier in their persona)
        customer_list = customers.to_dicts()
        eligible = [
            c for c in customer_list
            if personas.get(c["customer_id"]) and personas[c["customer_id"]].loyalty_tier
        ]

        # Trim to target count
        if len(eligible) > target_members:
            eligible = self.rng.sample(eligible, target_members)

        # Build order lookup: customer_id → list of (date, amount, source)
        order_history: dict[str, list[tuple[date, float, str]]] = {}
        if orders_online.height > 0:
            for row in orders_online.select(["customer_id", "order_date", "total_amount"]).to_dicts():
                cid = row["customer_id"]
                if cid not in order_history:
                    order_history[cid] = []
                order_history[cid].append((row["order_date"].date() if hasattr(row["order_date"], 'date') else row["order_date"], row["total_amount"], "online"))

        if orders_instore.height > 0:
            for row in orders_instore.select(["customer_id", "transaction_date", "total_amount"]).to_dicts():
                cid = row["customer_id"]
                if cid is None:
                    continue
                if cid not in order_history:
                    order_history[cid] = []
                order_history[cid].append((row["transaction_date"].date() if hasattr(row["transaction_date"], 'date') else row["transaction_date"], row["total_amount"], "instore"))

        members: list[dict] = []
        transactions: list[dict] = []

        for cust in eligible:
            cid = cust["customer_id"]
            persona = personas[cid]
            tier = persona.loyalty_tier or "Bronze"

            # Enrollment date: at or after account creation
            cust_created = cust["created_at"]
            if hasattr(cust_created, 'date'):
                cust_created_date = cust_created.date()
            else:
                cust_created_date = cust_created

            enroll_date = random_date_in_range(
                self.rng,
                cust_created_date,
                min(cust_created_date + timedelta(days=90), self.config.date_range.end),
            )

            loyalty_id = f"LOY-{len(members) + 1:06d}"

            # Process order history to generate earn transactions
            lifetime_points = 0
            redeemed_points = 0
            cust_orders = order_history.get(cid, [])
            cust_orders.sort(key=lambda x: x[0])

            for order_date, amount, source in cust_orders:
                if isinstance(order_date, date) and order_date < enroll_date:
                    continue

                # Points earned: $1 = 1 point, with tier multiplier
                multiplier = TIER_MULTIPLIERS.get(tier, 1.0)
                earned = int(round(amount * multiplier))

                transactions.append({
                    "loyalty_txn_id": self._uuid(),
                    "loyalty_id": loyalty_id,
                    "transaction_date": order_date if isinstance(order_date, date) else order_date,
                    "transaction_type": "earn",
                    "points": earned,
                    "source_order_id": None,  # Would need to join on order_id
                    "description": f"Purchase earn {multiplier}x points ({source})",
                })
                lifetime_points += earned

            # Add tier bonus transactions (quarterly)
            if tier in ("Gold", "Platinum"):
                for q in range(8):  # up to 8 quarters in 2 years
                    bonus_date = enroll_date + timedelta(days=90 * (q + 1))
                    if bonus_date > self.config.date_range.end:
                        break
                    bonus_points = {"Gold": 500, "Platinum": 1000}.get(tier, 0)
                    transactions.append({
                        "loyalty_txn_id": self._uuid(),
                        "loyalty_id": loyalty_id,
                        "transaction_date": bonus_date,
                        "transaction_type": "tier_bonus",
                        "points": bonus_points,
                        "source_order_id": None,
                        "description": f"Quarterly {tier} tier bonus",
                    })
                    lifetime_points += bonus_points

            # Occasional point redemptions
            if lifetime_points > 500 and self.rng.random() < 0.4:
                n_redemptions = self.rng.randint(1, 3)
                for _ in range(n_redemptions):
                    redeem_amount = min(
                        self.rng.randint(100, 2000),
                        lifetime_points - redeemed_points,
                    )
                    if redeem_amount <= 0:
                        break

                    redeem_date = random_date_in_range(
                        self.rng, enroll_date, self.config.date_range.end
                    )
                    transactions.append({
                        "loyalty_txn_id": self._uuid(),
                        "loyalty_id": loyalty_id,
                        "transaction_date": redeem_date,
                        "transaction_type": "redeem",
                        "points": -redeem_amount,
                        "source_order_id": None,
                        "description": f"Point redemption — ${redeem_amount / 100:.2f} off",
                    })
                    redeemed_points += redeem_amount

            # Point expiry (annual, ~10% of unredeemed points)
            available = lifetime_points - redeemed_points
            if available > 100 and self.rng.random() < 0.15:
                expired = int(available * self.rng.uniform(0.05, 0.20))
                if expired > 0:
                    expiry_date = random_date_in_range(
                        self.rng,
                        enroll_date + timedelta(days=365),
                        self.config.date_range.end,
                    )
                    transactions.append({
                        "loyalty_txn_id": self._uuid(),
                        "loyalty_id": loyalty_id,
                        "transaction_date": expiry_date,
                        "transaction_type": "expire",
                        "points": -expired,
                        "source_order_id": None,
                        "description": "Annual point expiry",
                    })
                    redeemed_points += expired

            # Birthday bonus
            if self.rng.random() < 0.7:
                bday_bonus = self.rng.choice([100, 200, 500])
                bday_date = random_date_in_range(
                    self.rng, enroll_date, self.config.date_range.end
                )
                transactions.append({
                    "loyalty_txn_id": self._uuid(),
                    "loyalty_id": loyalty_id,
                    "transaction_date": bday_date,
                    "transaction_type": "bonus",
                    "points": bday_bonus,
                    "source_order_id": None,
                    "description": "Birthday bonus points",
                })
                lifetime_points += bday_bonus

            points_balance = max(0, lifetime_points - redeemed_points)
            tier_expiry = enroll_date + timedelta(days=365)
            if tier_expiry < self.config.date_range.end:
                tier_expiry = self.config.date_range.end + timedelta(days=self.rng.randint(30, 180))

            # Preferred store for omnichannel customers
            preferred_store = None
            if persona.is_omnichannel:
                preferred_store = f"STORE-{self.rng.randint(1, self.config.store_count):03d}"

            members.append({
                "loyalty_id": loyalty_id,
                "customer_id": cid,
                "tier": tier,
                "points_balance": points_balance,
                "lifetime_points": lifetime_points,
                "enrolled_date": enroll_date,
                "tier_expiry_date": tier_expiry,
                "preferred_store_id": preferred_store,
            })

        members_df = pl.DataFrame(members).cast({
            "points_balance": pl.Int64,
            "lifetime_points": pl.Int64,
            "enrolled_date": pl.Date,
            "tier_expiry_date": pl.Date,
        }) if members else pl.DataFrame(schema={
            "loyalty_id": pl.Utf8, "customer_id": pl.Utf8,
            "tier": pl.Utf8, "points_balance": pl.Int64,
            "lifetime_points": pl.Int64, "enrolled_date": pl.Date,
            "tier_expiry_date": pl.Date, "preferred_store_id": pl.Utf8,
        })

        txn_df = pl.DataFrame(transactions).cast({
            "points": pl.Int64,
            "transaction_date": pl.Date,
        }) if transactions else pl.DataFrame(schema={
            "loyalty_txn_id": pl.Utf8, "loyalty_id": pl.Utf8,
            "transaction_date": pl.Date, "transaction_type": pl.Utf8,
            "points": pl.Int64, "source_order_id": pl.Utf8,
            "description": pl.Utf8,
        })

        return {
            "loyalty_members": members_df,
            "loyalty_transactions": txn_df,
        }
