"""Unit tests for DatabricksExporter with mocked SDK."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from ecommerce_synth.exporters.base import ExportConfig
from ecommerce_synth.exporters.databricks import DatabricksExporter


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


def test_databricks_missing_sdk_raises_import_error(sample_data_dir: Path) -> None:
    config = ExportConfig(
        target="databricks",
        data_dir=sample_data_dir,
        catalog="my_catalog",
        schema_name="my_schema",
    )
    exporter = DatabricksExporter(config)

    with patch.dict(sys.modules, {"databricks": None, "databricks.sdk": None}):
        with pytest.raises(ImportError) as exc_info:
            exporter.validate_prerequisites()
        assert "pip install 'ecommerce-synth[databricks]'" in str(exc_info.value)


def test_databricks_missing_catalog_raises_value_error(sample_data_dir: Path) -> None:
    config = ExportConfig(
        target="databricks",
        data_dir=sample_data_dir,
        catalog=None,
        schema_name="my_schema",
    )
    exporter = DatabricksExporter(config)
    mock_sdk = MagicMock()
    with patch.dict(sys.modules, {"databricks": mock_sdk, "databricks.sdk": mock_sdk}):
        with pytest.raises(ValueError) as exc_info:
            exporter.validate_prerequisites()
        assert "catalog name is required" in str(exc_info.value)


def test_databricks_export_mocked(sample_data_dir: Path) -> None:
    config = ExportConfig(
        target="databricks",
        data_dir=sample_data_dir,
        catalog="main",
        schema_name="ecommerce_test",
        warehouse="wh_123",
    )
    exporter = DatabricksExporter(config)

    mock_client = MagicMock()
    # Mock warehouse list and execution
    wh = MagicMock()
    wh.id = "wh_123"
    mock_client.warehouses.list.return_value = [wh]

    # Mock count result
    mock_res = MagicMock()
    mock_res.result.data_array = [["2"]]
    mock_client.statement_execution.execute_statement.return_value = mock_res

    exporter._client = mock_client
    mock_sdk = MagicMock()
    mock_sdk.WorkspaceClient.return_value = mock_client

    with patch.dict(sys.modules, {"databricks": mock_sdk, "databricks.sdk": mock_sdk}):
        result = exporter.export()

    assert result.target == "databricks"
    assert result.destination == "main.ecommerce_test"
    assert "customers" in result.tables_exported
    assert result.total_rows == 2

    # Verify upload was called for customers.parquet
    assert mock_client.files.upload.called
    uploaded_path = mock_client.files.upload.call_args[0][0]
    assert uploaded_path == "/Volumes/main/ecommerce_test/ecommerce_raw/customers.parquet"

    # Verify SQL statements executed
    executed_statements = [
        call.kwargs["statement"] for call in mock_client.statement_execution.execute_statement.call_args_list
    ]
    assert any("CREATE SCHEMA IF NOT EXISTS main.ecommerce_test;" in s for s in executed_statements)
    assert any("CREATE VOLUME IF NOT EXISTS main.ecommerce_test.ecommerce_raw;" in s for s in executed_statements)
    assert any("CREATE OR REPLACE TABLE main.ecommerce_test.customers USING DELTA" in s for s in executed_statements)
