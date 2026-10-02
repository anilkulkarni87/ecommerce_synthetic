"""Product catalog generator.

Generates a realistic product catalog with proper category/subcategory
hierarchies, brand assignments, price distributions, and seasonal
availability.  The catalog is a fixed-size dimension (~2 000 products)
that does NOT scale with volume tiers.
"""

from __future__ import annotations

import random
from datetime import date, timedelta

import polars as pl

from .base import BaseGenerator


class ProductGenerator(BaseGenerator):
    """Generate the product catalog."""

    def generate(self, **deps) -> pl.DataFrame:
        n = self.config.product_count
        categories = self.config.categories
        start_date = self.config.date_range.start
        end_date = self.config.date_range.end

        records: list[dict] = []
        sku_counter = 1

        # Distribute products across categories proportionally
        cat_names = list(categories.keys())
        # Weight: Electronics & Apparel get more SKUs
        cat_weights = {
            "Electronics": 1.3,
            "Apparel": 1.4,
            "Home & Kitchen": 1.1,
            "Beauty & Personal Care": 1.0,
            "Sports & Outdoors": 0.9,
            "Grocery & Gourmet": 0.8,
        }

        total_weight = sum(cat_weights.get(c, 1.0) for c in cat_names)
        cat_counts = {}
        allocated = 0
        for i, cat in enumerate(cat_names):
            w = cat_weights.get(cat, 1.0)
            count = int(round(n * w / total_weight))
            if i == len(cat_names) - 1:
                count = n - allocated  # fix rounding
            cat_counts[cat] = count
            allocated += count

        for cat_name, count in cat_counts.items():
            cat_cfg = categories[cat_name]
            subcats = cat_cfg.subcategories
            brands = cat_cfg.brands
            price_lo, price_hi = cat_cfg.price_range
            weight_lo, weight_hi = cat_cfg.weight_range

            for _ in range(count):
                subcat = self.rng.choice(subcats)
                brand = self.rng.choice(brands)

                # Log-normal price distribution (more cheap items, fewer expensive)
                import math
                mu = math.log((price_lo + price_hi) / 3)  # skew towards lower
                sigma = 0.8
                price = max(price_lo, min(price_hi, self.rng.lognormvariate(mu, sigma)))
                price = round(price, 2)

                # Cost is 40-70% of retail
                cost_ratio = self.rng.uniform(0.40, 0.70)
                cost = round(price * cost_ratio, 2)

                weight = round(self.rng.uniform(weight_lo, weight_hi), 2)

                # Product listing date: most products exist from the start,
                # but ~15% are "new arrivals" added later
                if self.rng.random() < 0.85:
                    created = start_date - timedelta(days=self.rng.randint(30, 365))
                else:
                    created = start_date + timedelta(
                        days=self.rng.randint(0, (end_date - start_date).days)
                    )

                # Generate realistic product name
                product_name = self._generate_product_name(brand, subcat, cat_name)

                # Ratings: bell curve centered at 4.0
                avg_rating = max(1.0, min(5.0, self.rng.gauss(4.0, 0.7)))
                avg_rating = round(avg_rating, 1)

                # Review count correlated with price (cheaper items get more reviews)
                base_reviews = max(0, int(self.rng.expovariate(0.01)))
                review_count = min(5000, base_reviews)

                # ~5% of products are discontinued
                is_active = self.rng.random() > 0.05

                records.append({
                    "product_id": f"SKU-{sku_counter:05d}",
                    "product_name": product_name,
                    "category": cat_name,
                    "subcategory": subcat,
                    "brand": brand,
                    "price": price,
                    "cost": cost,
                    "weight_kg": weight,
                    "is_active": is_active,
                    "created_at": created,
                    "avg_rating": avg_rating,
                    "review_count": review_count,
                })
                sku_counter += 1

        return pl.DataFrame(records).cast({
            "price": pl.Float64,
            "cost": pl.Float64,
            "weight_kg": pl.Float64,
            "avg_rating": pl.Float64,
            "review_count": pl.Int64,
            "is_active": pl.Boolean,
            "created_at": pl.Date,
        })

    def _generate_product_name(self, brand: str, subcat: str, category: str) -> str:
        """Generate a plausible product name."""
        # Modifiers by category
        modifiers = {
            "Electronics": ["Pro", "Ultra", "Max", "Lite", "Plus", "Elite", "X", "Air", "Neo", "Flex"],
            "Apparel": ["Classic", "Slim", "Relaxed", "Premium", "Essential", "Modern", "Heritage", "Active", "Everyday", "Luxe"],
            "Home & Kitchen": ["Deluxe", "Essential", "Premium", "Compact", "Professional", "Artisan", "Signature", "Classic", "Smart", "Eco"],
            "Beauty & Personal Care": ["Hydrating", "Revitalizing", "Soothing", "Brightening", "Daily", "Intensive", "Natural", "Pure", "Advanced", "Gentle"],
            "Sports & Outdoors": ["Performance", "Elite", "Trail", "Pro", "Core", "Endurance", "Summit", "Velocity", "Flex", "Titan"],
            "Grocery & Gourmet": ["Organic", "Select", "Premium", "Artisan", "Classic", "Farm Fresh", "Reserve", "Golden", "Harvest", "Heritage"],
        }

        mod = self.rng.choice(modifiers.get(category, ["Standard"]))

        # Model number for electronics
        if category == "Electronics":
            model = f"{self.rng.choice('ABCDEFGHJKLMNPRSTUVWXYZ')}{self.rng.randint(100, 9999)}"
            return f"{brand} {mod} {subcat.rstrip('s')} {model}"

        # Size/variant for apparel
        if category == "Apparel":
            styles = ["Fit", "Cut", "Style", "Edition", "Collection"]
            return f"{brand} {mod} {subcat.rstrip('s')} {self.rng.choice(styles)}"

        return f"{brand} {mod} {subcat.rstrip('s')}"
