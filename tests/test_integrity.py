"""Referential integrity and foreign key validation tests."""

import pytest
import polars as pl
from pathlib import Path

from ecommerce_synth.config import load_config
from ecommerce_synth.orchestrator import Orchestrator


@pytest.fixture(scope="module")
def generated_dataset(tmp_path_factory):
    output_dir = tmp_path_factory.mktemp("e2e_dataset")
    config = load_config(tier_name="small", seed=123, output_dir=output_dir)
    orchestrator = Orchestrator(config)
    orchestrator.run()
    return output_dir


def test_manifest_exists(generated_dataset: Path):
    manifest_path = generated_dataset / "_manifest.json"
    assert manifest_path.exists()


def test_customer_addresses_fk(generated_dataset: Path):
    customers = pl.read_parquet(generated_dataset / "customers.parquet")
    addresses = pl.read_parquet(generated_dataset / "addresses.parquet")

    customer_ids = set(customers["customer_id"].to_list())
    address_customer_ids = addresses["customer_id"].to_list()

    for cid in address_customer_ids:
        assert cid in customer_ids, f"Address customer_id {cid} not found in customers"


def test_orders_customers_fk(generated_dataset: Path):
    customers = pl.read_parquet(generated_dataset / "customers.parquet")
    orders_online = pl.read_parquet(generated_dataset / "orders_online.parquet")

    customer_ids = set(customers["customer_id"].to_list())
    order_customer_ids = orders_online["customer_id"].to_list()

    for cid in order_customer_ids:
        assert cid in customer_ids, f"Order customer_id {cid} not found in customers"


def test_order_items_online_fk(generated_dataset: Path):
    orders_online = pl.read_parquet(generated_dataset / "orders_online.parquet")
    order_items_online = pl.read_parquet(generated_dataset / "order_items_online.parquet")
    products = pl.read_parquet(generated_dataset / "products.parquet")

    order_ids = set(orders_online["order_id"].to_list())
    product_ids = set(products["product_id"].to_list())

    for oid in order_items_online["order_id"].to_list():
        assert oid in order_ids, f"Item order_id {oid} not found in orders_online"

    for pid in order_items_online["product_id"].to_list():
        assert pid in product_ids, f"Item product_id {pid} not found in products"


def test_orders_instore_stores_fk(generated_dataset: Path):
    stores = pl.read_parquet(generated_dataset / "stores.parquet")
    orders_instore = pl.read_parquet(generated_dataset / "orders_instore.parquet")

    store_ids = set(stores["store_id"].to_list())
    for sid in orders_instore["store_id"].to_list():
        assert sid in store_ids, f"In-store order store_id {sid} not found in stores"


def test_loyalty_members_fk(generated_dataset: Path):
    customers = pl.read_parquet(generated_dataset / "customers.parquet")
    loyalty_members = pl.read_parquet(generated_dataset / "loyalty_members.parquet")

    customer_ids = set(customers["customer_id"].to_list())
    for cid in loyalty_members["customer_id"].to_list():
        assert cid in customer_ids, f"Loyalty member customer_id {cid} not found in customers"


def test_fraud_flags_fk(generated_dataset: Path):
    customers = pl.read_parquet(generated_dataset / "customers.parquet")
    fraud_flags = pl.read_parquet(generated_dataset / "fraud_flags.parquet")

    customer_ids = set(customers["customer_id"].to_list())
    for cid in fraud_flags["customer_id"].to_list():
        assert cid in customer_ids, f"Fraud flag customer_id {cid} not found in customers"


def test_clickstream_order_session_linking(generated_dataset: Path):
    orders_online = pl.read_parquet(generated_dataset / "orders_online.parquet")
    clickstream = pl.read_parquet(generated_dataset / "clickstream.parquet")

    click_sessions = set(clickstream["session_id"].to_list())
    purchase_sessions = set(
        clickstream.filter(pl.col("event_type") == "purchase")["session_id"].to_list()
    )

    order_sessions = orders_online["session_id"].to_list()
    assert len(order_sessions) > 0
    for sid in order_sessions:
        assert sid in click_sessions, f"Order session_id {sid} missing from clickstream"
        assert sid in purchase_sessions, f"Order session_id {sid} missing purchase event in clickstream"


def test_identity_noise_end_to_end(tmp_path: Path):
    output_dir = tmp_path / "messy_dataset"
    config = load_config(tier_name="small", seed=77, output_dir=output_dir, identity_noise=0.20)
    orchestrator = Orchestrator(config)
    orchestrator.run()

    customers = pl.read_parquet(output_dir / "customers.parquet")
    gt_path = output_dir / "identity_ground_truth.parquet"
    assert gt_path.exists()

    gt = pl.read_parquet(gt_path)
    assert gt.height == customers.height
    assert gt.filter(pl.col("is_duplicate")).height > 0

    cust_ids = set(customers["customer_id"].to_list())
    assert set(gt["customer_id"].to_list()) == cust_ids
    for teid in gt["true_entity_id"].to_list():
        assert teid in cust_ids
