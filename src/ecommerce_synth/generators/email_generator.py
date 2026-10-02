"""Email campaign and engagement generator.

Generates:
- email_campaigns: Marketing campaigns with types, subjects, segments
- email_events: Per-recipient events (sent → delivered → opened → clicked → etc.)

Follows realistic engagement funnels:
  sent(100%) → delivered(~98%) → opened(~20-25%) → clicked(~3-5%)
  With bounced(~1.5%), unsubscribed(~0.5%), spam_reported(~0.1%)
"""

from __future__ import annotations

from datetime import timedelta

import polars as pl

from ..persona import CustomerPersona
from ..utils.temporal import random_date_in_range, random_timestamp
from .base import BaseGenerator


# Campaign subject line templates by type
SUBJECT_TEMPLATES = {
    "promotional": [
        "🔥 {pct}% Off Everything — This Weekend Only!",
        "Flash Sale: Up to {pct}% Off Top Brands",
        "Don't Miss Our Biggest Sale of the Season",
        "Your Exclusive {pct}% Discount Awaits",
        "Limited Time: Buy One Get One {pct}% Off",
        "Summer Savings Start Now — {pct}% Off Sitewide",
        "Early Access: {pct}% Off New Arrivals",
        "Final Hours: {pct}% Off Ends Tonight",
        "Secret Sale: {pct}% Off for VIP Members",
        "Stock Up & Save: {pct}% Off Essentials",
    ],
    "transactional": [
        "Your Order #{order} Has Shipped! 📦",
        "Order Confirmation — #{order}",
        "Your Return Has Been Processed",
        "Payment Received — Thank You!",
        "Your Refund Has Been Issued",
        "Delivery Update: Arriving {day}",
        "Receipt for Your Recent Purchase",
    ],
    "welcome": [
        "Welcome to the Family! Here's {pct}% Off 🎉",
        "Your Account is Ready — Let's Get Started",
        "Welcome! Enjoy Free Shipping on Your First Order",
        "Thanks for Joining — Here's a Gift",
        "Welcome Aboard! Explore What's New",
    ],
    "abandoned_cart": [
        "Forgot Something? Your Cart is Waiting 🛒",
        "Still Thinking It Over? Complete Your Order",
        "Don't Let These Items Get Away!",
        "Your Cart Misses You — Come Back & Save {pct}%",
        "Items in Your Cart Are Selling Fast!",
        "Complete Your Purchase & Get Free Shipping",
    ],
    "re_engagement": [
        "We Miss You! Come Back for {pct}% Off",
        "It's Been a While — Here's Something Special",
        "Long Time No See! {pct}% Off to Welcome You Back",
        "Your Favorites Are Waiting — Plus a Surprise",
        "We Saved Your Favorites — Check Them Out",
    ],
    "newsletter": [
        "This Week: New Arrivals + Editor's Picks",
        "What's Trending This Month",
        "Style Guide: {season} {year} Edition",
        "Top 10 Products Our Customers Love",
        "Inside Look: Behind the Brand",
        "Your Weekly Digest: News, Tips & Deals",
        "Monthly Roundup: Best of {month}",
    ],
}

SEASONS = ["Spring", "Summer", "Fall", "Winter"]
MONTHS = ["January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December"]

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

LINK_URLS = [
    "/shop/new-arrivals", "/sale", "/bestsellers", "/shop",
    "/products/{sku}", "/category/{cat}", "/deals",
    "/rewards", "/gift-cards", "/blog/latest",
]

DEVICE_TYPES = ["desktop", "mobile", "tablet"]
DEVICE_WEIGHTS_EMAIL = [0.25, 0.60, 0.15]  # Most email opens are mobile


class EmailGenerator(BaseGenerator):
    """Generate email campaigns and engagement events."""

    def generate(
        self,
        *,
        customers: pl.DataFrame,
        **deps,
    ) -> dict[str, pl.DataFrame]:
        personas: dict[str, CustomerPersona] = customers.__dict__.get("_personas", {})
        customer_records = customers.to_dicts()
        target_events = self.config.tier.emails_sent

        # Generate campaigns
        campaigns = self._generate_campaigns()

        # Generate events
        events = self._generate_events(
            campaigns, customer_records, personas, target_events
        )

        campaigns_df = pl.DataFrame(campaigns).cast({
            "send_date": pl.Date,
        })

        schema_overrides = {
            "email_event_id": pl.String,
            "customer_id": pl.String,
            "campaign_id": pl.String,
            "event_type": pl.String,
            "email_address": pl.String,
            "link_clicked": pl.String,
            "device_type": pl.String,
        }
        events_df = pl.DataFrame(events, schema_overrides=schema_overrides).cast({
            "event_timestamp": pl.Datetime,
        }) if events else pl.DataFrame(schema={
            "email_event_id": pl.Utf8, "customer_id": pl.Utf8,
            "campaign_id": pl.Utf8, "event_type": pl.Utf8,
            "event_timestamp": pl.Datetime, "email_address": pl.Utf8,
            "link_clicked": pl.Utf8, "device_type": pl.Utf8,
        })

        return {
            "email_campaigns": campaigns_df,
            "email_events": events_df,
        }

    def _generate_campaigns(self) -> list[dict]:
        """Generate email campaigns across the date range."""
        campaigns = []
        start = self.config.date_range.start
        end = self.config.date_range.end
        cpm = self.config.email.campaigns_per_month
        campaign_types = self.config.email.types

        current = start
        camp_id = 1
        while current <= end:
            for _ in range(cpm):
                ctype = self.rng.choice(campaign_types)

                # Pick a send date within the month
                month_end = min(
                    current.replace(day=28) + timedelta(days=4),
                    end,
                )
                month_end = month_end.replace(day=min(month_end.day, 28))
                send_date = random_date_in_range(self.rng, current, month_end)

                subject = self._generate_subject(ctype, send_date)

                # Target segment based on campaign type
                segment_map = {
                    "promotional": self.rng.choice(["all", "returning", "vip"]),
                    "transactional": "all",
                    "welcome": "new",
                    "abandoned_cart": "cart_abandoners",
                    "re_engagement": "churned",
                    "newsletter": self.rng.choice(["all", "returning"]),
                }

                campaigns.append({
                    "campaign_id": f"CAMP-{camp_id:04d}",
                    "campaign_name": subject[:50].rstrip("!.").strip(),
                    "campaign_type": ctype,
                    "subject_line": subject,
                    "send_date": send_date,
                    "target_segment": segment_map.get(ctype, "all"),
                })
                camp_id += 1

            # Move to next month
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1, day=1)
            else:
                current = current.replace(month=current.month + 1, day=1)

        return campaigns

    def _generate_subject(self, ctype: str, send_date) -> str:
        """Generate a campaign subject line."""
        templates = SUBJECT_TEMPLATES.get(ctype, SUBJECT_TEMPLATES["promotional"])
        template = self.rng.choice(templates)

        pct = self.rng.choice([10, 15, 20, 25, 30, 40, 50])
        order = f"ORD{self.rng.randint(100000, 999999)}"
        season = SEASONS[(send_date.month - 1) // 3]
        month = MONTHS[send_date.month - 1]
        year = send_date.year
        day = self.rng.choice(DAYS)

        return template.format(
            pct=pct, order=order, season=season,
            month=month, year=year, day=day,
        )

    def _generate_events(
        self,
        campaigns: list[dict],
        customers: list[dict],
        personas: dict[str, CustomerPersona],
        target_events: int,
    ) -> list[dict]:
        """Generate email engagement events."""
        events: list[dict] = []
        event_count = 0

        delivery_rate = self.config.email.delivery_rate

        for campaign in campaigns:
            if event_count >= target_events:
                break

            campaign_id = campaign["campaign_id"]
            send_date = campaign["send_date"]
            ctype = campaign["campaign_type"]
            segment = campaign["target_segment"]

            # Determine recipients based on segment
            recipients = self._select_recipients(
                customers, personas, segment, ctype
            )

            # Limit recipients to stay within target
            events_per_recipient = 1.5  # average events per recipient (sent + some opens/clicks)
            max_recipients = int((target_events - event_count) / events_per_recipient)
            if len(recipients) > max_recipients:
                recipients = self.rng.sample(recipients, max_recipients)

            for cust in recipients:
                if event_count >= target_events:
                    break

                cid = cust["customer_id"]
                persona = personas.get(cid)
                email = cust["email"]

                send_ts = random_timestamp(self.rng, send_date, "online")
                device = self._pick_weighted(DEVICE_TYPES, DEVICE_WEIGHTS_EMAIL)

                # 1) SENT — always
                events.append({
                    "email_event_id": self._uuid(),
                    "customer_id": cid,
                    "campaign_id": campaign_id,
                    "event_type": "sent",
                    "event_timestamp": send_ts,
                    "email_address": email,
                    "link_clicked": None,
                    "device_type": device,
                })
                event_count += 1

                # 2) DELIVERED vs BOUNCED
                if self.rng.random() < delivery_rate:
                    deliver_ts = send_ts + timedelta(seconds=self.rng.randint(1, 300))
                    events.append({
                        "email_event_id": self._uuid(),
                        "customer_id": cid,
                        "campaign_id": campaign_id,
                        "event_type": "delivered",
                        "event_timestamp": deliver_ts,
                        "email_address": email,
                        "link_clicked": None,
                        "device_type": device,
                    })
                    event_count += 1

                    # 3) OPENED — persona-driven rate
                    open_rate = persona.email_open_rate if persona else 0.20
                    # Promotional campaigns get higher open rates
                    if ctype == "abandoned_cart":
                        open_rate *= 1.3
                    elif ctype == "welcome":
                        open_rate *= 1.5

                    if self.rng.random() < open_rate:
                        # Open happens 0.5-48 hours after delivery
                        open_ts = deliver_ts + timedelta(
                            hours=self.rng.uniform(0.5, 48)
                        )
                        events.append({
                            "email_event_id": self._uuid(),
                            "customer_id": cid,
                            "campaign_id": campaign_id,
                            "event_type": "opened",
                            "event_timestamp": open_ts,
                            "email_address": email,
                            "link_clicked": None,
                            "device_type": device,
                        })
                        event_count += 1

                        # 4) CLICKED — persona-driven rate
                        click_rate = persona.email_click_rate if persona else 0.04
                        if self.rng.random() < click_rate:
                            click_ts = open_ts + timedelta(
                                seconds=self.rng.randint(5, 600)
                            )
                            link = self.rng.choice(LINK_URLS)
                            if "{sku}" in link:
                                link = link.replace("{sku}", f"SKU-{self.rng.randint(1, 2000):05d}")
                            if "{cat}" in link:
                                link = link.replace("{cat}", self.rng.choice(list(self.config.categories.keys())).lower().replace(" ", "-"))

                            events.append({
                                "email_event_id": self._uuid(),
                                "customer_id": cid,
                                "campaign_id": campaign_id,
                                "event_type": "clicked",
                                "event_timestamp": click_ts,
                                "email_address": email,
                                "link_clicked": link,
                                "device_type": device,
                            })
                            event_count += 1

                        # 5) UNSUBSCRIBED — rare
                        unsub_rate = 0.005
                        if persona and persona.persona_name == "one_and_done":
                            unsub_rate = 0.03
                        if self.rng.random() < unsub_rate:
                            unsub_ts = open_ts + timedelta(
                                seconds=self.rng.randint(10, 300)
                            )
                            events.append({
                                "email_event_id": self._uuid(),
                                "customer_id": cid,
                                "campaign_id": campaign_id,
                                "event_type": "unsubscribed",
                                "event_timestamp": unsub_ts,
                                "email_address": email,
                                "link_clicked": None,
                                "device_type": device,
                            })
                            event_count += 1

                        # 6) SPAM REPORTED — very rare
                        if self.rng.random() < 0.001:
                            spam_ts = open_ts + timedelta(
                                seconds=self.rng.randint(1, 60)
                            )
                            events.append({
                                "email_event_id": self._uuid(),
                                "customer_id": cid,
                                "campaign_id": campaign_id,
                                "event_type": "spam_reported",
                                "event_timestamp": spam_ts,
                                "email_address": email,
                                "link_clicked": None,
                                "device_type": device,
                            })
                            event_count += 1
                else:
                    # BOUNCED
                    bounce_ts = send_ts + timedelta(seconds=self.rng.randint(1, 60))
                    events.append({
                        "email_event_id": self._uuid(),
                        "customer_id": cid,
                        "campaign_id": campaign_id,
                        "event_type": "bounced",
                        "event_timestamp": bounce_ts,
                        "email_address": email,
                        "link_clicked": None,
                        "device_type": device,
                    })
                    event_count += 1

        return events

    def _select_recipients(
        self,
        customers: list[dict],
        personas: dict[str, CustomerPersona],
        segment: str,
        ctype: str,
    ) -> list[dict]:
        """Select recipients based on campaign segment."""
        if segment == "all":
            return customers

        filtered = []
        for cust in customers:
            persona = personas.get(cust["customer_id"])
            if persona is None:
                continue

            if segment == "new" and persona.customer_segment == "new":
                filtered.append(cust)
            elif segment == "returning" and persona.customer_segment in ("returning", "vip"):
                filtered.append(cust)
            elif segment == "vip" and persona.customer_segment == "vip":
                filtered.append(cust)
            elif segment == "churned" and persona.customer_segment == "churned":
                filtered.append(cust)
            elif segment == "cart_abandoners":
                # ~30% of active shoppers get abandoned cart emails
                if persona.orders_per_year > 0 and self.rng.random() < 0.30:
                    filtered.append(cust)

        return filtered if filtered else customers[:10]  # fallback
