"""Configuration loader and validation."""

from __future__ import annotations

import os
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_CONFIG_DIR = _PROJECT_ROOT / "config"


# ---------------------------------------------------------------------------
# Pydantic models for typed, validated configuration
# ---------------------------------------------------------------------------

class DateRangeConfig(BaseModel):
    start: date
    end: date


class TierConfig(BaseModel):
    customers: int
    online_orders: int
    instore_transactions: int
    clickstream_events: int
    emails_sent: int
    loyalty_members: int
    support_tickets: int
    ab_experiments: int


class ShippingRates(BaseModel):
    standard: list[float]
    express: list[float]
    overnight: list[float]


class ShippingConfig(BaseModel):
    free_threshold: float
    rates: ShippingRates
    standard_pct: float
    express_pct: float
    overnight_pct: float


class CategoryConfig(BaseModel):
    subcategories: list[str]
    price_range: list[float]
    brands: list[str]
    weight_range: list[float]


class PersonaConfig(BaseModel):
    share: float
    orders_per_year: list[int]
    loyalty_tier: list[str] | None = None
    email_open_rate: float
    email_click_rate: float
    browse_to_buy: float
    avg_cart_items: list[int]
    preferred_categories: int | None = None
    return_rate: float
    review_rate: float
    always_uses_coupon: bool = False


class EmailConfig(BaseModel):
    delivery_rate: float
    campaigns_per_month: int
    types: list[str]


class GenerationConfig(BaseModel):
    """Top-level generation configuration."""

    date_range: DateRangeConfig
    product_count: int = 2000
    store_count: int = 50
    fraud_rate: float = 0.02
    personas: dict[str, PersonaConfig]
    omnichannel_rate: float = 0.30
    seasonality: dict[int, float]
    email: EmailConfig
    categories: dict[str, CategoryConfig]
    tax_rates: dict[str, float]
    shipping: ShippingConfig

    # Tier info (populated at load time)
    tier_name: str = "small"
    tier: TierConfig = Field(
        default_factory=lambda: TierConfig(
            customers=500,
            online_orders=1000,
            instore_transactions=500,
            clickstream_events=50000,
            emails_sent=5000,
            loyalty_members=300,
            support_tickets=150,
            ab_experiments=10,
        )
    )

    # Runtime options
    seed: int = 42
    output_dir: Path = Path("output")


# ---------------------------------------------------------------------------
# Loading helpers
# ---------------------------------------------------------------------------

def _load_yaml(path: Path) -> dict[str, Any]:
    with open(path) as f:
        return yaml.safe_load(f)


def load_config(
    tier_name: str = "small",
    seed: int = 42,
    output_dir: str | Path | None = None,
    fraud_rate: float | None = None,
    config_dir: Path | None = None,
) -> GenerationConfig:
    """Load and merge default config with the requested tier."""

    cfg_dir = config_dir or _CONFIG_DIR

    default_data = _load_yaml(cfg_dir / "default.yaml")
    tiers_data = _load_yaml(cfg_dir / "volume_tiers.yaml")

    if tier_name not in tiers_data["tiers"]:
        raise ValueError(
            f"Unknown tier '{tier_name}'. Available: {list(tiers_data['tiers'].keys())}"
        )

    tier_cfg = TierConfig(**tiers_data["tiers"][tier_name])

    # Override fraud rate if provided
    if fraud_rate is not None:
        default_data["fraud_rate"] = fraud_rate

    config = GenerationConfig(
        **default_data,
        tier_name=tier_name,
        tier=tier_cfg,
        seed=seed,
    )

    if output_dir:
        config.output_dir = Path(output_dir)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        config.output_dir = Path("output") / f"{tier_name}_{timestamp}"

    return config
