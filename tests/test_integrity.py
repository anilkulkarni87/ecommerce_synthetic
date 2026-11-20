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
    known_orders = orders_online.filter(pl.col("customer_id").is_not_null())
    assert known_orders.height > 0

    for cid in known_orders["customer_id"].to_list():
        assert cid in customer_ids, f"Order customer_id {cid} not found in customers"

    # Guest checkouts should have null customer_id and non-null guest_email
    guests = orders_online.filter(pl.col("customer_id").is_null())
    if guests.height > 0:
        assert guests["guest_email"].null_count() == 0


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
    instore_accounts = pl.read_parquet(output_dir / "instore_accounts.parquet")
    gt_path = output_dir / "identity_ground_truth.parquet"
    assert gt_path.exists()

    gt = pl.read_parquet(gt_path)
    assert gt.height == customers.height + instore_accounts.height
    assert gt.filter(pl.col("is_duplicate")).height > 0

    cust_ids = set(customers["customer_id"].to_list())
    acct_ids = set(instore_accounts["instore_account_id"].to_list())
    gt_cust = gt.filter(pl.col("record_type") == "customer")
    gt_pos = gt.filter(pl.col("record_type") == "instore_account")
    assert set(gt_cust["customer_id"].to_list()) == cust_ids
    assert set(gt_pos["instore_account_id"].to_list()) == acct_ids
    assert "pos_cross_channel" in set(gt_pos["noise_type"].to_list())
    assert "pos_only" in set(gt_pos["noise_type"].to_list())
    valid_entities = cust_ids | acct_ids
    for teid in gt["true_entity_id"].to_list():
        assert teid in valid_entities


def test_chunked_parquet_persistence_and_duckdb(tmp_path: Path):
    import json
    import duckdb
    from ecommerce_synth.exporters.base import ExportConfig
    from ecommerce_synth.exporters.duckdb import DuckDBExporter
    from ecommerce_synth.utils.writer import read_table_parquet

    output_dir = tmp_path / "chunked_dataset"
    # Small tier has 50,000 clickstream events -> with chunk_size=10000 it writes 5 chunks
    config = load_config(tier_name="small", seed=55, output_dir=output_dir, chunk_size=10_000)
    orchestrator = Orchestrator(config)
    orchestrator.run()

    chunk_dir = output_dir / "clickstream"
    assert chunk_dir.is_dir()
    parts = sorted(chunk_dir.glob("part-*.parquet"))
    assert len(parts) == 5

    with open(output_dir / "_manifest.json") as f:
        manifest = json.load(f)
    assert manifest["chunk_counts"]["clickstream"] == 5
    assert manifest["row_counts"]["clickstream"] == 50_000

    df_full = read_table_parquet(output_dir, "clickstream")
    assert df_full is not None and df_full.height == 50_000

    # Verify DuckDB exporter ingests chunked directory cleanly
    db_file = tmp_path / "chunked.duckdb"
    exp = DuckDBExporter(ExportConfig(target="duckdb", data_dir=output_dir, database=str(db_file), create_views=False))
    exp.export()
    conn = duckdb.connect(str(db_file))
    assert conn.execute("SELECT COUNT(*) FROM clickstream").fetchone()[0] == 50_000
    conn.close()


def test_global_regions_and_compliance(tmp_path: Path):
    output_dir = tmp_path / "global_dataset"
    config = load_config(
        tier_name="small",
        seed=88,
        output_dir=output_dir,
        regions="US,GB,DE,JP",
        compliance_mode=True,
    )
    orchestrator = Orchestrator(config)
    orchestrator.run(only=["customers"])

    addresses = pl.read_parquet(output_dir / "addresses.parquet")
    countries = set(addresses["country"].to_list())
    assert len(countries) > 1
    assert countries.issubset({"US", "GB", "DE", "JP"})

    consents_path = output_dir / "customer_consents.parquet"
    assert consents_path.exists()
    consents = pl.read_parquet(consents_path)
    assert consents.height > 0
    assert set(consents["jurisdiction"].to_list()).issubset({"CCPA", "UK_GDPR", "GDPR", "APPI"})


def test_direct_stream_to_duckdb_no_local_files(tmp_path: Path):
    import duckdb
    from ecommerce_synth.exporters.base import ExportConfig
    from ecommerce_synth.exporters.duckdb import DuckDBExporter

    local_out = tmp_path / "should_stay_empty"
    db_file = tmp_path / "streamed_live.duckdb"

    config = load_config(tier_name="small", seed=12, output_dir=local_out, chunk_size=10_000)
    stream_exp = DuckDBExporter(
        ExportConfig(target="duckdb", data_dir=None, database=str(db_file), schema_name="live_ecom")
    )
    orchestrator = Orchestrator(config, stream_exporter=stream_exp)
    orchestrator.run()

    # Zero local Parquet files should have been created
    assert not local_out.exists()
    assert db_file.exists()

    conn = duckdb.connect(str(db_file))
    assert conn.execute("SELECT COUNT(*) FROM live_ecom.clickstream").fetchone()[0] == 50_000
    assert conn.execute("SELECT COUNT(*) FROM live_ecom.customers").fetchone()[0] == 500
    assert conn.execute("SELECT COUNT(*) FROM live_ecom.v_omnichannel_sales").fetchone()[0] > 0
    conn.close()


def test_multicurrency_vat_and_fulfillment_tables(tmp_path: Path):
    output_dir = tmp_path / "global_fulfillment"
    config = load_config(tier_name="small", seed=33, output_dir=output_dir, regions="US,GB,DE,JP")
    orchestrator = Orchestrator(config)
    orchestrator.run()

    orders = pl.read_parquet(output_dir / "orders_online.parquet")
    assert {"currency_code", "fx_rate_to_usd", "total_amount_usd", "tax_regime"}.issubset(set(orders.columns))
    assert len(set(orders["currency_code"].to_list())) > 1
    assert "VAT" in set(orders["tax_regime"].to_list())

    shipments = pl.read_parquet(output_dir / "shipments.parquet")
    returns = pl.read_parquet(output_dir / "returns.parquet")
    inventory = pl.read_parquet(output_dir / "inventory_snapshots.parquet")
    assert shipments.height > 0
    assert inventory.height > 0
    assert set(shipments["order_id"].to_list()).issubset(set(orders["order_id"].to_list()))
    if returns.height > 0:
        assert set(returns["order_id"].to_list()).issubset(set(orders["order_id"].to_list()))


def test_decoupled_pos_vs_digital_realism(generated_dataset: Path):
    customers = pl.read_parquet(generated_dataset / "customers.parquet")
    instore_accounts = pl.read_parquet(generated_dataset / "instore_accounts.parquet")
    orders_instore = pl.read_parquet(generated_dataset / "orders_instore.parquet")

    assert {"phone_number", "email"}.issubset(set(instore_accounts.columns))
    # POS tables do not natively store e-commerce customer_id UUIDs
    assert instore_accounts["customer_id"].null_count() == instore_accounts.height
    assert orders_instore["customer_id"].null_count() == orders_instore.height

    # Every POS account must have at least one contact identifier (phone, email, or both)
    phone_only = instore_accounts.filter(pl.col("phone_number").is_not_null() & pl.col("email").is_null()).height
    email_only = instore_accounts.filter(pl.col("phone_number").is_null() & pl.col("email").is_not_null()).height
    both = instore_accounts.filter(pl.col("phone_number").is_not_null() & pl.col("email").is_not_null()).height
    assert phone_only + email_only + both == instore_accounts.height
    assert phone_only > 0 and email_only > 0 and both > 0

    # Verify both omnichannel-stitchable POS accounts and POS-only accounts exist
    cust_emails = {e.strip().lower() for e in customers["email"].drop_nulls().to_list()}
    cust_phones = {"".join(ch for ch in p if ch.isdigit())[-10:] for p in customers["phone"].drop_nulls().to_list()}

    matched_accts: set[str] = set()
    unmatched_accts: set[str] = set()
    for row in instore_accounts.to_dicts():
        em = row["email"].strip().lower() if row["email"] else None
        ph = "".join(ch for ch in row["phone_number"] if ch.isdigit())[-10:] if row["phone_number"] else None
        if (em and em in cust_emails) or (ph and ph in cust_phones):
            matched_accts.add(row["instore_account_id"])
        else:
            unmatched_accts.add(row["instore_account_id"])

    assert len(matched_accts) > 0
    assert len(unmatched_accts) > 0

    # POS-only accounts must actually transact in orders_instore (not dead rows)
    tx_accts = set(orders_instore["instore_account_id"].drop_nulls().to_list())
    assert len(tx_accts.intersection(unmatched_accts)) > 0
    # Anonymous walk-in POS transactions must also exist
    assert orders_instore["instore_account_id"].null_count() > 0
    # Payment tokens should exist on card/mobile transactions across both channels
    orders_online = pl.read_parquet(generated_dataset / "orders_online.parquet")
    assert "payment_token" in orders_online.columns and "payment_token" in orders_instore.columns
    assert orders_online["payment_token"].drop_nulls().len() > 0
    assert orders_instore["payment_token"].drop_nulls().len() > 0

    # BOPIS & BORIS + clickstream anonymous_id checks
    assert "fulfillment_type" in orders_online.columns
    assert "bopis" in set(orders_online["fulfillment_type"].to_list())
    clickstream = pl.read_parquet(generated_dataset / "clickstream.parquet")
    assert "anonymous_id" in clickstream.columns
    assert clickstream["anonymous_id"].null_count() == 0
    stores = pl.read_parquet(generated_dataset / "stores.parquet")
    assert "country" in stores.columns


def test_paid_media_and_mmm_tables(generated_dataset: Path):
    ad_campaigns = pl.read_parquet(generated_dataset / "ad_campaigns.parquet")
    ad_spend = pl.read_parquet(generated_dataset / "ad_spend_daily.parquet")
    clickstream = pl.read_parquet(generated_dataset / "clickstream.parquet")

    assert ad_campaigns.height > 0
    assert ad_spend.height > 0
    camp_ids = set(ad_campaigns["campaign_id"].to_list())
    assert set(ad_spend["campaign_id"].to_list()).issubset(camp_ids)
    # Geo-lift holdouts should exist with 0 spend
    holdouts = ad_spend.filter(pl.col("is_holdout"))
    assert holdouts.height > 0
    assert holdouts["spend_usd"].sum() == 0.0

    # Clickstream paid sessions must link to valid ad_campaigns
    assert {"utm_source", "utm_medium", "utm_campaign"}.issubset(set(clickstream.columns))
    paid_utms = set(clickstream["utm_campaign"].drop_nulls().to_list())
    assert len(paid_utms) > 0
    assert paid_utms.issubset(camp_ids)
