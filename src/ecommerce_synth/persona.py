"""Customer persona engine.

Each customer is assigned a persona that drives their behaviour across
every domain: order frequency, cart size, loyalty enrolment, email
engagement, browsing patterns, fraud risk, and return/review rates.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import GenerationConfig


# ---------------------------------------------------------------------------
# Persona dataclass — holds resolved per-customer behaviour parameters
# ---------------------------------------------------------------------------

@dataclass
class CustomerPersona:
    """Resolved persona for a single customer."""

    persona_name: str
    orders_per_year: int
    loyalty_tier: str | None
    email_open_rate: float
    email_click_rate: float
    browse_to_buy: float
    avg_cart_items: int
    preferred_categories: list[str] | None
    return_rate: float
    review_rate: float
    always_uses_coupon: bool
    is_fraudster: bool = False
    fraud_type: str | None = None

    # Derived
    is_omnichannel: bool = False
    customer_segment: str = "new"


# ---------------------------------------------------------------------------
# Fraud sub-types with distinctive behaviour signatures
# ---------------------------------------------------------------------------

FRAUD_TYPES = [
    "card_testing",
    "account_takeover",
    "promo_abuse",
    "refund_abuse",
    "synthetic_identity",
    "velocity_spike",
]

FRAUD_BEHAVIOUR: dict[str, dict] = {
    "card_testing": {
        "orders_per_year": (15, 40),
        "avg_cart_items": (1, 1),
        "browse_to_buy": 0.90,  # barely browses, just transacts
        "return_rate": 0.0,
    },
    "account_takeover": {
        "orders_per_year": (5, 15),
        "avg_cart_items": (3, 8),
        "browse_to_buy": 0.70,
        "return_rate": 0.0,
    },
    "promo_abuse": {
        "orders_per_year": (8, 20),
        "avg_cart_items": (2, 5),
        "browse_to_buy": 0.30,
        "return_rate": 0.05,
        "always_uses_coupon": True,
    },
    "refund_abuse": {
        "orders_per_year": (4, 10),
        "avg_cart_items": (2, 4),
        "browse_to_buy": 0.15,
        "return_rate": 0.60,  # extremely high return rate
    },
    "synthetic_identity": {
        "orders_per_year": (3, 8),
        "avg_cart_items": (2, 6),
        "browse_to_buy": 0.40,
        "return_rate": 0.02,
    },
    "velocity_spike": {
        "orders_per_year": (20, 50),
        "avg_cart_items": (1, 3),
        "browse_to_buy": 0.60,
        "return_rate": 0.01,
    },
}


# ---------------------------------------------------------------------------
# PersonaEngine — assigns personas to customers
# ---------------------------------------------------------------------------

class PersonaEngine:
    """Assigns and resolves personas for a population of customers."""

    def __init__(self, config: GenerationConfig, rng: random.Random):
        self.config = config
        self.rng = rng
        self._all_categories = list(config.categories.keys())

        # Build cumulative distribution of persona shares
        self._persona_names: list[str] = []
        self._persona_weights: list[float] = []
        for name, pcfg in config.personas.items():
            self._persona_names.append(name)
            self._persona_weights.append(pcfg.share)

    def assign(self, customer_index: int, total_customers: int) -> CustomerPersona:
        """Assign a persona to a customer.

        Has a ``fraud_rate`` chance of producing a Fraudster persona instead
        of a normal persona.
        """
        # Decide fraud vs normal
        if self.rng.random() < self.config.fraud_rate:
            return self._make_fraudster()

        # Weighted random persona
        name = self.rng.choices(
            self._persona_names, weights=self._persona_weights, k=1
        )[0]
        pcfg = self.config.personas[name]

        orders = self.rng.randint(*pcfg.orders_per_year)

        loyalty = None
        if pcfg.loyalty_tier:
            loyalty = self.rng.choice(pcfg.loyalty_tier)

        # Resolve preferred categories
        pref_cats = None
        if pcfg.preferred_categories:
            pref_cats = self.rng.sample(
                self._all_categories,
                min(pcfg.preferred_categories, len(self._all_categories)),
            )

        # Slight per-customer jitter on rates (±20%)
        jitter = lambda v: max(0.0, min(1.0, v * self.rng.uniform(0.8, 1.2)))

        is_omni = self.rng.random() < self.config.omnichannel_rate

        # Segment assignment
        if orders == 0:
            segment = "churned"
        elif orders <= 1:
            segment = "new"
        elif orders <= 6:
            segment = "returning"
        else:
            segment = "vip"

        return CustomerPersona(
            persona_name=name,
            orders_per_year=orders,
            loyalty_tier=loyalty,
            email_open_rate=jitter(pcfg.email_open_rate),
            email_click_rate=jitter(pcfg.email_click_rate),
            browse_to_buy=jitter(pcfg.browse_to_buy),
            avg_cart_items=self.rng.randint(*pcfg.avg_cart_items) if pcfg.avg_cart_items[1] > 0 else 0,
            preferred_categories=pref_cats,
            return_rate=jitter(pcfg.return_rate),
            review_rate=jitter(pcfg.review_rate),
            always_uses_coupon=pcfg.always_uses_coupon,
            is_omnichannel=is_omni,
            customer_segment=segment,
        )

    def _make_fraudster(self) -> CustomerPersona:
        """Create a fraudster persona with distinctive behaviour."""
        fraud_type = self.rng.choice(FRAUD_TYPES)
        fb = FRAUD_BEHAVIOUR[fraud_type]

        orders_range = fb["orders_per_year"]
        cart_range = fb["avg_cart_items"]

        return CustomerPersona(
            persona_name="fraudster",
            orders_per_year=self.rng.randint(*orders_range),
            loyalty_tier=None,
            email_open_rate=0.05,
            email_click_rate=0.01,
            browse_to_buy=fb["browse_to_buy"],
            avg_cart_items=self.rng.randint(*cart_range),
            preferred_categories=None,
            return_rate=fb["return_rate"],
            review_rate=0.0,
            always_uses_coupon=fb.get("always_uses_coupon", False),
            is_fraudster=True,
            fraud_type=fraud_type,
            is_omnichannel=False,
            customer_segment="new",
        )
