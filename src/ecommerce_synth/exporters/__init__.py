"""Multi-warehouse exporter package for ecommerce-synth.

Supports exporting synthetic datasets to:
- DuckDB (standalone portable analytical database)
- Databricks (Unity Catalog Delta tables & Volumes)
- Snowflake (Internal/External stages & native tables)
- Google Cloud BigQuery (Datasets & native tables)
"""

from .base import BaseExporter, ExportConfig, ExportResult
from .bigquery import BigQueryExporter
from .databricks import DatabricksExporter
from .duckdb import DuckDBExporter
from .snowflake import SnowflakeExporter

__all__ = [
    "BaseExporter",
    "ExportConfig",
    "ExportResult",
    "DuckDBExporter",
    "DatabricksExporter",
    "SnowflakeExporter",
    "BigQueryExporter",
]
