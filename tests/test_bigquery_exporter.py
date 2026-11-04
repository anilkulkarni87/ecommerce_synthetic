"""Unit tests for BigQueryExporter with mocked client."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from ecommerce_synth.exporters.base import ExportConfig
from ecommerce_synth.exporters.bigquery import BigQueryExporter


@pytest.fixture
def sample_data_dir(tmp_path: Path) -> Path:
    import polars as pl
    df = pl.DataFrame({"customer_id": ["c1", "c2"], "first_name": ["Alice", "Bob"]})
    df.write_parquet(tmp_path / "customers.parquet")
    manifest = {
        "row_counts": {"customers": 2},
    }
    import json
    with open(tmp_path / "_manifest.json", "w") as f:
        json.dump(manifest, f)
    return tmp_path


def test_bigquery_missing_sdk_raises_import_error(sample_data_dir: Path) -> None:
    config = ExportConfig(
        target="bigquery",
        data_dir=sample_data_dir,
        project="my-gcp-project",
        dataset="ecommerce_ds",
    )
    exporter = BigQueryExporter(config)

    with patch.dict(sys.modules, {"google": None, "google.cloud": None, "google.cloud.bigquery": None}):
        with pytest.raises(ImportError) as exc_info:
            exporter.validate_prerequisites()
        assert "pip install 'ecommerce-synth[bigquery]'" in str(exc_info.value)


def test_bigquery_missing_project_raises_value_error(sample_data_dir: Path) -> None:
    config = ExportConfig(
        target="bigquery",
        data_dir=sample_data_dir,
        project=None,
        dataset="ecommerce_ds",
    )
    exporter = BigQueryExporter(config)
    mock_bq = MagicMock()
    with patch.dict(sys.modules, {"google": mock_bq, "google.cloud": mock_bq, "google.cloud.bigquery": mock_bq}):
        with pytest.raises(ValueError) as exc_info:
            exporter.validate_prerequisites()
        assert "project ID is required" in str(exc_info.value)


def test_bigquery_export_mocked_direct_file(sample_data_dir: Path) -> None:
    config = ExportConfig(
        target="bigquery",
        data_dir=sample_data_dir,
        project="test-proj-42",
        dataset="ecommerce_test",
    )
    exporter = BigQueryExporter(config)

    mock_client = MagicMock()
    mock_bq = MagicMock()
    mock_bq.Client.return_value = mock_client

    # Mock count query result
    mock_row = MagicMock()
    mock_row.cnt = 2
    mock_query_job = MagicMock()
    mock_query_job.result.return_value = [mock_row]
    mock_client.query.return_value = mock_query_job

    exporter._client = mock_client

    with patch.dict(sys.modules, {"google": mock_bq, "google.cloud": mock_bq, "google.cloud.bigquery": mock_bq}):
        result = exporter.export()

    assert result.target == "bigquery"
    assert result.destination == "test-proj-42.ecommerce_test"
    assert "customers" in result.tables_exported
    assert result.total_rows == 2

    # Verify direct file load was called
    assert mock_client.load_table_from_file.called
    assert mock_client.create_dataset.called
    assert mock_client.query.called
