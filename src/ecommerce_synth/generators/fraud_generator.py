"""Fraud flag generator.

Scans generated data for customers assigned the Fraudster persona and
creates fraud_flags records with:
- 6 distinct fraud types with type-specific detection signatures
- Risk scores (0.0–1.0) correlated with fraud severity
- Ground truth labels for ML training
- JSON-encoded details describing the specific anomaly patterns
"""

from __future__ import annotations

import json
from datetime import timedelta

import polars as pl

from ..persona import CustomerPersona
from ..utils.temporal import random_date_in_range, random_timestamp
from .base import BaseGenerator


class FraudGenerator(BaseGenerator):
    """Generate fraud flags by scanning for fraudster-persona entities."""

    def generate(
        self,
        *,
        customers: pl.DataFrame,
        orders_online: pl.DataFrame,
        orders_instore: pl.DataFrame,
        clickstream: pl.DataFrame,
        **deps,
    ) -> pl.DataFrame:
        personas: dict[str, CustomerPersona] = customers.__dict__.get("_personas", {})

        records: list[dict] = []

        # Identify fraudster customers
        fraudsters = {
            cid: persona
            for cid, persona in personas.items()
            if persona.is_fraudster
        }

        if not fraudsters:
            return self._empty_df()

        # Build order lookups
        online_orders_by_cust: dict[str, list[dict]] = {}
        if orders_online.height > 0:
            for row in orders_online.to_dicts():
                cid = row["customer_id"]
                online_orders_by_cust.setdefault(cid, []).append(row)

        instore_orders_by_cust: dict[str, list[dict]] = {}
        if orders_instore.height > 0:
            for row in orders_instore.to_dicts():
                cid = row.get("customer_id")
                if cid:
                    instore_orders_by_cust.setdefault(cid, []).append(row)

        for cid, persona in fraudsters.items():
            fraud_type = persona.fraud_type

            if fraud_type == "card_testing":
                records.extend(
                    self._flag_card_testing(cid, online_orders_by_cust.get(cid, []))
                )
            elif fraud_type == "account_takeover":
                records.extend(
                    self._flag_account_takeover(cid, online_orders_by_cust.get(cid, []))
                )
            elif fraud_type == "promo_abuse":
                records.extend(
                    self._flag_promo_abuse(cid, online_orders_by_cust.get(cid, []))
                )
            elif fraud_type == "refund_abuse":
                records.extend(
                    self._flag_refund_abuse(cid, online_orders_by_cust.get(cid, []))
                )
            elif fraud_type == "synthetic_identity":
                records.extend(
                    self._flag_synthetic_identity(cid)
                )
            elif fraud_type == "velocity_spike":
                all_orders = (
                    online_orders_by_cust.get(cid, [])
                    + instore_orders_by_cust.get(cid, [])
                )
                records.extend(
                    self._flag_velocity_spike(cid, all_orders)
                )

        # Add some false positives (~10% of total flags)
        n_false_positives = max(1, len(records) // 10)
        non_fraudster_ids = [
            cid for cid in personas if not personas[cid].is_fraudster
        ]
        for _ in range(min(n_false_positives, len(non_fraudster_ids))):
            cid = self.rng.choice(non_fraudster_ids)
            orders = online_orders_by_cust.get(cid, [])
            if orders:
                order = self.rng.choice(orders)
                records.append(self._make_flag(
                    entity_type="order",
                    entity_id=order["order_id"],
                    customer_id=cid,
                    fraud_type=self.rng.choice(["velocity_spike", "promo_abuse"]),
                    risk_score=self.rng.uniform(0.3, 0.6),
                    is_confirmed=False,
                    details={"reason": "automated_rule_trigger", "false_positive": True},
                ))

        df = pl.DataFrame(records)
        if df.height > 0:
            df = df.cast({
                "risk_score": pl.Float64,
                "is_confirmed_fraud": pl.Boolean,
                "detected_at": pl.Datetime,
            })
        return df

    def _flag_card_testing(self, cid: str, orders: list[dict]) -> list[dict]:
        """Flag rapid low-value transactions from the same customer."""
        flags = []
        for order in orders:
            total = order.get("total_amount", 0)
            if total < 20:  # Low-value test charge pattern
                flags.append(self._make_flag(
                    entity_type="order",
                    entity_id=order["order_id"],
                    customer_id=cid,
                    fraud_type="card_testing",
                    risk_score=self.rng.uniform(0.7, 0.95),
                    is_confirmed=self.rng.random() < 0.85,
                    details={
                        "pattern": "rapid_low_value_transactions",
                        "transaction_amount": total,
                        "velocity": f"{len(orders)} orders",
                        "avg_time_between_orders_hours": round(self.rng.uniform(0.1, 2.0), 1),
                    },
                ))
        # Also flag the account
        flags.append(self._make_flag(
            entity_type="account",
            entity_id=cid,
            customer_id=cid,
            fraud_type="card_testing",
            risk_score=self.rng.uniform(0.80, 0.98),
            is_confirmed=True,
            details={
                "pattern": "automated_card_testing",
                "total_transactions": len(orders),
                "low_value_pct": round(sum(1 for o in orders if o.get("total_amount", 0) < 20) / max(len(orders), 1), 2),
            },
        ))
        return flags

    def _flag_account_takeover(self, cid: str, orders: list[dict]) -> list[dict]:
        """Flag suspicious address changes + large orders."""
        flags = []
        flags.append(self._make_flag(
            entity_type="account",
            entity_id=cid,
            customer_id=cid,
            fraud_type="account_takeover",
            risk_score=self.rng.uniform(0.75, 0.95),
            is_confirmed=self.rng.random() < 0.70,
            details={
                "pattern": "shipping_address_change_before_large_order",
                "new_address_state": self.rng.choice(["CA", "TX", "FL", "NY", "IL"]),
                "days_since_address_change": self.rng.randint(0, 3),
                "password_changed_recently": self.rng.random() < 0.5,
            },
        ))
        # Flag suspicious high-value orders
        for order in orders:
            if order.get("total_amount", 0) > 300:
                flags.append(self._make_flag(
                    entity_type="order",
                    entity_id=order["order_id"],
                    customer_id=cid,
                    fraud_type="account_takeover",
                    risk_score=self.rng.uniform(0.65, 0.90),
                    is_confirmed=self.rng.random() < 0.60,
                    details={
                        "pattern": "high_value_order_after_account_change",
                        "order_amount": order.get("total_amount", 0),
                        "shipping_billing_mismatch": True,
                    },
                ))
        return flags

    def _flag_promo_abuse(self, cid: str, orders: list[dict]) -> list[dict]:
        """Flag repeated coupon use across multiple orders."""
        flags = []
        coupon_orders = [o for o in orders if o.get("coupon_code")]
        if len(coupon_orders) >= 3:
            flags.append(self._make_flag(
                entity_type="account",
                entity_id=cid,
                customer_id=cid,
                fraud_type="promo_abuse",
                risk_score=self.rng.uniform(0.60, 0.85),
                is_confirmed=self.rng.random() < 0.75,
                details={
                    "pattern": "excessive_coupon_usage",
                    "coupon_usage_count": len(coupon_orders),
                    "unique_coupons_used": len(set(o.get("coupon_code") for o in coupon_orders)),
                    "total_discount_amount": round(sum(o.get("discount_amount", 0) for o in coupon_orders), 2),
                },
            ))
            # Flag individual high-discount orders
            for o in coupon_orders:
                if o.get("discount_amount", 0) > 50:
                    flags.append(self._make_flag(
                        entity_type="order",
                        entity_id=o["order_id"],
                        customer_id=cid,
                        fraud_type="promo_abuse",
                        risk_score=self.rng.uniform(0.55, 0.80),
                        is_confirmed=self.rng.random() < 0.65,
                        details={
                            "pattern": "high_discount_order",
                            "discount_amount": o.get("discount_amount", 0),
                            "coupon_code": o.get("coupon_code"),
                        },
                    ))
        return flags

    def _flag_refund_abuse(self, cid: str, orders: list[dict]) -> list[dict]:
        """Flag high return rate with defective claims."""
        flags = []
        returned = [o for o in orders if o.get("status") == "returned"]
        if len(returned) >= 2:
            return_rate = len(returned) / max(len(orders), 1)
            flags.append(self._make_flag(
                entity_type="account",
                entity_id=cid,
                customer_id=cid,
                fraud_type="refund_abuse",
                risk_score=self.rng.uniform(0.65, 0.90),
                is_confirmed=self.rng.random() < 0.70,
                details={
                    "pattern": "excessive_returns",
                    "total_orders": len(orders),
                    "total_returns": len(returned),
                    "return_rate": round(return_rate, 2),
                    "total_refund_amount": round(sum(o.get("total_amount", 0) for o in returned), 2),
                    "claimed_reason": self.rng.choice(["defective", "not_as_described", "damaged", "wrong_item"]),
                },
            ))
        return flags

    def _flag_synthetic_identity(self, cid: str) -> list[dict]:
        """Flag accounts with mismatched identity signals."""
        return [self._make_flag(
            entity_type="account",
            entity_id=cid,
            customer_id=cid,
            fraud_type="synthetic_identity",
            risk_score=self.rng.uniform(0.70, 0.95),
            is_confirmed=self.rng.random() < 0.60,
            details={
                "pattern": "identity_mismatch",
                "name_address_mismatch": True,
                "phone_area_code_mismatch": self.rng.random() < 0.7,
                "email_domain_disposable": self.rng.random() < 0.4,
                "account_age_days": self.rng.randint(0, 30),
                "ip_geolocation_mismatch": self.rng.random() < 0.6,
            },
        )]

    def _flag_velocity_spike(self, cid: str, orders: list[dict]) -> list[dict]:
        """Flag abnormal order frequency."""
        flags = []
        if len(orders) >= 5:
            flags.append(self._make_flag(
                entity_type="account",
                entity_id=cid,
                customer_id=cid,
                fraud_type="velocity_spike",
                risk_score=self.rng.uniform(0.60, 0.88),
                is_confirmed=self.rng.random() < 0.55,
                details={
                    "pattern": "abnormal_order_frequency",
                    "orders_in_period": len(orders),
                    "expected_frequency": "2-4 per quarter",
                    "actual_frequency": f"{len(orders)} in period",
                    "peak_day_orders": self.rng.randint(3, 10),
                },
            ))
        return flags

    def _make_flag(
        self,
        entity_type: str,
        entity_id: str,
        customer_id: str,
        fraud_type: str,
        risk_score: float,
        is_confirmed: bool,
        details: dict,
    ) -> dict:
        """Create a single fraud flag record."""
        detected_at = random_timestamp(
            self.rng,
            random_date_in_range(
                self.rng,
                self.config.date_range.start,
                self.config.date_range.end,
            ),
            "online",
        )

        return {
            "flag_id": self._uuid(),
            "entity_type": entity_type,
            "entity_id": entity_id,
            "customer_id": customer_id,
            "fraud_type": fraud_type,
            "risk_score": round(risk_score, 3),
            "is_confirmed_fraud": is_confirmed,
            "detected_at": detected_at,
            "details": json.dumps(details),
        }

    def _empty_df(self) -> pl.DataFrame:
        return pl.DataFrame(schema={
            "flag_id": pl.Utf8, "entity_type": pl.Utf8,
            "entity_id": pl.Utf8, "customer_id": pl.Utf8,
            "fraud_type": pl.Utf8, "risk_score": pl.Float64,
            "is_confirmed_fraud": pl.Boolean, "detected_at": pl.Datetime,
            "details": pl.Utf8,
        })
