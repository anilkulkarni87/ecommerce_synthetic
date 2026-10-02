"""Tests for synthetic data generators."""

import pytest
import polars as pl

from ecommerce_synth.config import load_config
from ecommerce_synth.generators.customer_generator import CustomerGenerator
from ecommerce_synth.generators.product_generator import ProductGenerator
from ecommerce_synth.generators.store_generator import StoreGenerator
from ecommerce_synth.generators.order_generator import OrderGenerator
from ecommerce_synth.generators.clickstream_generator import ClickstreamGenerator
from ecommerce_synth.generators.email_generator import EmailGenerator
from ecommerce_synth.generators.loyalty_generator import LoyaltyGenerator
from ecommerce_synth.generators.review_generator import ReviewGenerator
from ecommerce_synth.generators.support_generator import SupportGenerator
from ecommerce_synth.generators.experiment_generator import ExperimentGenerator
from ecommerce_synth.generators.fraud_generator import FraudGenerator


@pytest.fixture(scope="module")
def small_config(tmp_path_factory):
    tmp_dir = tmp_path_factory.mktemp("test_output")
    cfg = load_config(tier_name="small", seed=42, output_dir=tmp_dir)
    return cfg


def test_product_generator(small_config):
    gen = ProductGenerator(small_config)
    products = gen.generate()

    assert isinstance(products, pl.DataFrame)
    assert products.height == small_config.product_count
    assert "product_id" in products.columns
    assert "category" in products.columns
    assert "price" in products.columns
    assert products.filter(pl.col("product_id").is_null()).height == 0


def test_store_generator(small_config):
    gen = StoreGenerator(small_config)
    stores = gen.generate()

    assert isinstance(stores, pl.DataFrame)
    assert stores.height == small_config.store_count
    assert "store_id" in stores.columns
    assert "state" in stores.columns
    assert stores.filter(pl.col("store_id").is_null()).height == 0


def test_customer_generator(small_config):
    gen = CustomerGenerator(small_config)
    res = gen.generate()

    assert "customers" in res
    assert "addresses" in res
    customers = res["customers"]
    addresses = res["addresses"]

    assert customers.height == small_config.tier.customers
    assert addresses.height >= customers.height  # at least 1 address per customer
    assert "_personas" in customers.__dict__


def test_order_generator(small_config):
    cust_gen = CustomerGenerator(small_config)
    cust_res = cust_gen.generate()
    prod_gen = ProductGenerator(small_config)
    products = prod_gen.generate()
    store_gen = StoreGenerator(small_config)
    stores = store_gen.generate()

    order_gen = OrderGenerator(small_config)
    order_res = order_gen.generate(
        customers=cust_res["customers"],
        addresses=cust_res["addresses"],
        products=products,
        stores=stores,
    )

    assert "orders_online" in order_res
    assert "order_items_online" in order_res
    assert "orders_instore" in order_res
    assert "order_items_instore" in order_res
    assert "instore_accounts" in order_res

    assert order_res["orders_online"].height > 0
    assert order_res["order_items_online"].height >= order_res["orders_online"].height
    assert order_res["orders_instore"].height > 0


def test_clickstream_generator(small_config):
    cust_gen = CustomerGenerator(small_config)
    cust_res = cust_gen.generate()
    prod_gen = ProductGenerator(small_config)
    products = prod_gen.generate()

    click_gen = ClickstreamGenerator(small_config)
    clickstream = click_gen.generate(
        customers=cust_res["customers"],
        products=products,
    )

    assert isinstance(clickstream, pl.DataFrame)
    assert clickstream.height > 0
    assert "event_type" in clickstream.columns
    assert "session_id" in clickstream.columns


def test_email_generator(small_config):
    cust_gen = CustomerGenerator(small_config)
    cust_res = cust_gen.generate()

    email_gen = EmailGenerator(small_config)
    res = email_gen.generate(customers=cust_res["customers"])

    assert "email_campaigns" in res
    assert "email_events" in res
    assert res["email_campaigns"].height > 0
    assert res["email_events"].height > 0


def test_loyalty_generator(small_config):
    cust_gen = CustomerGenerator(small_config)
    cust_res = cust_gen.generate()

    loyalty_gen = LoyaltyGenerator(small_config)
    res = loyalty_gen.generate(
        customers=cust_res["customers"],
        orders_online=pl.DataFrame(),
        orders_instore=pl.DataFrame(),
    )

    assert "loyalty_members" in res
    assert "loyalty_transactions" in res
    assert "loyalty_members" in res
    assert "loyalty_transactions" in res
    assert res["loyalty_members"].height > 0


def test_support_generator(small_config):
    cust_gen = CustomerGenerator(small_config)
    cust_res = cust_gen.generate()

    support_gen = SupportGenerator(small_config)
    support_tickets = support_gen.generate(
        customers=cust_res["customers"],
        orders_online=pl.DataFrame(),
        orders_instore=pl.DataFrame(),
    )

    assert isinstance(support_tickets, pl.DataFrame)
    assert support_tickets.height > 0
    assert "ticket_id" in support_tickets.columns
    assert "category" in support_tickets.columns


def test_experiment_generator(small_config):
    cust_gen = CustomerGenerator(small_config)
    cust_res = cust_gen.generate()

    exp_gen = ExperimentGenerator(small_config)
    res = exp_gen.generate(
        customers=cust_res["customers"],
        orders_online=pl.DataFrame(),
    )

    assert "experiments" in res
    assert "experiment_assignments" in res
    assert res["experiments"].height > 0
    assert res["experiment_assignments"].height > 0


def test_fraud_generator(small_config):
    cust_gen = CustomerGenerator(small_config)
    cust_res = cust_gen.generate()

    fraud_gen = FraudGenerator(small_config)
    fraud_flags = fraud_gen.generate(
        customers=cust_res["customers"],
        orders_online=pl.DataFrame(),
        orders_instore=pl.DataFrame(),
        clickstream=pl.DataFrame(),
    )

    assert isinstance(fraud_flags, pl.DataFrame)
    assert "risk_score" in fraud_flags.columns
    assert "is_confirmed_fraud" in fraud_flags.columns
