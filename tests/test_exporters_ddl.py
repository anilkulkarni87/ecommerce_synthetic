"""Tests for DDL and View generators across Databricks, Snowflake, and BigQuery."""

from pathlib import Path
import pytest

from ecommerce_synth.exporters.ddl import DDLGenerator
from ecommerce_synth.exporters.views import ViewGenerator


@pytest.fixture
def ddl_gen() -> DDLGenerator:
    return DDLGenerator()


def test_ddl_generator_loads_19_tables(ddl_gen: DDLGenerator) -> None:
    assert len(ddl_gen.tables) == 19
    assert "customers" in ddl_gen.tables
    assert "orders_online" in ddl_gen.tables
    assert "fraud_flags" in ddl_gen.tables


def test_databricks_create_table_ddl(ddl_gen: DDLGenerator) -> None:
    sql = ddl_gen.generate_create_table_sql(
        table_name="customers",
        dialect="databricks",
        catalog_or_project="my_catalog",
        schema_or_dataset="my_schema",
    )
    assert "CREATE TABLE IF NOT EXISTS my_catalog.my_schema.customers" in sql
    assert "customer_id STRING NOT NULL COMMENT 'Primary key'" in sql
    assert "CONSTRAINT customers_pk PRIMARY KEY (customer_id)" in sql
    assert "COMMENT 'Customer accounts and demographic profiles" in sql


def test_snowflake_create_table_ddl(ddl_gen: DDLGenerator) -> None:
    sql = ddl_gen.generate_create_table_sql(
        table_name="orders_online",
        dialect="snowflake",
        catalog_or_project="MY_DB",
        schema_or_dataset="ECOMMERCE",
    )
    assert "CREATE TABLE IF NOT EXISTS MY_DB.ECOMMERCE.orders_online" in sql
    assert "order_id VARCHAR NOT NULL" in sql
    assert "total_amount FLOAT NOT NULL" in sql
    assert "CONSTRAINT orders_online_pk PRIMARY KEY (order_id)" in sql
    assert "COMMENT = 'E-commerce web checkout orders.'" in sql


def test_bigquery_create_table_ddl(ddl_gen: DDLGenerator) -> None:
    sql = ddl_gen.generate_create_table_sql(
        table_name="products",
        dialect="bigquery",
        catalog_or_project="my-project-123",
        schema_or_dataset="ecommerce_dataset",
    )
    assert "CREATE TABLE IF NOT EXISTS `my-project-123.ecommerce_dataset.products`" in sql
    assert "`product_id` STRING NOT NULL" in sql
    assert "`price` FLOAT64 NOT NULL" in sql
    assert "PRIMARY KEY (`product_id`) NOT ENFORCED" in sql
    assert "OPTIONS(description='Fixed dimension product catalog" in sql


def test_foreign_keys_generation(ddl_gen: DDLGenerator) -> None:
    # orders_online has shipping_address_id -> addresses.address_id
    db_fks = ddl_gen.generate_foreign_keys_sql(
        table_name="orders_online",
        dialect="databricks",
        catalog_or_project="cat",
        schema_or_dataset="sch",
    )
    assert len(db_fks) > 0
    assert any("REFERENCES cat.sch.customers (customer_id)" in fk for fk in db_fks)
    assert any("REFERENCES cat.sch.addresses (address_id)" in fk for fk in db_fks)

    bq_fks = ddl_gen.generate_foreign_keys_sql(
        table_name="orders_online",
        dialect="bigquery",
        catalog_or_project="proj",
        schema_or_dataset="ds",
    )
    assert len(bq_fks) > 0
    assert any("REFERENCES `proj.ds.customers` (`customer_id`) NOT ENFORCED" in fk for fk in bq_fks)

    # Polymorphic FKs (e.g. fraud_flags.entity_id pointing to multiple tables) should be skipped
    fraud_fks = ddl_gen.generate_foreign_keys_sql(
        table_name="fraud_flags",
        dialect="databricks",
        catalog_or_project="cat",
        schema_or_dataset="sch",
    )
    # customer_id should be included, entity_id (polymorphic) should be safely omitted
    assert any("REFERENCES cat.sch.customers (customer_id)" in fk for fk in fraud_fks)
    assert not any("entity_id" in fk for fk in fraud_fks)


def test_ctas_and_copy_sql(ddl_gen: DDLGenerator) -> None:
    ctas = ddl_gen.generate_databricks_ctas_sql("customers", "cat", "sch", "raw_files")
    assert "CREATE OR REPLACE TABLE cat.sch.customers USING DELTA AS SELECT * FROM read_files('/Volumes/cat/sch/raw_files/customers.parquet');" == ctas

    copy_sql = ddl_gen.generate_snowflake_copy_sql("customers", "DB", "SCH", "MY_STAGE")
    assert "COPY INTO DB.SCH.customers FROM @MY_STAGE/customers.parquet FILE_FORMAT = (TYPE = PARQUET) MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE;" == copy_sql


def test_view_generator_all_dialects() -> None:
    views_db = ViewGenerator.get_all_views("databricks", "cat", "sch")
    assert len(views_db) == 2
    assert views_db[0][0] == "v_omnichannel_sales"
    assert "cat.sch.orders_online" in views_db[0][1]
    assert views_db[1][0] == "v_customer_360"
    assert "cat.sch.v_omnichannel_sales" in views_db[1][1]

    views_bq = ViewGenerator.get_all_views("bigquery", "proj", "ds")
    assert "`proj.ds.orders_online`" in views_bq[0][1]
    assert "`proj.ds.v_omnichannel_sales`" in views_bq[1][1]
