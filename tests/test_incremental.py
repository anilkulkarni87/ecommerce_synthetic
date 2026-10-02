"""Tests for incremental generation mode."""

import json
from pathlib import Path
import polars as pl
import pytest

from ecommerce_synth.config import load_config
from ecommerce_synth.incremental import IncrementalGenerator
from ecommerce_synth.orchestrator import Orchestrator


@pytest.fixture
def base_run(tmp_path: Path):
    output_dir = tmp_path / "base_dataset"
    config = load_config(tier_name="small", seed=77, output_dir=output_dir)
    orchestrator = Orchestrator(config)
    orchestrator.run()
    return output_dir


def test_incremental_single_batch(base_run: Path):
    # Read base row counts
    base_orders = pl.read_parquet(base_run / "orders_online.parquet")
    base_count = base_orders.height

    # Run incremental generation for 2 days
    inc_gen = IncrementalGenerator(
        base_dir=base_run,
        days=2,
        daily_batches=False,
        append=True,
    )
    result = inc_gen.run()

    # Verify orders increased
    updated_orders = pl.read_parquet(base_run / "orders_online.parquet")
    assert updated_orders.height > base_count

    # Check manifest updated
    with open(base_run / "_manifest.json") as f:
        manifest = json.load(f)
    assert manifest.get("is_incremental") is True
    assert "incremental_state" in manifest


def test_incremental_daily_batches(base_run: Path):
    # Run incremental generation with daily batches
    inc_gen = IncrementalGenerator(
        base_dir=base_run,
        days=3,
        daily_batches=True,
        append=True,
    )
    inc_gen.run()

    # Check batch subdirectories created
    batch_dirs = list(base_run.glob("batches/day_*"))
    assert len(batch_dirs) == 3
    for bdir in batch_dirs:
        assert (bdir / "orders_online.parquet").exists()
