"""Fulfillment, returns, and inventory snapshot generator.

Produces:
- shipments: carrier tracking & delivery SLA for non-cancelled online orders
- returns: item-level return reasons, refund amounts, and restock flags for returned orders
- inventory_snapshots: store x SKU stock levels, reorder points, and stockout flags
"""

from __future__ import annotations

from datetime import timedelta

import polars as pl

from .base import BaseGenerator

CARRIERS = ["UPS", "FedEx", "USPS", "DHL"]
CARRIER_WEIGHTS = [0.38, 0.32, 0.22, 0.08]

SHIPPING_TIERS = ["standard", "express", "overnight"]
TIER_DAYS = {"standard": (3, 7), "express": (2, 3), "overnight": (1, 1)}

RETURN_REASONS = [
    "wrong_size", "damaged_in_transit", "defective_product",
    "not_as_described", "changed_mind", "arrived_late",
]


class FulfillmentGenerator(BaseGenerator):
    """Generate shipments, returns, and inventory_snapshots tables."""

    def generate(
        self,
        *,
        orders_online: pl.DataFrame,
        order_items_online: pl.DataFrame,
        stores: pl.DataFrame,
        products: pl.DataFrame,
        **deps,
    ) -> dict[str, pl.DataFrame]:
        shipments: list[dict] = []
        returns: list[dict] = []

        # Index first item per order for item-level return attribution
        items_by_order: dict[str, list[dict]] = {}
        if order_items_online is not None and not order_items_online.is_empty():
            for it in order_items_online.select(["order_id", "order_item_id", "line_total"]).to_dicts():
                items_by_order.setdefault(it["order_id"], []).append(it)

        if orders_online is not None and not orders_online.is_empty():
            for ord_row in orders_online.select([
                "order_id", "customer_id", "order_date", "status", "shipping_cost"
            ]).to_dicts():
                status = ord_row["status"]
                if status == "cancelled":
                    continue

                oid = ord_row["order_id"]
                odate = ord_row["order_date"]
                carrier = self._pick_weighted(CARRIERS, CARRIER_WEIGHTS)
                tier = "overnight" if ord_row["shipping_cost"] >= 20 else (
                    "express" if ord_row["shipping_cost"] >= 10 else "standard"
                )
                min_d, max_d = TIER_DAYS[tier]
                shipped_at = odate + timedelta(hours=self.rng.randint(2, 36))
                est_delivery = shipped_at + timedelta(days=self.rng.randint(min_d, max_d))

                if status in ("delivered", "returned"):
                    delivered_at = est_delivery + timedelta(hours=self.rng.randint(-12, 24))
                    ship_status = "delivered"
                elif status == "shipped":
                    delivered_at = None
                    ship_status = "in_transit"
                else:
                    delivered_at = None
                    ship_status = "label_created"

                shipments.append({
                    "shipment_id": self._uuid(),
                    "order_id": oid,
                    "carrier": carrier,
                    "tracking_number": f"{carrier[:2].upper()}{self.rng.randint(1000000000, 9999999999)}",
                    "shipping_tier": tier,
                    "shipped_at": shipped_at,
                    "estimated_delivery_at": est_delivery,
                    "delivered_at": delivered_at,
                    "status": ship_status,
                })

                if status == "returned":
                    ord_items = items_by_order.get(oid, [])
                    if ord_items:
                        chosen = self.rng.choice(ord_items)
                        ret_item_id = chosen["order_item_id"]
                        refund_amt = round(chosen["line_total"], 2)
                    else:
                        ret_item_id = None
                        refund_amt = 0.0
                    base_dt = delivered_at or shipped_at
                    returns.append({
                        "return_id": self._uuid(),
                        "order_id": oid,
                        "order_item_id": ret_item_id,
                        "customer_id": ord_row["customer_id"],
                        "return_reason": self.rng.choice(RETURN_REASONS),
                        "refund_amount": refund_amt,
                        "returned_at": base_dt + timedelta(days=self.rng.randint(1, 21)),
                        "restocked": self.rng.random() < 0.78,
                    })

        # Inventory snapshots (sample store x SKU combinations scaled cleanly)
        snapshots: list[dict] = []
        store_ids = stores["store_id"].to_list() if stores is not None and not stores.is_empty() else []
        product_ids = products.filter(pl.col("is_active"))["product_id"].to_list() if products is not None and not products.is_empty() else []

        if store_ids and product_ids:
            target_snaps = min(5000, max(200, len(store_ids) * 20))
            snap_date = self.config.date_range.end
            for _ in range(target_snaps):
                on_hand = max(0, int(self.rng.gauss(35, 25)))
                reorder_pt = self.rng.choice([5, 10, 15, 20])
                snapshots.append({
                    "snapshot_id": self._uuid(),
                    "snapshot_date": snap_date,
                    "store_id": self.rng.choice(store_ids),
                    "product_id": self.rng.choice(product_ids),
                    "on_hand_qty": on_hand,
                    "reorder_point": reorder_pt,
                    "is_stockout": on_hand == 0,
                })

        shipments_df = pl.DataFrame(shipments).cast({
            "shipped_at": pl.Datetime,
            "estimated_delivery_at": pl.Datetime,
            "delivered_at": pl.Datetime,
        }) if shipments else pl.DataFrame(schema={
            "shipment_id": pl.Utf8, "order_id": pl.Utf8, "carrier": pl.Utf8,
            "tracking_number": pl.Utf8, "shipping_tier": pl.Utf8,
            "shipped_at": pl.Datetime, "estimated_delivery_at": pl.Datetime,
            "delivered_at": pl.Datetime, "status": pl.Utf8,
        })

        returns_df = pl.DataFrame(returns).cast({
            "refund_amount": pl.Float64,
            "returned_at": pl.Datetime,
            "restocked": pl.Boolean,
        }) if returns else pl.DataFrame(schema={
            "return_id": pl.Utf8, "order_id": pl.Utf8, "order_item_id": pl.Utf8,
            "customer_id": pl.Utf8, "return_reason": pl.Utf8,
            "refund_amount": pl.Float64, "returned_at": pl.Datetime, "restocked": pl.Boolean,
        })

        snapshots_df = pl.DataFrame(snapshots).cast({
            "snapshot_date": pl.Date,
            "on_hand_qty": pl.Int64,
            "reorder_point": pl.Int64,
            "is_stockout": pl.Boolean,
        }) if snapshots else pl.DataFrame(schema={
            "snapshot_id": pl.Utf8, "snapshot_date": pl.Date, "store_id": pl.Utf8,
            "product_id": pl.Utf8, "on_hand_qty": pl.Int64,
            "reorder_point": pl.Int64, "is_stockout": pl.Boolean,
        })

        return {
            "shipments": shipments_df,
            "returns": returns_df,
            "inventory_snapshots": snapshots_df,
        }
