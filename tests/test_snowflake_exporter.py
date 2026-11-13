"""Unit tests for SnowflakeExporter with mocked connector."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from ecommerce_synth.exporters.base import ExportConfig
from ecommerce_synth.exporters.snowflake import SnowflakeExporter


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


def test_snowflake_missing_sdk_raises_import_error(sample_data_dir: Path) -> None:
    config = ExportConfig(
        target="snowflake",
        data_dir=sample_data_dir,
        database="MY_DB",
        schema_name="MY_SCHEMA",
    )
    exporter = SnowflakeExporter(config)

    with patch.dict(sys.modules, {"snowflake": None, "snowflake.connector": None}):
        with pytest.raises(ImportError) as exc_info:
            exporter.validate_prerequisites()
        assert "pip install 'ecommerce-synth[snowflake]'" in str(exc_info.value)


def test_snowflake_missing_database_raises_value_error(sample_data_dir: Path) -> None:
    config = ExportConfig(
        target="snowflake",
        data_dir=sample_data_dir,
        database=None,
        schema_name="MY_SCHEMA",
    )
    exporter = SnowflakeExporter(config)
    mock_snow = MagicMock()
    with patch.dict(sys.modules, {"snowflake": mock_snow, "snowflake.connector": mock_snow}):
        with pytest.raises(ValueError) as exc_info:
            exporter.validate_prerequisites()
        assert "database name is required" in str(exc_info.value)


def test_snowflake_export_mocked(sample_data_dir: Path) -> None:
    config = ExportConfig(
        target="snowflake",
        data_dir=sample_data_dir,
        database="ANALYTICS_DB",
        schema_name="ECOMMERCE",
        warehouse="LOAD_WH",
        extra_params={"account": "test_account", "user": "test_user"},
    )
    exporter = SnowflakeExporter(config)

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    # Mock cursor fetchall for count query
    mock_cursor.fetchall.return_value = [(2,)]
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    exporter._conn = mock_conn

    mock_snow = MagicMock()
    mock_snow.connect.return_value = mock_conn

    with patch.dict(sys.modules, {"snowflake": mock_snow, "snowflake.connector": mock_snow}):
        result = exporter.export()

    assert result.target == "snowflake"
    assert result.destination == "ANALYTICS_DB.ECOMMERCE"
    assert "customers" in result.tables_exported
    assert result.total_rows == 2

    executed_queries = [call[0][0] for call in mock_cursor.execute.call_args_list]
    assert any("CREATE SCHEMA IF NOT EXISTS ANALYTICS_DB.ECOMMERCE;" in q for q in executed_queries)
    assert any("CREATE STAGE IF NOT EXISTS ANALYTICS_DB.ECOMMERCE.ecommerce_stage;" in q for q in executed_queries)
    assert any("PUT file://" in q for q in executed_queries)
    assert any("CREATE OR REPLACE TABLE ANALYTICS_DB.ECOMMERCE.customers" in q for q in executed_queries)
    assert any("COPY INTO ANALYTICS_DB.ECOMMERCE.customers" in q for q in executed_queries)


def test_snowflake_discover_connection_name(sample_data_dir: Path) -> None:
    config = ExportConfig(
        target="snowflake",
        data_dir=sample_data_dir,
        database="MY_DB",
        schema_name="MY_SCHEMA",
    )
    exporter = SnowflakeExporter(config)

    # 1. When explicit profile is provided
    exporter.connection_name = "custom_profile"
    assert exporter._discover_connection_name() == "custom_profile"

    # Mock snowflake.connector.config_manager.CONFIG_MANAGER
    exporter.connection_name = None
    mock_cm_mod = MagicMock()
    mock_connector_mod = MagicMock()
    mock_connector_mod.config_manager = mock_cm_mod
    mock_snow = MagicMock()
    mock_snow.connector = mock_connector_mod

    # 2. When config_manager has 'default'
    mock_cm_mod.CONFIG_MANAGER.get.return_value = {"default": {"user": "u1"}}
    with patch.dict(sys.modules, {
        "snowflake": mock_snow,
        "snowflake.connector": mock_connector_mod,
        "snowflake.connector.config_manager": mock_cm_mod,
    }):
        assert exporter._discover_connection_name() == "default"

        # 3. When config_manager has typo 'defautlt'
        mock_cm_mod.CONFIG_MANAGER.get.return_value = {"defautlt": {"user": "u1"}, "other": {}}
        assert exporter._discover_connection_name() == "defautlt"

        # 4. When single connection exists
        mock_cm_mod.CONFIG_MANAGER.get.return_value = {"my_prod_conn": {"user": "u1"}}
        assert exporter._discover_connection_name() == "my_prod_conn"

        # 5. When no connections exist
        mock_cm_mod.CONFIG_MANAGER.get.return_value = {}
        assert exporter._discover_connection_name() is None



