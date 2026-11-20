"""Paid media & Marketing Mix Modeling (MMM) generator.

Produces:
- ad_campaigns: paid media campaign catalog across search, social, video, and retail media
- ad_spend_daily: daily channel x campaign x region spend, impressions, clicks,
  platform-reported conversions, and Geo-Lift holdout flags
"""

from __future__ import annotations

from datetime import timedelta
import math

import polars as pl

from ..utils.temporal import seasonal_multiplier
from .base import BaseGenerator


PAID_CHANNELS = [
    ("google_search", "google", "cpc", 0.34, (12.0, 28.0), (0.030, 0.065)),
    ("meta_ads", "facebook", "paid_social", 0.30, (7.0, 16.0), (0.012, 0.028)),
    ("tiktok", "tiktok", "paid_social", 0.16, (5.0, 12.0), (0.010, 0.024)),
    ("youtube", "youtube", "video", 0.12, (8.0, 18.0), (0.006, 0.015)),
    ("retail_media", "affiliate", "sponsored", 0.08, (10.0, 22.0), (0.022, 0.048)),
]

OBJECTIVES = ["prospecting", "retargeting", "brand"]
OBJECTIVE_WEIGHTS = [0.55, 0.25, 0.20]

CAMPAIGN_THEMES = [
    "AlwaysOn_Core", "Q4_Holiday_Push", "Spring_NewArrivals",
    "Summer_Clearance", "VIP_Lookalike", "Dynamic_Retargeting",
    "Brand_Awareness", "BackToSchool", "Category_Hero",
]


class MarketingGenerator(BaseGenerator):
    """Generate paid media campaigns and daily ad spend for MMM & attribution."""

    def generate(self, **deps) -> dict[str, pl.DataFrame]:
        start_date = self.config.date_range.start
        end_date = self.config.date_range.end
        regions = getattr(self.config, "regions", ["US"]) or ["US"]
        tier_scale = max(1.0, math.sqrt(self.config.tier.customers / 500.0))

        campaigns: list[dict] = []
        campaign_meta: list[dict] = []

        # 15 campaigns across the 5 paid channels
        for idx in range(15):
            channel, utm_src, utm_med, weight, cpm_range, ctr_range = PAID_CHANNELS[idx % len(PAID_CHANNELS)]
            objective = self._pick_weighted(OBJECTIVES, OBJECTIVE_WEIGHTS)
            theme = CAMPAIGN_THEMES[idx % len(CAMPAIGN_THEMES)]
            cid = f"AD-{idx + 1:04d}"

            # Holdout-eligible campaigns (20% of campaigns run a 30-day geo-lift holdout)
            is_holdout_enabled = (idx % 5 == 0)
            daily_budget = round(self.rng.uniform(180.0, 1200.0) * weight * 3.0 * tier_scale, 2)

            campaigns.append({
                "campaign_id": cid,
                "campaign_name": f"{channel}_{objective}_{theme}",
                "channel": channel,
                "objective": objective,
                "utm_source": utm_src,
                "utm_medium": utm_med,
                "daily_budget_usd": daily_budget,
                "start_date": start_date,
                "end_date": end_date,
                "is_holdout_enabled": is_holdout_enabled,
            })
            campaign_meta.append({
                "campaign_id": cid,
                "channel": channel,
                "objective": objective,
                "daily_budget_usd": daily_budget,
                "cpm_range": cpm_range,
                "ctr_range": ctr_range,
                "is_holdout_enabled": is_holdout_enabled,
            })

        # Geo-lift holdout window: 30 days in the final quarter on the first region
        holdout_region = regions[0]
        holdout_end = end_date - timedelta(days=15)
        holdout_start = max(start_date, holdout_end - timedelta(days=29))

        spend_rows: list[dict] = []
        total_days = max(1, (end_date - start_date).days + 1)

        for day_offset in range(total_days):
            cur_date = start_date + timedelta(days=day_offset)
            mult = seasonal_multiplier(self.config, cur_date)
            in_holdout_window = holdout_start <= cur_date <= holdout_end

            for cm in campaign_meta:
                for reg in regions:
                    is_holdout = bool(cm["is_holdout_enabled"] and in_holdout_window and reg == holdout_region)
                    if is_holdout:
                        spend_usd = 0.0
                        impressions = 0
                        clicks = 0
                        conv_reported = 0
                    else:
                        reg_share = 1.0 / len(regions)
                        jitter = self.rng.uniform(0.78, 1.25)
                        spend_usd = round(cm["daily_budget_usd"] * reg_share * mult * jitter, 2)
                        cpm = self.rng.uniform(*cm["cpm_range"]) * (1.15 if mult > 1.3 else 1.0)
                        impressions = max(100, int((spend_usd / cpm) * 1000))
                        ctr = self.rng.uniform(*cm["ctr_range"])
                        clicks = max(1, int(impressions * ctr))
                        # Hill diminishing returns + platform over-attribution (~15-25%)
                        effective_cvr = 0.035 if cm["objective"] == "retargeting" else 0.018
                        sat = spend_usd / (spend_usd + 450.0 * tier_scale)
                        conv_reported = max(0, int(round(clicks * effective_cvr * (0.7 + sat) * self.rng.uniform(1.10, 1.25))))

                    spend_rows.append({
                        "spend_id": self._uuid(),
                        "spend_date": cur_date,
                        "campaign_id": cm["campaign_id"],
                        "channel": cm["channel"],
                        "region": reg,
                        "impressions": impressions,
                        "clicks": clicks,
                        "spend_usd": spend_usd,
                        "attributed_conversions_reported": conv_reported,
                        "is_holdout": is_holdout,
                    })

        campaigns_df = pl.DataFrame(campaigns).cast({
            "daily_budget_usd": pl.Float64,
            "start_date": pl.Date,
            "end_date": pl.Date,
            "is_holdout_enabled": pl.Boolean,
        })

        spend_df = pl.DataFrame(spend_rows).cast({
            "spend_date": pl.Date,
            "impressions": pl.Int64,
            "clicks": pl.Int64,
            "spend_usd": pl.Float64,
            "attributed_conversions_reported": pl.Int64,
            "is_holdout": pl.Boolean,
        }) if spend_rows else pl.DataFrame(schema={
            "spend_id": pl.Utf8, "spend_date": pl.Date, "campaign_id": pl.Utf8,
            "channel": pl.Utf8, "region": pl.Utf8, "impressions": pl.Int64,
            "clicks": pl.Int64, "spend_usd": pl.Float64,
            "attributed_conversions_reported": pl.Int64, "is_holdout": pl.Boolean,
        })

        return {
            "ad_campaigns": campaigns_df,
            "ad_spend_daily": spend_df,
        }
