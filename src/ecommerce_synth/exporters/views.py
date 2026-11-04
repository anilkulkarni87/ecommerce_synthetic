"""Analytical views generator for Databricks, Snowflake, BigQuery, and DuckDB."""

from __future__ import annotations


class ViewGenerator:
    """Generates engine-specific SQL for analytical views."""

    @staticmethod
    def get_view_sql(
        view_name: str,
        dialect: str,
        catalog_or_project: str | None = None,
        schema_or_dataset: str | None = None,
    ) -> str:
        """Return the CREATE VIEW statement for the specified analytical view."""
        d = dialect.lower()

        # Build qualified prefix if provided
        def q(name: str) -> str:
            if not catalog_or_project or not schema_or_dataset:
                return name
            if d == "bigquery":
                return f"`{catalog_or_project}.{schema_or_dataset}.{name}`"
            return f"{catalog_or_project}.{schema_or_dataset}.{name}"

        target_view = q(view_name)
        orders_online = q("orders_online")
        orders_instore = q("orders_instore")
        customers = q("customers")
        omnichannel_sales = q("v_omnichannel_sales")

        if view_name == "v_omnichannel_sales":
            return f"""CREATE OR REPLACE VIEW {target_view} AS
SELECT 
    order_id AS transaction_id,
    'online' AS channel,
    customer_id,
    order_date AS transaction_date,
    status,
    total_amount,
    payment_method,
    device_type
FROM {orders_online}
UNION ALL
SELECT 
    transaction_id,
    'instore' AS channel,
    customer_id,
    transaction_date,
    'completed' AS status,
    total_amount,
    payment_method,
    'pos' AS device_type
FROM {orders_instore};"""

        elif view_name == "v_customer_360":
            return f"""CREATE OR REPLACE VIEW {target_view} AS
SELECT 
    c.customer_id,
    c.first_name || ' ' || c.last_name AS full_name,
    c.email,
    c.customer_segment,
    c.channel_acquired,
    COUNT(s.transaction_id) AS total_orders,
    COALESCE(SUM(s.total_amount), 0.0) AS lifetime_spend,
    MAX(s.transaction_date) AS last_order_date
FROM {customers} c
LEFT JOIN {omnichannel_sales} s ON c.customer_id = s.customer_id
GROUP BY 1, 2, 3, 4, 5;"""

        else:
            raise ValueError(f"Unknown view: {view_name}")

    @classmethod
    def get_all_views(
        cls,
        dialect: str,
        catalog_or_project: str | None = None,
        schema_or_dataset: str | None = None,
    ) -> list[tuple[str, str]]:
        """Return all available views as list of (view_name, create_sql)."""
        return [
            ("v_omnichannel_sales", cls.get_view_sql("v_omnichannel_sales", dialect, catalog_or_project, schema_or_dataset)),
            ("v_customer_360", cls.get_view_sql("v_customer_360", dialect, catalog_or_project, schema_or_dataset)),
        ]
