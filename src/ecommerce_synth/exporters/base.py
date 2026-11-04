"""Base exporter interface and common models for multi-warehouse exports."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rich.console import Console

console = Console()


@dataclass
class ExportConfig:
    """Unified configuration for exporting synthetic data to any warehouse target."""

    target: str
    data_dir: Path | str
    catalog: str | None = None          # Databricks catalog / Snowflake database
    schema_name: str | None = None      # Schema or dataset name
    database: str | None = None         # Snowflake database / DuckDB path
    warehouse: str | None = None        # Snowflake warehouse / Databricks SQL Warehouse ID
    project: str | None = None          # BigQuery GCP project ID
    dataset: str | None = None          # BigQuery dataset ID
    stage_or_volume: str | None = None  # UC Volume or Snowflake Stage name
    create_views: bool = True           # Whether to create analytical views
    verify_counts: bool = True          # Verify row counts against _manifest.json
    extra_params: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.data_dir = Path(self.data_dir)
        if not self.data_dir.exists():
            raise FileNotFoundError(f"Data directory does not exist: {self.data_dir}")

    @property
    def parquet_files(self) -> list[Path]:
        """Return list of .parquet files in data_dir, excluding hidden files."""
        return sorted([p for p in self.data_dir.glob("*.parquet") if not p.name.startswith(".")])

    @property
    def manifest(self) -> dict[str, Any] | None:
        """Load _manifest.json if present."""
        manifest_path = self.data_dir / "_manifest.json"
        if manifest_path.exists():
            with open(manifest_path) as f:
                return json.load(f)
        return None


@dataclass
class ExportResult:
    """Standardized result returned by all warehouse exporters."""

    target: str
    tables_exported: list[str]
    total_rows: int
    views_created: list[str]
    duration_seconds: float
    destination: str
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseExporter(ABC):
    """Abstract base class for all target warehouse exporters."""

    def __init__(self, config: ExportConfig) -> None:
        self.config = config

    @abstractmethod
    def validate_prerequisites(self) -> None:
        """Check for required dependencies, client configurations, and credentials."""
        pass

    @abstractmethod
    def stage_files(self) -> Any:
        """Upload local Parquet files to target staging area (Volume/Stage/Bucket)."""
        pass

    @abstractmethod
    def create_tables(self) -> list[str]:
        """Create target tables and bulk ingest staged Parquet files."""
        pass

    @abstractmethod
    def create_views(self) -> list[str]:
        """Create standard analytical views (e.g. v_omnichannel_sales, v_customer_360)."""
        pass

    @abstractmethod
    def verify_manifest(self) -> bool:
        """Verify row counts in warehouse match _manifest.json."""
        pass

    @abstractmethod
    def export(self) -> ExportResult:
        """Run the full end-to-end export pipeline."""
        pass

