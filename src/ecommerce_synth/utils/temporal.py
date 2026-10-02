"""Temporal utility functions.

Provides realistic time-of-day, day-of-week, and seasonal distributions
for generating timestamps that mirror real ecommerce patterns.
"""

from __future__ import annotations

import random
from datetime import date, datetime, time, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..config import GenerationConfig


# ---------------------------------------------------------------------------
# Hour-of-day probability distributions (24 buckets)
# ---------------------------------------------------------------------------

# Online shopping peaks evening / late night
ONLINE_HOUR_WEIGHTS = [
    0.8,   # 00
    0.5,   # 01
    0.3,   # 02
    0.2,   # 03
    0.2,   # 04
    0.3,   # 05
    0.5,   # 06
    1.5,   # 07  morning check
    2.0,   # 08
    2.5,   # 09
    2.0,   # 10
    2.0,   # 11
    3.0,   # 12  lunch break
    2.5,   # 13
    2.0,   # 14
    2.0,   # 15
    2.5,   # 16
    3.0,   # 17
    4.0,   # 18
    5.0,   # 19  evening peak
    6.0,   # 20  prime shopping hour
    5.5,   # 21
    4.0,   # 22
    2.0,   # 23
]

# In-store peaks during business hours
INSTORE_HOUR_WEIGHTS = [
    0.0,   # 00  closed
    0.0,   # 01
    0.0,   # 02
    0.0,   # 03
    0.0,   # 04
    0.0,   # 05
    0.0,   # 06
    0.0,   # 07
    0.5,   # 08  early birds
    2.0,   # 09
    4.0,   # 10  opens
    5.0,   # 11
    6.0,   # 12  lunch rush
    5.5,   # 13
    5.0,   # 14
    5.0,   # 15
    5.5,   # 16  after-work
    5.0,   # 17
    4.0,   # 18
    3.0,   # 19
    2.0,   # 20  winding down
    0.5,   # 21  closing
    0.0,   # 22  closed
    0.0,   # 23
]

# Day-of-week weights (Mon=0 .. Sun=6)
ONLINE_DOW_WEIGHTS = [3.0, 3.0, 3.0, 3.5, 4.0, 5.0, 4.5]  # Fri-Sat peak
INSTORE_DOW_WEIGHTS = [1.5, 1.5, 2.0, 2.5, 3.0, 6.0, 5.0]  # Sat peak

# Email send hour distribution (marketing sends cluster 8-10 AM)
EMAIL_HOUR_WEIGHTS = [
    0.2, 0.1, 0.1, 0.1, 0.1, 0.3, 1.0, 2.0,
    6.0, 7.0, 5.0, 3.0, 2.0, 1.5, 1.5, 1.0,
    1.0, 0.8, 0.5, 0.3, 0.2, 0.2, 0.2, 0.1,
]

# Clickstream session duration ranges (minutes) by session type
SESSION_DURATIONS = {
    "bounce": (0.1, 0.5),          # < 30 seconds
    "quick_browse": (1, 5),
    "engaged_browse": (5, 20),
    "shopping": (10, 45),
    "deep_research": (30, 90),
}


def pick_hour(rng: random.Random, channel: str = "online") -> int:
    """Pick a weighted random hour of day for the given channel."""
    weights = ONLINE_HOUR_WEIGHTS if channel == "online" else INSTORE_HOUR_WEIGHTS
    return rng.choices(range(24), weights=weights, k=1)[0]


def pick_dow(rng: random.Random, channel: str = "online") -> int:
    """Pick a weighted random day-of-week (0=Mon, 6=Sun)."""
    weights = ONLINE_DOW_WEIGHTS if channel == "online" else INSTORE_DOW_WEIGHTS
    return rng.choices(range(7), weights=weights, k=1)[0]


def seasonal_multiplier(config: GenerationConfig, d: date) -> float:
    """Return the seasonal multiplier for a given date."""
    return config.seasonality.get(d.month, 1.0)


def random_date_in_range(
    rng: random.Random,
    start: date,
    end: date,
    config: GenerationConfig | None = None,
) -> date:
    """Pick a random date in [start, end], weighted by seasonality if config given."""
    delta_days = (end - start).days
    if delta_days <= 0:
        return start

    if config is None:
        offset = rng.randint(0, delta_days)
        return start + timedelta(days=offset)

    # Build month-weighted sampling
    days: list[date] = []
    weights: list[float] = []
    for i in range(delta_days + 1):
        d = start + timedelta(days=i)
        days.append(d)
        weights.append(config.seasonality.get(d.month, 1.0))

    return rng.choices(days, weights=weights, k=1)[0]


def random_timestamp(
    rng: random.Random,
    d: date,
    channel: str = "online",
) -> datetime:
    """Generate a realistic timestamp for a given date and channel."""
    hour = pick_hour(rng, channel)
    minute = rng.randint(0, 59)
    second = rng.randint(0, 59)
    microsecond = rng.randint(0, 999999)
    return datetime.combine(d, time(hour, minute, second, microsecond))


def random_timestamp_in_range(
    rng: random.Random,
    start: date,
    end: date,
    channel: str = "online",
    config: GenerationConfig | None = None,
) -> datetime:
    """Pick a random date in range, then a realistic time of day."""
    d = random_date_in_range(rng, start, end, config)
    return random_timestamp(rng, d, channel)


def timestamp_after(
    rng: random.Random,
    base: datetime,
    min_hours: float = 0.1,
    max_hours: float = 72.0,
    distribution: str = "lognormal",
) -> datetime:
    """Generate a timestamp some hours after a base timestamp.

    Uses log-normal distribution by default for realistic response times.
    """
    import math

    if distribution == "lognormal":
        # Median around 4 hours, with a long tail
        mu = math.log(4.0)
        sigma = 1.0
        hours = max(min_hours, min(max_hours, rng.lognormvariate(mu, sigma)))
    elif distribution == "uniform":
        hours = rng.uniform(min_hours, max_hours)
    else:
        hours = rng.uniform(min_hours, max_hours)

    return base + timedelta(hours=hours)


def distribute_events_over_range(
    rng: random.Random,
    total: int,
    start: date,
    end: date,
    config: GenerationConfig,
) -> dict[date, int]:
    """Distribute a total event count across dates, weighted by seasonality.

    Returns a dict mapping date -> count.
    """
    delta_days = (end - start).days
    if delta_days <= 0:
        return {start: total}

    # Build daily weights
    days: list[date] = []
    weights: list[float] = []
    for i in range(delta_days + 1):
        d = start + timedelta(days=i)
        days.append(d)
        # Combine seasonality × day-of-week
        season = config.seasonality.get(d.month, 1.0)
        dow_w = ONLINE_DOW_WEIGHTS[d.weekday()]
        weights.append(season * dow_w)

    # Normalize and allocate
    total_weight = sum(weights)
    distribution: dict[date, int] = {}
    allocated = 0
    for d, w in zip(days, weights):
        count = int(round(total * w / total_weight))
        distribution[d] = count
        allocated += count

    # Fix rounding errors
    diff = total - allocated
    if diff != 0:
        # Add/subtract from random days
        for _ in range(abs(diff)):
            d = rng.choice(days)
            distribution[d] = max(0, distribution[d] + (1 if diff > 0 else -1))

    return distribution
