"""Web clickstream generator.

Generates realistic browsing sessions with proper funnel modeling:
  page_view → search → product_view → add_to_cart → begin_checkout → purchase

Sessions have different profiles (bounce, browse, shopping, research)
and only ~2-4% convert to purchases.
"""

from __future__ import annotations

from datetime import timedelta

import polars as pl

from ..persona import CustomerPersona
from ..utils.temporal import random_date_in_range, random_timestamp
from .base import BaseGenerator


# Session types with funnel definitions
SESSION_PROFILES = {
    "bounce": {
        "weight": 0.30,
        "events": ["page_view"],
        "duration_minutes": (0.1, 0.5),
    },
    "quick_browse": {
        "weight": 0.25,
        "events": ["page_view", "page_view", "product_view"],
        "duration_minutes": (1, 5),
    },
    "search_browse": {
        "weight": 0.20,
        "events": ["page_view", "search", "product_view", "product_view", "filter_products"],
        "duration_minutes": (3, 15),
    },
    "engaged_browse": {
        "weight": 0.10,
        "events": ["page_view", "search", "product_view", "product_view", "sort_products", "product_view", "add_to_wishlist"],
        "duration_minutes": (5, 25),
    },
    "cart_abandon": {
        "weight": 0.08,
        "events": ["page_view", "search", "product_view", "add_to_cart", "product_view", "add_to_cart"],
        "duration_minutes": (5, 20),
    },
    "checkout_abandon": {
        "weight": 0.04,
        "events": ["page_view", "product_view", "add_to_cart", "apply_coupon", "begin_checkout"],
        "duration_minutes": (8, 30),
    },
    "purchase": {
        "weight": 0.03,
        "events": ["page_view", "search", "product_view", "add_to_cart", "product_view", "add_to_cart", "begin_checkout", "purchase"],
        "duration_minutes": (10, 45),
    },
}

REFERRERS = ["google", "facebook", "direct", "email", "instagram", "bing", "twitter", "tiktok", "pinterest", "youtube", "reddit", "affiliate"]
REFERRER_WEIGHTS = [0.30, 0.12, 0.25, 0.10, 0.06, 0.04, 0.03, 0.03, 0.02, 0.02, 0.02, 0.01]

BROWSERS = ["Chrome", "Safari", "Firefox", "Edge", "Samsung Internet", "Opera"]
BROWSER_WEIGHTS = [0.55, 0.20, 0.10, 0.08, 0.05, 0.02]

OPERATING_SYSTEMS = ["Windows", "macOS", "iOS", "Android", "Linux", "ChromeOS"]
OS_WEIGHTS = [0.30, 0.15, 0.25, 0.22, 0.05, 0.03]

DEVICE_TYPES = ["desktop", "mobile", "tablet"]
DEVICE_WEIGHTS = [0.35, 0.50, 0.15]

# Device → OS compatibility
DEVICE_OS_MAP = {
    "desktop": ["Windows", "macOS", "Linux", "ChromeOS"],
    "mobile": ["iOS", "Android"],
    "tablet": ["iOS", "Android"],
}

DEVICE_BROWSER_MAP = {
    "desktop": ["Chrome", "Safari", "Firefox", "Edge", "Opera"],
    "mobile": ["Chrome", "Safari", "Samsung Internet", "Firefox"],
    "tablet": ["Chrome", "Safari", "Firefox"],
}

SEARCH_QUERIES = [
    "running shoes", "wireless headphones", "laptop bag", "yoga mat",
    "coffee maker", "winter jacket", "face moisturizer", "desk lamp",
    "bluetooth speaker", "hiking boots", "organic protein", "smartwatch",
    "throw pillow", "gaming mouse", "sunscreen SPF 50", "water bottle",
    "backpack", "phone case", "air fryer", "resistance bands",
    "vitamins", "candle set", "hoodie", "earbuds", "kitchen knife set",
    "yoga pants", "sneakers", "foundation makeup", "board game",
    "weighted blanket", "electric toothbrush", "watch band", "socks pack",
    "portable charger", "dog food", "hair dryer", "cast iron skillet",
    "mens jeans", "womens dress", "protein bars", "office chair",
]

PAGE_URLS = [
    "/", "/shop", "/new-arrivals", "/sale", "/bestsellers",
    "/account/login", "/account/register", "/cart", "/checkout",
    "/about", "/contact", "/shipping-info", "/returns",
    "/blog", "/gift-cards", "/rewards", "/brand/{brand}",
    "/category/{category}", "/deals", "/clearance",
]


class ClickstreamGenerator(BaseGenerator):
    """Generate web clickstream events."""

    def iter_generate(
        self,
        *,
        customers: pl.DataFrame,
        products: pl.DataFrame,
        orders_online: pl.DataFrame | None = None,
        ad_campaigns: pl.DataFrame | None = None,
        chunk_size: int | None = None,
        **deps,
    ):
        """Yield clickstream DataFrame chunks to support 50M+ row generation with bounded RAM."""
        target = self.config.tier.clickstream_events
        c_size = chunk_size or getattr(self.config, "chunk_size", 500_000) or 500_000
        personas: dict[str, CustomerPersona] = customers.__dict__.get("_personas", {})
        customer_ids = customers["customer_id"].to_list()
        product_list = products.filter(pl.col("is_active")).to_dicts()
        categories = list(set(p["category"] for p in product_list))

        campaigns_by_source: dict[str, list[dict]] = {}
        if ad_campaigns is not None and not ad_campaigns.is_empty():
            for c_row in ad_campaigns.select(["campaign_id", "utm_source", "utm_medium"]).to_dicts():
                campaigns_by_source.setdefault(c_row["utm_source"], []).append(c_row)

        # Persistent browser/device anonymous_id (cookie) per customer & device for pre-login stitching
        cust_anon_ids: dict[tuple[str, str], str] = {}
        for cid in customer_ids:
            cust_anon_ids[(cid, "desktop")] = self._uuid()
            cust_anon_ids[(cid, "mobile")] = self._uuid()
            cust_anon_ids[(cid, "tablet")] = self._uuid()

        records: list[dict] = []
        event_count = 0

        def _flush_chunk() -> pl.DataFrame:
            df = pl.DataFrame(
                records,
                schema_overrides={
                    "product_id": pl.String,
                    "search_query": pl.String,
                    "cart_value": pl.Float64,
                    "utm_source": pl.String,
                    "utm_medium": pl.String,
                    "utm_campaign": pl.String,
                },
            )
            if df.height > 0:
                df = df.cast({
                    "event_timestamp": pl.Datetime,
                    "cart_value": pl.Float64,
                })
            records.clear()
            return df

        # 1. Generate linked purchase sessions for actual online orders
        has_orders = orders_online is not None and not orders_online.is_empty()
        if has_orders:
            order_rows = orders_online.select([
                "customer_id", "order_date", "device_type", "session_id", "total_amount"
            ]).to_dicts()
            for ord_row in order_rows:
                if event_count >= target:
                    break
                remaining = target - event_count
                cid = ord_row["customer_id"]
                persona = personas.get(cid)
                base_events = list(SESSION_PROFILES["purchase"]["events"])
                events = self._expand_events(base_events, persona)
                if len(events) > remaining:
                    events = events[-remaining:]
                if not events:
                    break

                anon_id = cust_anon_ids.get((cid, ord_row["device_type"]), self._uuid()) if cid else self._uuid()
                session_records = self._build_session_records(
                    events=events,
                    session_id=ord_row["session_id"],
                    anonymous_id=anon_id,
                    cid=cid,
                    persona=persona,
                    device=ord_row["device_type"],
                    end_timestamp=ord_row["order_date"],
                    final_cart_value=ord_row["total_amount"],
                    product_list=product_list,
                    categories=categories,
                    campaigns_by_source=campaigns_by_source,
                )
                records.extend(session_records)
                event_count += len(session_records)

                if len(records) >= c_size:
                    yield _flush_chunk()

        # 2. Fill remaining budget with non-converting / browsing sessions
        while event_count < target:
            remaining = target - event_count

            # Pick a customer (70% logged in, 30% anonymous)
            if self.rng.random() < 0.70 and customer_ids:
                cid = self.rng.choice(customer_ids)
                persona = personas.get(cid)
            else:
                cid = None
                persona = None

            # Pick session profile, weighted by persona
            session_type = self._pick_session_type(persona, allow_purchase=not has_orders)
            profile = SESSION_PROFILES[session_type]
            base_events = list(profile["events"])

            # Add realistic variation: sometimes extra product views, repeat searches
            events = self._expand_events(base_events, persona)

            if event_count + len(events) > target:
                events = events[:remaining]
            if not events:
                break

            device = self._pick_weighted(DEVICE_TYPES, DEVICE_WEIGHTS)
            if cid is not None:
                anon_id = cust_anon_ids.get((cid, device), self._uuid())
            elif customer_ids and self.rng.random() < 0.40:
                # Simulate pre-login browsing on a known customer's persistent device cookie
                anon_cid = self.rng.choice(customer_ids)
                anon_id = cust_anon_ids.get((anon_cid, device), self._uuid())
            else:
                anon_id = self._uuid()

            session_date = random_date_in_range(
                self.rng,
                self.config.date_range.start,
                self.config.date_range.end,
                self.config,
            )
            session_start = random_timestamp(self.rng, session_date, "online")

            session_records = self._build_session_records(
                events=events,
                session_id=self._uuid(),
                anonymous_id=anon_id,
                cid=cid,
                persona=persona,
                device=device,
                start_timestamp=session_start,
                product_list=product_list,
                categories=categories,
                campaigns_by_source=campaigns_by_source,
            )
            records.extend(session_records)
            event_count += len(session_records)

            if len(records) >= c_size:
                yield _flush_chunk()

        if records or event_count == 0:
            yield _flush_chunk()

    def generate(
        self,
        *,
        customers: pl.DataFrame,
        products: pl.DataFrame,
        orders_online: pl.DataFrame | None = None,
        ad_campaigns: pl.DataFrame | None = None,
        **deps,
    ) -> pl.DataFrame:
        if ad_campaigns is not None:
            deps["ad_campaigns"] = ad_campaigns
        chunks = list(
            self.iter_generate(
                customers=customers,
                products=products,
                orders_online=orders_online,
                chunk_size=self.config.tier.clickstream_events + 1,
                **deps,
            )
        )
        return pl.concat(chunks) if len(chunks) > 1 else chunks[0]

    def _build_session_records(
        self,
        *,
        events: list[str],
        session_id: str,
        anonymous_id: str,
        cid: str | None,
        persona: CustomerPersona | None,
        device: str,
        product_list: list[dict],
        categories: list[str],
        start_timestamp=None,
        end_timestamp=None,
        final_cart_value: float | None = None,
        campaigns_by_source: dict[str, list[dict]] | None = None,
    ) -> list[dict]:
        """Build ordered clickstream event rows for a single session."""
        browser = self.rng.choice(DEVICE_BROWSER_MAP.get(device, BROWSERS))
        os = self.rng.choice(DEVICE_OS_MAP.get(device, OPERATING_SYSTEMS))
        referrer = self._pick_weighted(REFERRERS, REFERRER_WEIGHTS)
        ip = f"{self.rng.randint(10, 223)}.{self.rng.randint(0, 255)}.{self.rng.randint(0, 255)}.xxx"

        utm_source = None
        utm_medium = None
        utm_campaign = None
        if campaigns_by_source:
            src_key = "facebook" if referrer == "instagram" else referrer
            matching = campaigns_by_source.get(src_key)
            if matching and self.rng.random() < 0.70:
                chosen_camp = self.rng.choice(matching)
                utm_source = referrer
                utm_medium = chosen_camp["utm_medium"]
                utm_campaign = chosen_camp["campaign_id"]
            elif referrer == "email":
                utm_source = "email"
                utm_medium = "crm"

        gaps = [timedelta(seconds=self.rng.uniform(3, 120)) for _ in events]
        if end_timestamp is not None:
            total_dur = sum((g for g in gaps), timedelta())
            current_time = end_timestamp - total_dur
        else:
            current_time = start_timestamp

        session_records: list[dict] = []
        cart_value = 0.0
        viewed_products: list[dict] = []

        for event_type, gap in zip(events, gaps):
            current_time = current_time + gap

            product_id = None
            search_query = None
            page_url = "/"

            if event_type == "page_view":
                page_url = self.rng.choice(PAGE_URLS)
                if "{category}" in page_url:
                    page_url = page_url.replace("{category}", self.rng.choice(categories).lower().replace(" ", "-"))
                if "{brand}" in page_url:
                    brand = self.rng.choice(product_list)["brand"]
                    page_url = page_url.replace("{brand}", brand.lower().replace(" ", "-"))

            elif event_type == "product_view":
                prod = self._pick_product(persona, product_list, categories)
                product_id = prod["product_id"]
                page_url = f"/products/{product_id}"
                viewed_products.append(prod)

            elif event_type == "search":
                search_query = self.rng.choice(SEARCH_QUERIES)
                page_url = f"/search?q={search_query.replace(' ', '+')}"

            elif event_type == "add_to_cart":
                if viewed_products:
                    prod = self.rng.choice(viewed_products)
                else:
                    prod = self._pick_product(persona, product_list, categories)
                product_id = prod["product_id"]
                cart_value += prod["price"]
                cart_value = round(cart_value, 2)
                page_url = f"/products/{product_id}"

            elif event_type == "remove_from_cart":
                if viewed_products:
                    prod = self.rng.choice(viewed_products)
                    product_id = prod["product_id"]
                    cart_value = max(0, cart_value - prod["price"])
                page_url = "/cart"

            elif event_type == "begin_checkout":
                page_url = "/checkout"

            elif event_type == "purchase":
                page_url = "/checkout/confirmation"
                if final_cart_value is not None:
                    cart_value = round(final_cart_value, 2)

            elif event_type == "add_to_wishlist":
                if viewed_products:
                    prod = self.rng.choice(viewed_products)
                    product_id = prod["product_id"]
                page_url = "/wishlist"

            elif event_type == "apply_coupon":
                page_url = "/cart"

            elif event_type in ("filter_products", "sort_products"):
                page_url = f"/category/{self.rng.choice(categories).lower().replace(' ', '-')}"

            elif event_type == "login":
                page_url = "/account/login"

            elif event_type == "signup":
                page_url = "/account/register"

            session_records.append({
                "event_id": self._uuid(),
                "session_id": session_id,
                "anonymous_id": anonymous_id,
                "customer_id": cid,
                "event_timestamp": current_time,
                "event_type": event_type,
                "page_url": page_url,
                "referrer": referrer,
                "utm_source": utm_source,
                "utm_medium": utm_medium,
                "utm_campaign": utm_campaign,
                "device_type": device,
                "browser": browser,
                "os": os,
                "ip_address": ip,
                "product_id": product_id,
                "search_query": search_query,
                "cart_value": cart_value if event_type in ("add_to_cart", "remove_from_cart", "begin_checkout", "purchase") else None,
            })

        return session_records

    def _pick_session_type(self, persona: CustomerPersona | None, allow_purchase: bool = True) -> str:
        """Pick a session type weighted by persona's browse-to-buy rate."""
        profiles = list(SESSION_PROFILES.keys())
        weights = [SESSION_PROFILES[p]["weight"] for p in profiles]

        purchase_idx = profiles.index("purchase")
        if not allow_purchase:
            weights[purchase_idx] = 0.0
        elif persona:
            # Boost purchase sessions for high-converting personas
            if persona.browse_to_buy > 0.05:
                weights[purchase_idx] *= (persona.browse_to_buy / 0.03)
            elif persona.browse_to_buy == 0:
                weights[purchase_idx] = 0.001
                # Boost browse sessions instead
                weights[profiles.index("engaged_browse")] *= 2.0

            # Fraudsters have unusual session patterns
            if persona.is_fraudster:
                if persona.fraud_type == "card_testing":
                    # Very short sessions, jump straight to purchase (7 profiles total)
                    weights = [0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.70]
                elif persona.fraud_type == "velocity_spike":
                    weights[purchase_idx] *= 3.0

        return self._pick_weighted(profiles, weights)

    def _expand_events(
        self,
        base_events: list[str],
        persona: CustomerPersona | None,
    ) -> list[str]:
        """Add realistic variation to the base event sequence."""
        expanded = []
        for event in base_events:
            expanded.append(event)

            # Sometimes add extra product views
            if event == "product_view" and self.rng.random() < 0.3:
                expanded.append("product_view")

            # Sometimes add a search after a page view
            if event == "page_view" and self.rng.random() < 0.15:
                expanded.append("search")

            # Occasionally remove from cart
            if event == "add_to_cart" and self.rng.random() < 0.1:
                expanded.append("remove_from_cart")

            # Login before checkout sometimes
            if event == "begin_checkout" and self.rng.random() < 0.2:
                expanded.insert(-1, "login")

        return expanded

    def _pick_product(
        self,
        persona: CustomerPersona | None,
        products: list[dict],
        categories: list[str],
    ) -> dict:
        """Pick a product based on persona preferences."""
        if persona and persona.preferred_categories and self.rng.random() < 0.70:
            cat = self.rng.choice(persona.preferred_categories)
            filtered = [p for p in products if p["category"] == cat]
            if filtered:
                return self.rng.choice(filtered)
        return self.rng.choice(products)
