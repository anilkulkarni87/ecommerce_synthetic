"""Product review generator.

Generates reviews tied to actual purchases with:
- Rating distribution: bell curve centered at 4.0, with persona skew
- Verified vs unverified purchase flags
- Realistic review titles and body text
- Helpful vote counts correlated with review quality/length
"""

from __future__ import annotations

from datetime import timedelta

import polars as pl

from ..persona import CustomerPersona
from ..utils.temporal import random_date_in_range
from .base import BaseGenerator


# Review title templates by star rating
REVIEW_TITLES = {
    5: [
        "Absolutely love it!", "Best purchase ever!", "Exceeded expectations",
        "Highly recommend!", "Perfect quality", "Five stars all the way",
        "Amazing product!", "Worth every penny", "Couldn't be happier",
        "Must have!", "Outstanding!", "Game changer!",
    ],
    4: [
        "Really good quality", "Very satisfied", "Great value for money",
        "Would buy again", "Solid product", "Nice quality",
        "Good but not perfect", "Happy with purchase", "Recommended",
        "Does what it's supposed to", "Pleasantly surprised",
    ],
    3: [
        "It's okay", "Average quality", "Mixed feelings",
        "Not bad, not great", "Could be better", "Decent for the price",
        "Met basic expectations", "Acceptable", "Fair quality",
        "Some pros and cons", "Middle of the road",
    ],
    2: [
        "Disappointed", "Not worth the price", "Below expectations",
        "Quality issues", "Would not recommend", "Could be much better",
        "Underwhelming", "Needs improvement", "Poor value",
        "Regret this purchase", "Not as described",
    ],
    1: [
        "Terrible quality", "Complete waste of money", "Broke after one use",
        "Do not buy!", "Worst purchase ever", "Total disappointment",
        "Want my money back", "Defective product", "Avoid!",
        "Falls apart immediately", "Scam product",
    ],
}

# Review body templates (mixed and filled at generation time)
REVIEW_BODIES = {
    5: [
        "I've been using this {product_type} for {weeks} weeks now and I absolutely love it. The quality is outstanding and it {positive_action}. Shipping was fast and the packaging was great. Highly recommend to anyone looking for a {product_type}.",
        "This is hands down the best {product_type} I've ever purchased. The {feature} is amazing and it's well worth the price. I've already recommended it to several friends.",
        "Wow, where has this been all my life? The {product_type} arrived in perfect condition and works exactly as described. {positive_action}. Will definitely buy from this brand again.",
        "Exceptional quality! The {product_type} exceeded all my expectations. It's clear that a lot of thought went into the design. The {feature} is a great bonus.",
    ],
    4: [
        "Overall a great {product_type}. The {feature} works well and it's good quality for the price. My only minor complaint is {minor_issue}, but that's nitpicking. Would recommend.",
        "Happy with this purchase. The {product_type} does what it's supposed to do and the quality is solid. I'd give it 5 stars but {minor_issue}. Still a good buy.",
        "Nice {product_type} that delivers on its promises. The {feature} is a nice touch. Arrived on time and was easy to set up. Good value overall.",
    ],
    3: [
        "The {product_type} is okay but nothing special. The {feature} works fine but I expected better for the price. It's decent but I've seen better options out there.",
        "Mixed feelings about this {product_type}. On one hand, the {feature} is nice. On the other hand, {negative_aspect}. It's acceptable but not something I'd rave about.",
        "It does the job but {minor_issue}. The {product_type} is average quality. Not terrible but not great either. You get what you pay for I suppose.",
    ],
    2: [
        "Disappointed with this {product_type}. The {feature} doesn't work as advertised and {negative_aspect}. The quality feels cheap and I don't think it will last. Not worth the money.",
        "I had high hopes but this {product_type} let me down. {negative_aspect} and the overall quality is below what I expected. Considering returning it.",
        "Not impressed. The {product_type} arrived and immediately I noticed {negative_aspect}. The {feature} is mediocre at best. Would not purchase again.",
    ],
    1: [
        "Terrible product. The {product_type} broke within {days} days of use. {negative_aspect} and the quality is absolutely horrible. I want a full refund. Do not waste your money on this.",
        "This is the worst {product_type} I've ever purchased. It {broke_action} almost immediately. The {feature} is completely useless. Save your money and buy something else.",
        "Complete waste of money. {negative_aspect}. I contacted customer service and they were unhelpful. Avoid this {product_type} at all costs. Returning immediately.",
    ],
}

POSITIVE_ACTIONS = [
    "works perfectly every time", "has made my daily routine so much easier",
    "looks even better in person", "is incredibly well-made",
    "fits perfectly", "exceeded all my expectations",
]

FEATURES = [
    "build quality", "design", "material", "functionality", "durability",
    "comfort", "color", "size", "packaging", "texture",
]

MINOR_ISSUES = [
    "the color is slightly different from the photos",
    "it took a while to arrive",
    "the instructions could be clearer",
    "the packaging was minimal",
    "it's slightly smaller than expected",
    "there was a minor scratch on arrival",
]

NEGATIVE_ASPECTS = [
    "the stitching is already coming apart",
    "it doesn't fit as described",
    "the quality doesn't match the price",
    "it arrived damaged",
    "the material feels cheap",
    "it started malfunctioning after a few uses",
    "the color faded after first wash",
    "parts were missing from the box",
]

BROKE_ACTIONS = [
    "stopped working", "fell apart", "cracked", "ripped",
    "started making strange noises", "lost its shape",
]


class ReviewGenerator(BaseGenerator):
    """Generate product reviews."""

    def generate(
        self,
        *,
        customers: pl.DataFrame,
        products: pl.DataFrame,
        orders_online: pl.DataFrame,
        **deps,
    ) -> pl.DataFrame:
        personas: dict[str, CustomerPersona] = customers.__dict__.get("_personas", {})

        # Build order → customer mapping for verified purchases
        order_customer: dict[str, str] = {}
        order_products: dict[str, list[str]] = {}
        if orders_online.height > 0:
            for row in orders_online.select(["order_id", "customer_id"]).to_dicts():
                order_customer[row["order_id"]] = row["customer_id"]

        product_map = {p["product_id"]: p for p in products.to_dicts()}
        active_products = [p for p in products.to_dicts() if p["is_active"]]

        records: list[dict] = []
        customer_list = customers.to_dicts()

        for cust in customer_list:
            cid = cust["customer_id"]
            persona = personas.get(cid)
            if persona is None or persona.review_rate <= 0:
                continue

            # Number of reviews based on persona
            if self.rng.random() < persona.review_rate:
                n_reviews = self.rng.randint(1, max(1, persona.orders_per_year // 2))
            else:
                continue

            for _ in range(n_reviews):
                prod = self.rng.choice(active_products)
                product_id = prod["product_id"]

                # Rating: bell curve centered at 4.0 with persona influence
                if persona.persona_name == "power_shopper":
                    rating = max(1, min(5, round(self.rng.gauss(4.3, 0.6))))
                elif persona.persona_name == "bargain_hunter":
                    rating = max(1, min(5, round(self.rng.gauss(3.5, 1.0))))
                else:
                    rating = max(1, min(5, round(self.rng.gauss(4.0, 0.8))))

                # Verified purchase: ~70% if they have orders
                is_verified = self.rng.random() < 0.70
                order_id = None
                if is_verified:
                    # Pick a random order ID from this customer
                    cust_orders = [
                        oid for oid, ocid in order_customer.items() if ocid == cid
                    ]
                    if cust_orders:
                        order_id = self.rng.choice(cust_orders)
                    else:
                        is_verified = False

                # Generate review text
                title = self.rng.choice(REVIEW_TITLES.get(rating, REVIEW_TITLES[3]))

                product_type = prod["subcategory"].lower().rstrip("s")
                body = self._generate_body(rating, product_type)

                # Review date: after purchase (or random date if unverified)
                cust_created = cust["created_at"]
                if hasattr(cust_created, 'date'):
                    cust_created_date = cust_created.date()
                else:
                    cust_created_date = cust_created
                review_date = random_date_in_range(
                    self.rng,
                    cust_created_date,
                    self.config.date_range.end,
                )

                # Helpful votes: longer reviews get more, extreme ratings get more
                base_votes = self.rng.randint(0, 50)
                if rating in (1, 5):
                    base_votes = int(base_votes * 1.5)
                if len(body) > 200:
                    base_votes = int(base_votes * 1.3)
                helpful_votes = max(0, base_votes)

                records.append({
                    "review_id": self._uuid(),
                    "product_id": product_id,
                    "customer_id": cid,
                    "order_id": order_id,
                    "rating": rating,
                    "title": title,
                    "body": body,
                    "created_at": review_date,
                    "is_verified_purchase": is_verified,
                    "helpful_votes": helpful_votes,
                })

        df = pl.DataFrame(records)
        if df.height > 0:
            df = df.cast({
                "rating": pl.Int64,
                "created_at": pl.Date,
                "is_verified_purchase": pl.Boolean,
                "helpful_votes": pl.Int64,
            })
        return df

    def _generate_body(self, rating: int, product_type: str) -> str:
        """Generate a review body with template filling."""
        templates = REVIEW_BODIES.get(rating, REVIEW_BODIES[3])
        template = self.rng.choice(templates)

        return template.format(
            product_type=product_type,
            weeks=self.rng.randint(1, 12),
            days=self.rng.randint(1, 30),
            feature=self.rng.choice(FEATURES),
            positive_action=self.rng.choice(POSITIVE_ACTIONS),
            minor_issue=self.rng.choice(MINOR_ISSUES),
            negative_aspect=self.rng.choice(NEGATIVE_ASPECTS),
            broke_action=self.rng.choice(BROKE_ACTIONS),
        )
