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
            store_ids=None,
            store_states=None,
        )

        # ---- Generate In-Store Accounts ----
        instore_accounts = self._generate_instore_accounts(
            customer_ids, personas, store_ids
        )

        # ---- Generate In-Store POS ----
        target_instore = self.config.tier.instore_transactions
        instore_account_ids = {
            r["customer_id"]: r["instore_account_id"]
            for r in instore_accounts.to_dicts()
            if r["customer_id"] is not None
        }

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
            instore_account_ids=instore_account_ids,
        )

        # Forward personas to downstream generators
        online_orders.__dict__["_personas"] = personas

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
        instore_account_ids: dict[str, str] | None = None,
    ) -> tuple[pl.DataFrame, pl.DataFrame]:
        """Generate orders + line items for a channel."""

        orders: list[dict] = []
        items: list[dict] = []
        order_count = 0

        # Distribute orders across customers weighted by persona
        cust_order_counts: list[tuple[str, int]] = []
        total_weight = 0
        for cid in customer_ids:
            persona = personas.get(cid)
            if persona is None:
                continue
            # Instore: only omnichannel customers shop in-store
            if channel == "instore" and not persona.is_omnichannel:
                continue
            w = persona.orders_per_year
            if channel == "instore":
                w = max(0, int(w * 0.4))  # fewer in-store than online
            cust_order_counts.append((cid, w))
            total_weight += w

        if total_weight == 0:
            # Return empty DataFrames
            return self._empty_order_df(channel), self._empty_items_df(channel)

        # Scale weights to hit target count (over ~2 years)
        scale_factor = target_count / (total_weight * 2) if total_weight > 0 else 1

        for cid, base_weight in cust_order_counts:
            if order_count >= target_count:
                break

            persona = personas[cid]
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

                # Tax
                if channel == "online":
                    addrs = addr_by_customer.get(cid, [])
                    ship_addr = next((a for a in addrs if a["address_type"] == "shipping" and a["is_default"]), None)
                    if ship_addr:
                        state = ship_addr["state"]
                    else:
                        state = "CA"
                    tax_rate = self.config.tax_rates.get(state, self.config.tax_rates["default"])
                else:
                    store_id = self.rng.choice(store_ids) if store_ids else "STORE-001"
                    state = store_states.get(store_id, "CA") if store_states else "CA"
                    tax_rate = self.config.tax_rates.get(state, self.config.tax_rates["default"])

                taxable = max(0, subtotal - order_discount)
                tax = round(taxable * tax_rate, 2)

                # Shipping (online only)
                shipping = 0.0
                if channel == "online":
                    if subtotal >= self.config.shipping.free_threshold:
                        shipping = 0.0
                    else:
                        ship_type = self._pick_weighted(
                            ["standard", "express", "overnight"],
                            [self.config.shipping.standard_pct, self.config.shipping.express_pct, self.config.shipping.overnight_pct],
                        )
                        rate_range = getattr(self.config.shipping.rates, ship_type)
                        shipping = round(self.rng.uniform(*rate_range), 2)

                total = round(subtotal - order_discount + tax + shipping, 2)

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

                    orders.append({
                        "order_id": order_id,
                        "customer_id": cid,
                        "order_date": ts,
                        "status": status,
                        "shipping_address_id": ship_id,
                        "billing_address_id": bill_id,
                        "subtotal": subtotal,
                        "discount_amount": order_discount,
                        "tax_amount": tax,
                        "shipping_cost": shipping,
                        "total_amount": total,
                        "payment_method": payment,
                        "coupon_code": coupon,
                        "device_type": device,
                        "session_id": self._uuid(),
                    })
                else:
                    payment = self._pick_weighted(PAYMENT_METHODS_INSTORE, PAYMENT_WEIGHTS_INSTORE)
                    instore_acct = instore_account_ids.get(cid) if instore_account_ids else None

                    # ~20% of in-store transactions are walk-in (no account)
                    if instore_acct is None or self.rng.random() < 0.20:
                        instore_acct = None
                        cid_for_record = None
                    else:
                        cid_for_record = cid

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
                        "payment_method": payment,
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

    def _generate_instore_accounts(
        self,
        customer_ids: list[str],
        personas: dict[str, CustomerPersona],
        store_ids: list[str],
    ) -> pl.DataFrame:
        """Generate in-store POS accounts for omnichannel customers."""
        records: list[dict] = []

        for cid in customer_ids:
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

            records.append({
                "instore_account_id": self._uuid(),
                "customer_id": cid,
                "store_id": self.rng.choice(store_ids),
                "phone_number": self.faker.phone_number(),
                "created_at": created,
                "last_visit_date": last_visit,
                "total_visits": total_visits,
            })

        # Add some unlinked POS accounts (walk-in regulars without online accounts)
        n_unlinked = max(1, int(len(records) * 0.15))
        for _ in range(n_unlinked):
            records.append({
                "instore_account_id": self._uuid(),
                "customer_id": None,
                "store_id": self.rng.choice(store_ids),
                "phone_number": self.faker.phone_number(),
                "created_at": random_timestamp(
                    self.rng,
                    random_date_in_range(self.rng, self.config.date_range.start, self.config.date_range.end),
                    "instore",
                ),
                "last_visit_date": random_date_in_range(
                    self.rng, self.config.date_range.start, self.config.date_range.end
                ),
                "total_visits": self.rng.randint(1, 20),
            })

        return pl.DataFrame(records).cast({
            "created_at": pl.Datetime,
            "last_visit_date": pl.Date,
            "total_visits": pl.Int64,
        })

    def _empty_order_df(self, channel: str) -> pl.DataFrame:
        if channel == "online":
            return pl.DataFrame(schema={
                "order_id": pl.Utf8, "customer_id": pl.Utf8,
                "order_date": pl.Datetime, "status": pl.Utf8,
                "shipping_address_id": pl.Utf8, "billing_address_id": pl.Utf8,
                "subtotal": pl.Float64, "discount_amount": pl.Float64,
                "tax_amount": pl.Float64, "shipping_cost": pl.Float64,
                "total_amount": pl.Float64, "payment_method": pl.Utf8,
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
                "total_amount": pl.Float64, "payment_method": pl.Utf8,
                "coupon_code": pl.Utf8,
            })

    def _empty_items_df(self, channel: str) -> pl.DataFrame:
        pk = "order_item_id" if channel == "online" else "line_item_id"
        fk = "order_id" if channel == "online" else "transaction_id"
        return pl.DataFrame(schema={
            pk: pl.Utf8, fk: pl.Utf8, "product_id": pl.Utf8,
            "quantity": pl.Int64, "unit_price": pl.Float64,
            "discount_pct": pl.Float64, "line_total": pl.Float64,
        })
