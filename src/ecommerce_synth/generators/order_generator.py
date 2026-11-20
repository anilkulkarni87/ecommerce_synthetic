"""Order generator for online and in-store channels.

Generates:
- orders_online + order_items_online
- orders_instore + order_items_instore
- instore_accounts

All with proper persona-driven frequency, seasonal patterns, realistic
pricing, tax, shipping, and coupon logic.
"""

from __future__ import annotations

from datetime import date, timedelta

import polars as pl

from ..persona import CustomerPersona
from ..utils.temporal import (
    random_date_in_range,
    random_timestamp,
    seasonal_multiplier,
)
from .base import BaseGenerator


# Coupon codes with realistic formats
COUPON_CODES = [
    "SAVE10", "SAVE15", "SAVE20", "WELCOME10", "SPRING25",
    "SUMMER20", "FALL15", "WINTER30", "FLASH50", "VIP20",
    "LOYALTY15", "BOGO50", "FREESHIP", "NEWYEAR25", "HOLIDAY30",
    "BIRTHDAY20", "CLEARANCE40", "MEMBER10", "REFER15", "BACK2SCHOOL",
    None, None, None, None, None,  # most orders don't have coupons
]

PAYMENT_METHODS_ONLINE = ["credit_card", "debit_card", "paypal", "apple_pay", "gift_card"]
PAYMENT_WEIGHTS_ONLINE = [0.40, 0.20, 0.20, 0.15, 0.05]

PAYMENT_METHODS_INSTORE = ["credit_card", "debit_card", "cash", "mobile_pay", "gift_card"]
PAYMENT_WEIGHTS_INSTORE = [0.35, 0.25, 0.20, 0.15, 0.05]

DEVICE_TYPES = ["desktop", "mobile", "tablet"]
DEVICE_WEIGHTS = [0.35, 0.50, 0.15]

ORDER_STATUSES = ["pending", "confirmed", "shipped", "delivered", "cancelled", "returned"]
# Most orders are delivered
ORDER_STATUS_WEIGHTS = [0.02, 0.03, 0.05, 0.80, 0.05, 0.05]


class OrderGenerator(BaseGenerator):
    """Generate online orders, in-store POS transactions, and in-store accounts."""

    def generate(
        self,
        *,
        customers: pl.DataFrame,
        addresses: pl.DataFrame,
        products: pl.DataFrame,
        stores: pl.DataFrame,
        **deps,
    ) -> dict[str, pl.DataFrame]:
        personas: dict[str, CustomerPersona] = customers.__dict__.get("_personas", {})

        # Build lookup structures
        customer_ids = customers["customer_id"].to_list()
        product_records = products.to_dicts()
        active_products = [p for p in product_records if p["is_active"]]
        store_ids = stores["store_id"].to_list()
        store_states = dict(zip(stores["store_id"].to_list(), stores["state"].to_list()))
        store_countries = (
            dict(zip(stores["store_id"].to_list(), stores["country"].to_list()))
            if "country" in stores.columns
            else {}
        )
        cust_emails = (
            dict(zip(customers["customer_id"].to_list(), customers["email"].to_list()))
            if "email" in customers.columns
            else {}
        )

        # Group addresses by customer
        addr_by_customer: dict[str, list[dict]] = {}
        for row in addresses.to_dicts():
            cid = row["customer_id"]
            if cid not in addr_by_customer:
                addr_by_customer[cid] = []
            addr_by_customer[cid].append(row)

        # Products by category for persona-based selection
        products_by_category: dict[str, list[dict]] = {}
        for p in active_products:
            cat = p["category"]
            if cat not in products_by_category:
                products_by_category[cat] = []
            products_by_category[cat].append(p)

        all_categories = list(products_by_category.keys())

        # ---- Generate Online Orders ----
        target_online = self.config.tier.online_orders
        online_orders, online_items = self._generate_orders(
            customer_ids=customer_ids,
            personas=personas,
            products=active_products,
            products_by_category=products_by_category,
            all_categories=all_categories,
            addr_by_customer=addr_by_customer,
            target_count=target_online,
            channel="online",
            store_ids=store_ids,
            store_states=store_states,
            store_countries=store_countries,
            cust_emails=cust_emails,
        )

        # ---- Generate In-Store Accounts (decoupled POS registry: phone, email, or both) ----
        instore_accounts, instore_to_customer, pos_only_shoppers = self._generate_instore_accounts(
            customers, personas, store_ids
        )

        # ---- Generate In-Store POS ----
        target_instore = self.config.tier.instore_transactions
        cust_to_instore_acct = {cid: acct_id for acct_id, cid in instore_to_customer.items()}

        instore_orders, instore_items = self._generate_orders(
            customer_ids=customer_ids,
            personas=personas,
            products=active_products,
            products_by_category=products_by_category,
            all_categories=all_categories,
            addr_by_customer=addr_by_customer,
            target_count=target_instore,
            channel="instore",
            store_ids=store_ids,
            store_states=store_states,
            store_countries=store_countries,
            cust_emails=cust_emails,
            instore_account_ids=cust_to_instore_acct,
            pos_only_shoppers=pos_only_shoppers,
        )

        # Forward personas and internal POS->customer mapping for downstream generators
        online_orders.__dict__["_personas"] = personas
        instore_orders.__dict__["_instore_to_customer"] = instore_to_customer
        instore_accounts.__dict__["_instore_to_customer"] = instore_to_customer

        return {
            "orders_online": online_orders,
            "order_items_online": online_items,
            "instore_accounts": instore_accounts,
            "orders_instore": instore_orders,
            "order_items_instore": instore_items,
        }

    def _generate_orders(
        self,
        customer_ids: list[str],
        personas: dict[str, CustomerPersona],
        products: list[dict],
        products_by_category: dict[str, list[dict]],
        all_categories: list[str],
        addr_by_customer: dict[str, list[dict]],
        target_count: int,
        channel: str,
        store_ids: list[str] | None,
        store_states: dict[str, str] | None,
        store_countries: dict[str, str] | None = None,
        cust_emails: dict[str, str] | None = None,
        instore_account_ids: dict[str, str] | None = None,
        pos_only_shoppers: dict[str, dict] | None = None,
    ) -> tuple[pl.DataFrame, pl.DataFrame]:
        """Generate orders + line items for a channel."""

        orders: list[dict] = []
        items: list[dict] = []
        order_count = 0
        shopper_tokens: dict[str, str] = {}
        walkin_token_pool = [f"tok_wi_{i:06x}" for i in range(50)]

        # Distribute orders across shoppers weighted by persona
        # Entry tuple: (shopper_key, weight, persona, is_pos_only, home_store_id)
        shopper_weights: list[tuple[str, int, CustomerPersona, bool, str | None]] = []
        total_weight = 0
        for cid in customer_ids:
            persona = personas.get(cid)
            if persona is None:
                continue
            # Instore: only omnichannel digital customers shop in-store
            if channel == "instore" and not persona.is_omnichannel:
                continue
            w = persona.orders_per_year
            if channel == "instore":
                w = max(1, int(w * 0.4))  # fewer in-store than online
            shopper_weights.append((cid, w, persona, False, None))
            total_weight += w

        if channel == "instore" and pos_only_shoppers:
            for acct_id, info in pos_only_shoppers.items():
                p = info["persona"]
                w = max(1, int(p.orders_per_year * 0.5))
                shopper_weights.append((acct_id, w, p, True, info.get("store_id")))
                total_weight += w

        if total_weight == 0:
            # Return empty DataFrames
            return self._empty_order_df(channel), self._empty_items_df(channel)

        # Scale weights to hit target count (over ~2 years)
        scale_factor = target_count / (total_weight * 2) if total_weight > 0 else 1

        for shopper_key, base_weight, persona, is_pos_only, home_store_id in shopper_weights:
            if order_count >= target_count:
                break

            cid = None if is_pos_only else shopper_key
            n_orders = max(0, int(round(base_weight * 2 * scale_factor)))

            # Add jitter
            n_orders = max(0, n_orders + self.rng.randint(-1, 1))

            for _ in range(n_orders):
                if order_count >= target_count:
                    break

                order_date = random_date_in_range(
                    self.rng,
                    self.config.date_range.start,
                    self.config.date_range.end,
                    self.config,
                )
                ts = random_timestamp(self.rng, order_date, channel)

                # Pick products based on persona preferences
                n_items = max(1, persona.avg_cart_items + self.rng.randint(-1, 1))
                selected_products = self._pick_products(
                    persona, products, products_by_category, all_categories, n_items
                )

                # Generate line items
                subtotal = 0.0
                order_id = self._uuid()

                for prod in selected_products:
                    qty = self.rng.choices([1, 2, 3, 4, 5], weights=[60, 20, 10, 5, 5], k=1)[0]

                    # Discount: bargain hunters always get a discount
                    discount_pct = 0.0
                    if persona.always_uses_coupon:
                        discount_pct = self.rng.choice([0.10, 0.15, 0.20, 0.25, 0.30])
                    elif self.rng.random() < 0.15:
                        discount_pct = self.rng.choice([0.05, 0.10, 0.15, 0.20])

                    unit_price = prod["price"]
                    line_total = round(qty * unit_price * (1 - discount_pct), 2)
                    subtotal += line_total

                    item_record = {
                        "order_item_id" if channel == "online" else "line_item_id": self._uuid(),
                        "order_id" if channel == "online" else "transaction_id": order_id,
                        "product_id": prod["product_id"],
                        "quantity": qty,
                        "unit_price": unit_price,
                        "discount_pct": round(discount_pct, 2),
                        "line_total": line_total,
                    }
                    items.append(item_record)

                subtotal = round(subtotal, 2)

                # Coupon
                coupon = None
                if persona.always_uses_coupon:
                    coupon = self.rng.choice([c for c in COUPON_CODES if c is not None])
                elif self.rng.random() < 0.12:
                    coupon = self.rng.choice([c for c in COUPON_CODES if c is not None])

                # Discount on top of line-level discounts (order-level)
                order_discount = 0.0
                if coupon and self.rng.random() < 0.5:
                    order_discount = round(subtotal * self.rng.uniform(0.05, 0.15), 2)

                # Tax & Region Currency
                region_configs = getattr(self.config, "region_configs", {}) or {}
                if channel == "online":
                    addrs = addr_by_customer.get(cid, [])
                    ship_addr = next((a for a in addrs if a["address_type"] == "shipping" and a["is_default"]), None)
                    if ship_addr:
                        state = ship_addr["state"]
                        country = ship_addr.get("country", "US")
                    else:
                        state = "CA"
                        country = "US"
                else:
                    if home_store_id and self.rng.random() < 0.70:
                        store_id = home_store_id
                    else:
                        store_id = self.rng.choice(store_ids) if store_ids else "STORE-001"
                    state = store_states.get(store_id, "CA") if store_states else "CA"
                    country = store_countries.get(store_id, "US") if store_countries else "US"

                rc = region_configs.get(country)
                currency_code = rc.currency if rc else "USD"
                fx_rate = rc.fx_rate_to_usd if rc else 1.0
                tax_regime = rc.tax_regime if rc else "SALES_TAX"

                taxable = max(0, subtotal - order_discount)
                if country == "US" or not rc:
                    tax_rate = self.config.tax_rates.get(state, self.config.tax_rates["default"])
                    tax = round(taxable * tax_rate, 2)
                elif tax_regime == "VAT":
                    # Tax-inclusive: VAT is already embedded in shelf price
                    tax = round(taxable * (rc.default_tax_rate / (1.0 + rc.default_tax_rate)), 2)
                else:
                    # GST / Sales Tax exclusive
                    tax = round(taxable * rc.default_tax_rate, 2)

                # Fulfillment & Shipping (online only; BOPIS has free pickup)
                fulfillment_type = "ship_to_home"
                pickup_store_id = None
                shipping = 0.0
                if channel == "online":
                    if store_ids and self.rng.random() < 0.18:
                        fulfillment_type = "bopis"
                        pickup_store_id = self.rng.choice(store_ids)
                        shipping = 0.0
                    elif subtotal >= self.config.shipping.free_threshold:
                        shipping = 0.0
                    else:
                        ship_type = self._pick_weighted(
                            ["standard", "express", "overnight"],
                            [self.config.shipping.standard_pct, self.config.shipping.express_pct, self.config.shipping.overnight_pct],
                        )
                        rate_range = getattr(self.config.shipping.rates, ship_type)
                        shipping = round(self.rng.uniform(*rate_range), 2)

                if tax_regime == "VAT" and country != "US":
                    total = round(taxable + shipping, 2)
                else:
                    total = round(taxable + tax + shipping, 2)
                total_usd = round(total * fx_rate, 2)

                # Status — persona-driven
                if persona.is_fraudster and persona.fraud_type in ("card_testing",):
                    status = self.rng.choice(["cancelled", "pending", "confirmed"])
                elif persona.return_rate > 0 and self.rng.random() < persona.return_rate:
                    status = "returned"
                elif self.rng.random() < 0.05:
                    status = "cancelled"
                else:
                    status = self._pick_weighted(
                        ["pending", "confirmed", "shipped", "delivered"],
                        [0.02, 0.03, 0.05, 0.90],
                    )

                if channel == "online":
                    addrs = addr_by_customer.get(cid, [])
                    ship_id = next(
                        (a["address_id"] for a in addrs if a["address_type"] == "shipping"),
                        None,
                    )
                    bill_id = next(
                        (a["address_id"] for a in addrs if a["address_type"] == "billing"),
                        None,
                    )

                    device = self._pick_weighted(DEVICE_TYPES, DEVICE_WEIGHTS)
                    payment = self._pick_weighted(PAYMENT_METHODS_ONLINE, PAYMENT_WEIGHTS_ONLINE)
                    pay_token = None
                    if payment in ("credit_card", "debit_card", "apple_pay"):
                        pay_token = shopper_tokens.setdefault(shopper_key, f"tok_{self._uuid()[:12]}")

                    # ~15% of non-fraudster online orders are guest checkouts (customer_id = NULL)
                    is_guest = (not persona.is_fraudster) and (self.rng.random() < 0.15)
                    cid_for_online = None if is_guest else cid
                    guest_email = (
                        (cust_emails.get(cid) if cust_emails else None) or self.faker.email()
                        if is_guest
                        else None
                    )

                    orders.append({
                        "order_id": order_id,
                        "customer_id": cid_for_online,
                        "guest_email": guest_email,
                        "fulfillment_type": fulfillment_type,
                        "pickup_store_id": pickup_store_id,
                        "order_date": ts,
                        "status": status,
                        "shipping_address_id": ship_id,
                        "billing_address_id": bill_id,
                        "subtotal": subtotal,
                        "discount_amount": order_discount,
                        "tax_amount": tax,
                        "shipping_cost": shipping,
                        "total_amount": total,
                        "currency_code": currency_code,
                        "fx_rate_to_usd": fx_rate,
                        "total_amount_usd": total_usd,
                        "tax_regime": tax_regime,
                        "payment_method": payment,
                        "payment_token": pay_token,
                        "coupon_code": coupon,
                        "device_type": device,
                        "session_id": self._uuid(),
                    })
                else:
                    payment = self._pick_weighted(PAYMENT_METHODS_INSTORE, PAYMENT_WEIGHTS_INSTORE)
                    if is_pos_only:
                        instore_acct = shopper_key
                    else:
                        instore_acct = instore_account_ids.get(cid) if (instore_account_ids and cid) else None

                    # ~20% of in-store transactions are anonymous walk-ins (no POS account)
                    if instore_acct is None or self.rng.random() < 0.20:
                        instore_acct = None

                    pay_token = None
                    if payment in ("credit_card", "debit_card", "mobile_pay"):
                        if instore_acct is not None:
                            pay_token = shopper_tokens.setdefault(shopper_key, f"tok_{self._uuid()[:12]}")
                        elif self.rng.random() < 0.30:
                            pay_token = self.rng.choice(walkin_token_pool)

                    # Real-world POS registers do not know the e-commerce customer_id UUID
                    cid_for_record = None

                    orders.append({
                        "transaction_id": order_id,
                        "store_id": store_id if store_ids else "STORE-001",
                        "instore_account_id": instore_acct,
                        "customer_id": cid_for_record,
                        "transaction_date": ts,
                        "register_id": f"REG-{self.rng.randint(1, 12):02d}",
                        "employee_id": f"EMP-{self.rng.randint(1, 200):04d}",
                        "subtotal": subtotal,
                        "tax_amount": tax,
                        "discount_amount": order_discount,
                        "total_amount": total,
                        "currency_code": currency_code,
                        "fx_rate_to_usd": fx_rate,
                        "total_amount_usd": total_usd,
                        "tax_regime": tax_regime,
                        "payment_method": payment,
                        "payment_token": pay_token,
                        "coupon_code": coupon,
                    })

                order_count += 1

        if channel == "online":
            orders_df = pl.DataFrame(orders).cast({
                "order_date": pl.Datetime,
                "subtotal": pl.Float64,
                "discount_amount": pl.Float64,
                "tax_amount": pl.Float64,
                "shipping_cost": pl.Float64,
                "total_amount": pl.Float64,
                "fx_rate_to_usd": pl.Float64,
                "total_amount_usd": pl.Float64,
            }) if orders else self._empty_order_df(channel)

            items_df = pl.DataFrame(items).cast({
                "quantity": pl.Int64,
                "unit_price": pl.Float64,
                "discount_pct": pl.Float64,
                "line_total": pl.Float64,
            }) if items else self._empty_items_df(channel)
        else:
            orders_df = pl.DataFrame(orders).cast({
                "transaction_date": pl.Datetime,
                "subtotal": pl.Float64,
                "tax_amount": pl.Float64,
                "discount_amount": pl.Float64,
                "total_amount": pl.Float64,
                "fx_rate_to_usd": pl.Float64,
                "total_amount_usd": pl.Float64,
            }) if orders else self._empty_order_df(channel)

            items_df = pl.DataFrame(items).cast({
                "quantity": pl.Int64,
                "unit_price": pl.Float64,
                "discount_pct": pl.Float64,
                "line_total": pl.Float64,
            }) if items else self._empty_items_df(channel)

        return orders_df, items_df

    def _pick_products(
        self,
        persona: CustomerPersona,
        all_products: list[dict],
        products_by_category: dict[str, list[dict]],
        all_categories: list[str],
        n: int,
    ) -> list[dict]:
        """Pick products based on persona's category preferences."""
        selected = []
        for _ in range(n):
            if persona.preferred_categories and self.rng.random() < 0.75:
                cat = self.rng.choice(persona.preferred_categories)
                pool = products_by_category.get(cat, all_products)
            else:
                pool = all_products
            selected.append(self.rng.choice(pool))
        return selected

    def _format_pos_phone(self, phone: str) -> str:
        """Apply realistic POS register phone formatting variations (~20% of the time)."""
        if self.rng.random() >= 0.20:
            return phone
        digits = "".join(ch for ch in phone if ch.isdigit())
        if len(digits) < 10:
            return phone
        last10 = digits[-10:]
        variant = self.rng.choice(["digits", "parens", "dots", "dashes"])
        if variant == "digits":
            return last10
        if variant == "parens":
            return f"({last10[:3]}) {last10[3:6]}-{last10[6:]}"
        if variant == "dots":
            return f"{last10[:3]}.{last10[3:6]}.{last10[6:]}"
        return f"{last10[:3]}-{last10[3:6]}-{last10[6:]}"

    def _format_pos_email(self, email: str) -> str:
        """Apply realistic POS email casing/whitespace variations (~15% of the time)."""
        if self.rng.random() >= 0.15:
            return email
        if self.rng.random() < 0.5:
            return email.upper()
        return f" {email.capitalize()} "

    def _pick_pos_contact(
        self,
        phone: str | None,
        email: str | None,
    ) -> tuple[str | None, str | None]:
        """Choose whether a POS shopper provides phone only, email only, or both."""
        mode = self._pick_weighted(
            ["phone_only", "email_only", "both"],
            [0.45, 0.25, 0.30],
        )
        if mode == "phone_only" and phone:
            return self._format_pos_phone(phone), None
        if mode == "email_only" and email:
            return None, self._format_pos_email(email)
        return (
            self._format_pos_phone(phone) if phone else None,
            self._format_pos_email(email) if email else None,
        )

    def _generate_instore_accounts(
        self,
        customers: pl.DataFrame,
        personas: dict[str, CustomerPersona],
        store_ids: list[str],
    ) -> tuple[pl.DataFrame, dict[str, str], dict[str, dict]]:
        """Generate decoupled POS accounts (omnichannel + POS-only) with phone, email, or both."""
        records: list[dict] = []
        instore_to_customer: dict[str, str] = {}
        pos_only_shoppers: dict[str, dict] = {}

        cust_lookup = {
            row["customer_id"]: row
            for row in customers.select(["customer_id", "email", "phone"]).to_dicts()
        }

        for cid, cust_row in cust_lookup.items():
            persona = personas.get(cid)
            if persona is None or not persona.is_omnichannel:
                continue

            total_visits = self.rng.randint(1, 50) if persona.orders_per_year > 3 else self.rng.randint(1, 10)
            created = random_timestamp(
                self.rng,
                random_date_in_range(self.rng, self.config.date_range.start, self.config.date_range.end),
                "instore",
            )
            last_visit = random_date_in_range(
                self.rng,
                created.date(),
                self.config.date_range.end,
            )

            acct_id = self._uuid()
            raw_phone = cust_row.get("phone")
            raw_email = cust_row.get("email")
            # ~5% temporal PII drift at POS (e.g. updated phone/email while keeping the other)
            if raw_phone and raw_email and self.rng.random() < 0.05:
                if self.rng.random() < 0.5:
                    raw_email = f"pos.{raw_email.split('@')[0]}@gmail.com"
                else:
                    raw_phone = self.faker.phone_number()
                pos_phone = self._format_pos_phone(raw_phone)
                pos_email = self._format_pos_email(raw_email)
            else:
                pos_phone, pos_email = self._pick_pos_contact(raw_phone, raw_email)
            instore_to_customer[acct_id] = cid

            records.append({
                "instore_account_id": acct_id,
                "customer_id": None,
                "store_id": self.rng.choice(store_ids),
                "phone_number": pos_phone,
                "email": pos_email,
                "created_at": created,
                "last_visit_date": last_visit,
                "total_visits": total_visits,
            })

        # Add POS-only shoppers (~40% of total POS accounts) who never registered online
        n_pos_only = max(1, int(len(records) * 0.70))
        for _ in range(n_pos_only):
            acct_id = self._uuid()
            home_store = self.rng.choice(store_ids)
            pos_phone, pos_email = self._pick_pos_contact(
                self.faker.phone_number(),
                self.faker.email(),
            )
            created = random_timestamp(
                self.rng,
                random_date_in_range(self.rng, self.config.date_range.start, self.config.date_range.end),
                "instore",
            )
            last_visit = random_date_in_range(
                self.rng,
                created.date(),
                self.config.date_range.end,
            )
            total_visits = self.rng.randint(1, 20)

            records.append({
                "instore_account_id": acct_id,
                "customer_id": None,
                "store_id": home_store,
                "phone_number": pos_phone,
                "email": pos_email,
                "created_at": created,
                "last_visit_date": last_visit,
                "total_visits": total_visits,
            })
            pos_only_shoppers[acct_id] = {
                "store_id": home_store,
                "persona": CustomerPersona(
                    persona_name="occasional",
                    orders_per_year=max(2, total_visits // 2),
                    loyalty_tier=None,
                    email_open_rate=0.0,
                    email_click_rate=0.0,
                    browse_to_buy=0.0,
                    avg_cart_items=2,
                    preferred_categories=None,
                    return_rate=0.05,
                    review_rate=0.0,
                    always_uses_coupon=False,
                    is_omnichannel=False,
                ),
            }

        df = pl.DataFrame(records).cast({
            "instore_account_id": pl.Utf8,
            "customer_id": pl.Utf8,
            "store_id": pl.Utf8,
            "phone_number": pl.Utf8,
            "email": pl.Utf8,
            "created_at": pl.Datetime,
            "last_visit_date": pl.Date,
            "total_visits": pl.Int64,
        })
        return df, instore_to_customer, pos_only_shoppers

    def _empty_order_df(self, channel: str) -> pl.DataFrame:
        if channel == "online":
            return pl.DataFrame(schema={
                "order_id": pl.Utf8, "customer_id": pl.Utf8,
                "guest_email": pl.Utf8, "fulfillment_type": pl.Utf8,
                "pickup_store_id": pl.Utf8,
                "order_date": pl.Datetime, "status": pl.Utf8,
                "shipping_address_id": pl.Utf8, "billing_address_id": pl.Utf8,
                "subtotal": pl.Float64, "discount_amount": pl.Float64,
                "tax_amount": pl.Float64, "shipping_cost": pl.Float64,
                "total_amount": pl.Float64, "currency_code": pl.Utf8,
                "fx_rate_to_usd": pl.Float64, "total_amount_usd": pl.Float64,
                "tax_regime": pl.Utf8, "payment_method": pl.Utf8,
                "payment_token": pl.Utf8,
                "coupon_code": pl.Utf8, "device_type": pl.Utf8,
                "session_id": pl.Utf8,
            })
        else:
            return pl.DataFrame(schema={
                "transaction_id": pl.Utf8, "store_id": pl.Utf8,
                "instore_account_id": pl.Utf8, "customer_id": pl.Utf8,
                "transaction_date": pl.Datetime, "register_id": pl.Utf8,
                "employee_id": pl.Utf8, "subtotal": pl.Float64,
                "tax_amount": pl.Float64, "discount_amount": pl.Float64,
                "total_amount": pl.Float64, "currency_code": pl.Utf8,
                "fx_rate_to_usd": pl.Float64, "total_amount_usd": pl.Float64,
                "tax_regime": pl.Utf8, "payment_method": pl.Utf8,
                "payment_token": pl.Utf8, "coupon_code": pl.Utf8,
            })

    def _empty_items_df(self, channel: str) -> pl.DataFrame:
        pk = "order_item_id" if channel == "online" else "line_item_id"
        fk = "order_id" if channel == "online" else "transaction_id"
        return pl.DataFrame(schema={
            pk: pl.Utf8, fk: pl.Utf8, "product_id": pl.Utf8,
            "quantity": pl.Int64, "unit_price": pl.Float64,
            "discount_pct": pl.Float64, "line_total": pl.Float64,
        })
