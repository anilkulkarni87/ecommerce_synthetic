"""Customer support ticket generator.

Generates realistic support tickets with:
- Category distribution matching real ecommerce patterns
- Priority levels correlated with issue severity
- Resolution time following log-normal distribution
- CSAT scores correlated with resolution speed
- ~25% of tickets reference an actual order
- Fraud-related tickets flagged appropriately
"""

from __future__ import annotations

from datetime import timedelta

import polars as pl

from ..persona import CustomerPersona
from ..utils.temporal import (
    random_date_in_range,
    random_timestamp,
    timestamp_after,
)
from .base import BaseGenerator


CHANNELS = ["email", "chat", "phone", "social"]
CHANNEL_WEIGHTS = [0.35, 0.30, 0.25, 0.10]

CATEGORIES = ["shipping", "returns", "billing", "product_defect", "account", "general_inquiry"]
CATEGORY_WEIGHTS = [0.25, 0.20, 0.18, 0.15, 0.12, 0.10]

PRIORITIES = ["low", "medium", "high", "urgent"]
PRIORITY_BY_CATEGORY = {
    "shipping": [0.20, 0.50, 0.25, 0.05],
    "returns": [0.15, 0.45, 0.30, 0.10],
    "billing": [0.10, 0.30, 0.40, 0.20],
    "product_defect": [0.10, 0.35, 0.40, 0.15],
    "account": [0.25, 0.40, 0.25, 0.10],
    "general_inquiry": [0.50, 0.35, 0.10, 0.05],
}

STATUSES = ["open", "in_progress", "waiting_customer", "resolved", "closed", "escalated"]
STATUS_WEIGHTS = [0.05, 0.08, 0.05, 0.40, 0.35, 0.07]

SUBJECT_TEMPLATES = {
    "shipping": [
        "Where is my order?", "Package not delivered", "Wrong item shipped",
        "Delayed shipment — order #{order}", "Tracking number not working",
        "Package damaged in transit", "Need to change shipping address",
        "Missing items from my order", "Delivery to wrong address",
    ],
    "returns": [
        "Want to return item", "Return label not working", "Refund not received",
        "Exchange request", "Item doesn't fit — return needed",
        "Return window — is it still open?", "Damaged item — need return",
        "How to return multiple items?", "Refund status inquiry",
    ],
    "billing": [
        "Charged twice for order", "Incorrect amount charged",
        "Payment declined but order went through", "Need invoice/receipt",
        "Unauthorized charge on my card", "Promo code not applied",
        "Gift card balance issue", "Subscription billing question",
    ],
    "product_defect": [
        "Product stopped working", "Defective item received",
        "Missing parts", "Product doesn't match description",
        "Quality issue with purchase", "Item arrived broken",
        "Warranty claim", "Color/size different than pictured",
    ],
    "account": [
        "Can't log into my account", "Password reset not working",
        "Update my email address", "Delete my account",
        "Suspicious activity on my account", "Merge duplicate accounts",
        "Points/rewards not showing", "Email preferences update",
    ],
    "general_inquiry": [
        "Product availability question", "Size guide question",
        "Bulk order inquiry", "Store hours question",
        "International shipping?", "Gift wrapping options",
        "Product recommendation needed", "Loyalty program question",
    ],
}

DESCRIPTION_TEMPLATES = {
    "shipping": [
        "I placed order #{order} on {date} and it still hasn't arrived. The tracking hasn't updated in {days} days. Can someone please look into this? I need the items by {deadline}.",
        "My package was marked as delivered but I never received it. I've checked with my neighbors and the front desk but nothing. Order #{order}.",
        "I received the wrong items in my order #{order}. I ordered {expected} but received something completely different. Please help resolve this.",
    ],
    "returns": [
        "I'd like to return the items from order #{order}. The {reason}. I've had the items for {days} days. Can you send me a return label?",
        "I initiated a return {days} days ago and haven't received my refund yet. The tracking shows the item was delivered back to your warehouse on {date}. Reference: #{order}.",
        "I need to exchange my purchase for a different size/color. Order #{order}. Is it possible to do a direct exchange rather than return and rebuy?",
    ],
    "billing": [
        "I noticed I was charged ${amount} for order #{order} but the total shown at checkout was ${expected_amount}. Can you explain the discrepancy?",
        "I see a charge of ${amount} on my card statement but I never authorized this purchase. Please investigate and reverse the charge immediately.",
        "I used promo code {code} at checkout but the discount wasn't applied to my order #{order}. The total should be ${expected_amount} not ${amount}.",
    ],
    "product_defect": [
        "The {product} I purchased (order #{order}) stopped working after only {days} days. It {defect}. This is clearly a manufacturing defect and I'd like a replacement or refund.",
        "I received a {product} from order #{order} and it has visible {defect_type}. The item appears to have been damaged before shipping. I'd like a replacement.",
        "The {product} doesn't match the description on your website. The listing said {expected} but what I received {actual}. Very misleading.",
    ],
    "account": [
        "I've been trying to log into my account for the past {days} days but keep getting an error message. I've tried resetting my password multiple times but the reset email never arrives.",
        "I noticed some suspicious activity on my account — there are orders I didn't place and my shipping address was changed. Please lock my account immediately.",
        "I have two accounts with different email addresses and would like to merge them. My loyalty points are split between {email1} and {email2}.",
    ],
    "general_inquiry": [
        "I'm looking for {product} but can't find it on your website. Is it currently out of stock? When will it be available again?",
        "Can you tell me the dimensions and material of {product}? The listing doesn't have enough detail for me to make a decision.",
        "I'm interested in placing a bulk order of {quantity}+ items. Do you offer any bulk discounts or wholesale pricing?",
    ],
}

AGENT_IDS = [f"AGT-{i:03d}" for i in range(1, 51)]  # 50 support agents


class SupportGenerator(BaseGenerator):
    """Generate customer support tickets."""

    def generate(
        self,
        *,
        customers: pl.DataFrame,
        orders_online: pl.DataFrame,
        orders_instore: pl.DataFrame,
        **deps,
    ) -> pl.DataFrame:
        target = self.config.tier.support_tickets
        personas: dict[str, CustomerPersona] = customers.__dict__.get("_personas", {})
        customer_list = customers.to_dicts()

        # Build order lookups
        online_orders = orders_online.to_dicts() if orders_online.height > 0 else []
        instore_orders = orders_instore.to_dicts() if orders_instore.height > 0 else []

        orders_by_customer: dict[str, list[dict]] = {}
        for o in online_orders:
            cid = o.get("customer_id")
            if cid:
                orders_by_customer.setdefault(cid, []).append(o)
        for o in instore_orders:
            cid = o.get("customer_id")
            if cid:
                orders_by_customer.setdefault(cid, []).append(o)

        records: list[dict] = []

        for _ in range(target):
            cust = self.rng.choice(customer_list)
            cid = cust["customer_id"]
            persona = personas.get(cid)

            # Category selection — returns-heavy for high-return personas
            if persona and persona.return_rate > 0.3:
                category = self._pick_weighted(
                    CATEGORIES,
                    [0.15, 0.40, 0.15, 0.15, 0.10, 0.05],
                )
            else:
                category = self._pick_weighted(CATEGORIES, CATEGORY_WEIGHTS)

            priority = self._pick_weighted(
                PRIORITIES,
                PRIORITY_BY_CATEGORY.get(category, [0.25, 0.40, 0.25, 0.10]),
            )

            channel = self._pick_weighted(CHANNELS, CHANNEL_WEIGHTS)

            # Status — most tickets resolve
            status = self._pick_weighted(STATUSES, STATUS_WEIGHTS)

            # Link to order (~25%)
            order_id = None
            if self.rng.random() < 0.25:
                cust_orders = orders_by_customer.get(cid, [])
                if cust_orders:
                    o = self.rng.choice(cust_orders)
                    order_id = o.get("order_id") or o.get("transaction_id")

            # Subject and description
            subject = self.rng.choice(SUBJECT_TEMPLATES.get(category, SUBJECT_TEMPLATES["general_inquiry"]))
            subject = subject.replace("#{order}", f"#{self.rng.randint(100000, 999999)}")

            description = self._generate_description(category, cid, order_id)

            # Timestamps
            created_at = random_timestamp(
                self.rng,
                random_date_in_range(
                    self.rng,
                    self.config.date_range.start,
                    self.config.date_range.end,
                    self.config,
                ),
                "online",
            )

            # First response: 15min - 24h, log-normal distribution
            first_response_at = None
            if status not in ("open",):
                first_response_at = timestamp_after(
                    self.rng, created_at,
                    min_hours=0.25, max_hours=24.0,
                    distribution="lognormal",
                )

            # Resolution: 1h - 72h after creation
            resolved_at = None
            if status in ("resolved", "closed"):
                resolved_at = timestamp_after(
                    self.rng, created_at,
                    min_hours=1.0, max_hours=72.0,
                    distribution="lognormal",
                )

            # CSAT: only for resolved/closed tickets, correlated with resolution speed
            satisfaction_score = None
            if status in ("resolved", "closed") and self.rng.random() < 0.60:
                if resolved_at and (resolved_at - created_at).total_seconds() < 7200:
                    satisfaction_score = self.rng.choices([4, 5, 5, 5, 3], k=1)[0]
                elif resolved_at and (resolved_at - created_at).total_seconds() < 86400:
                    satisfaction_score = self.rng.choices([3, 4, 4, 5, 2], k=1)[0]
                else:
                    satisfaction_score = self.rng.choices([1, 2, 3, 3, 4], k=1)[0]

            # Fraud-related flag
            is_fraud_related = False
            if persona and persona.is_fraudster:
                is_fraud_related = True
            elif category == "billing" and "unauthorized" in subject.lower():
                is_fraud_related = True
            elif category == "account" and "suspicious" in subject.lower():
                is_fraud_related = True

            records.append({
                "ticket_id": self._uuid(),
                "customer_id": cid,
                "order_id": order_id,
                "channel": channel,
                "category": category,
                "priority": priority,
                "status": status,
                "subject": subject,
                "description": description,
                "created_at": created_at,
                "first_response_at": first_response_at,
                "resolved_at": resolved_at,
                "satisfaction_score": satisfaction_score,
                "agent_id": self.rng.choice(AGENT_IDS),
                "is_fraud_related": is_fraud_related,
            })

        df = pl.DataFrame(records)
        if df.height > 0:
            df = df.cast({
                "created_at": pl.Datetime,
                "first_response_at": pl.Datetime,
                "resolved_at": pl.Datetime,
                "satisfaction_score": pl.Int64,
                "is_fraud_related": pl.Boolean,
            })
        return df

    def _generate_description(self, category: str, cid: str, order_id: str | None) -> str:
        """Generate a ticket description."""
        templates = DESCRIPTION_TEMPLATES.get(category, DESCRIPTION_TEMPLATES["general_inquiry"])
        template = self.rng.choice(templates)

        return template.format(
            order=self.rng.randint(100000, 999999),
            date=f"{self.rng.randint(1, 12)}/{self.rng.randint(1, 28)}/{self.rng.randint(2023, 2024)}",
            days=self.rng.randint(1, 30),
            deadline=f"{self.rng.randint(1, 12)}/{self.rng.randint(1, 28)}",
            expected=self.rng.choice(["a blue jacket", "wireless headphones", "size M shirt", "the kitchen set"]),
            reason=self.rng.choice(["item doesn't fit", "not what I expected", "changed my mind", "found a better price", "defective"]),
            amount=round(self.rng.uniform(20, 500), 2),
            expected_amount=round(self.rng.uniform(15, 400), 2),
            code=self.rng.choice(["SAVE20", "VIP15", "WELCOME10", "FLASH30"]),
            product=self.rng.choice(["bluetooth speaker", "running shoes", "laptop stand", "moisturizer", "backpack"]),
            defect=self.rng.choice(["makes a buzzing noise", "has a crack", "buttons don't work", "color is fading"]),
            defect_type=self.rng.choice(["scratches", "dents", "stains", "tears", "cracks"]),
            actual=self.rng.choice(["is much smaller", "is a different color", "has fewer features", "looks nothing like the photo"]),
            email1=f"user{self.rng.randint(1, 999)}@gmail.com",
            email2=f"user{self.rng.randint(1, 999)}@yahoo.com",
            quantity=self.rng.choice([10, 25, 50, 100]),
        )
