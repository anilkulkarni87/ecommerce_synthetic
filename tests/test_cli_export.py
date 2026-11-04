"""Tests for CLI export command."""

import json
from pathlib import Path
from typer.testing import CliRunner
import polars as pl
import pytest

from ecommerce_synth.cli import app

runner = CliRunner()


@pytest.fixture
def sample_dataset(tmp_path: Path) -> Path:
    df = pl.DataFrame({"customer_id": ["c1", "c2"], "first_name": ["Alice", "Bob"]})
    df.write_parquet(tmp_path / "customers.parquet")
    manifest = {
        "tier": "small",
        "row_counts": {"customers": 2},
    }
    with open(tmp_path / "_manifest.json", "w") as f:
        json.dump(manifest, f)
    return tmp_path


def test_cli_export_invalid_target(sample_dataset: Path) -> None:
    result = runner.invoke(app, ["export", str(sample_dataset), "--target", "invalid_warehouse"])
    assert result.exit_code != 0
    assert "Unknown export target 'invalid_warehouse'" in result.stdout


def test_cli_export_duckdb(sample_dataset: Path) -> None:
    db_out = sample_dataset / "test_cli.duckdb"
    result = runner.invoke(app, ["export", str(sample_dataset), "--target", "duckdb", "--database", str(db_out)])
    assert result.exit_code == 0
    assert "DuckDB bundle ready" in result.stdout
    assert db_out.exists()


def test_cli_export_databricks_missing_sdk(sample_dataset: Path) -> None:
    result = runner.invoke(
        app,
        ["export", str(sample_dataset), "--target", "databricks", "--catalog", "main", "--schema", "test_sch"],
    )
    # Exits with error code and prints friendly install hint
    assert result.exit_code != 0
    assert "pip install 'ecommerce-synth[databricks]'" in result.stdout


def test_cli_export_snowflake_missing_sdk(sample_dataset: Path) -> None:
    result = runner.invoke(
        app,
        ["export", str(sample_dataset), "--target", "snowflake", "--database", "TEST_DB", "--schema", "TEST_SCH"],
    )
    assert result.exit_code != 0
    assert "pip install 'ecommerce-synth[snowflake]'" in result.stdout


def test_cli_export_bigquery_missing_sdk(sample_dataset: Path) -> None:
    result = runner.invoke(
        app,
        ["export", str(sample_dataset), "--target", "bigquery", "--project", "test-proj", "--dataset", "test_ds"],
    )
    assert result.exit_code != 0
    assert "pip install 'ecommerce-synth[bigquery]'" in result.stdout

