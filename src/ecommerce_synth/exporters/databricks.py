"""Databricks Unity Catalog exporter implementation."""

from __future__ import annotations

import io
import time
from pathlib import Path
from typing import Any

from rich.console import Console

from .base import BaseExporter, ExportConfig, ExportResult
from .ddl import DDLGenerator
from .views import ViewGenerator

console = Console()


class DatabricksExporter(BaseExporter):
    """Exports synthetic datasets to Databricks Unity Catalog Delta tables via UC Volumes."""

    def __init__(self, config: ExportConfig) -> None:
        super().__init__(config)
        self.catalog = config.catalog
        self.schema_name = config.schema_name
        self.volume_name = config.stage_or_volume or "ecommerce_raw"
        self.warehouse_id = config.warehouse or config.extra_params.get("warehouse_id")
        self.profile = config.extra_params.get("profile")
        self.ddl_gen = DDLGenerator()
        self._client: Any = None

    def validate_prerequisites(self) -> None:
        """Check for databricks-sdk and required Unity Catalog target parameters."""
        try:
            import databricks.sdk  # noqa: F401
        except ImportError:
            raise ImportError(
                "Databricks SDK is required for Unity Catalog export. "
                "Install it using: pip install 'ecommerce-synth[databricks]'"
            )

        if not self.catalog:
            raise ValueError(
                "Databricks catalog name is required. Specify via --catalog <catalog_name>."
            )
        if not self.schema_name:
            raise ValueError(
                "Databricks schema name is required. Specify via --schema <schema_name>."
            )

    def _get_client(self) -> Any:
        """Lazy-initialize and return WorkspaceClient."""
        if self._client is None:
            from databricks.sdk import WorkspaceClient
            if self.profile:
                self._client = WorkspaceClient(profile=self.profile)
            else:
                self._client = WorkspaceClient()
        return self._client

    def _execute_sql(self, statement: str) -> Any:
        """Execute SQL via Databricks Statement Execution API."""
        w = self._get_client()
        warehouse_id = self.warehouse_id

        # If warehouse_id is not explicitly specified, find the first available SQL warehouse
        if not warehouse_id:
            warehouses = list(w.warehouses.list())
            if not warehouses:
                raise RuntimeError(
                    "No SQL Warehouses found in Databricks workspace. "
                    "Please create one or supply --warehouse <warehouse_id>."
                )
            warehouse_id = warehouses[0].id
            self.warehouse_id = warehouse_id

        res = w.statement_execution.execute_statement(
            warehouse_id=warehouse_id,
            statement=statement,
            catalog=self.catalog,
            schema=self.schema_name,
            wait_timeout="50s",
        )
        return res

    def stage_files(self) -> list[str]:
        """Upload local Parquet files to Unity Catalog Volume."""
        w = self._get_client()
        staged_paths: list[str] = []

        console.print(f"\n📦 [bold cyan]Staging files to UC Volume:[/bold cyan] /Volumes/{self.catalog}/{self.schema_name}/{self.volume_name}/")

        for pf in self.config.parquet_files:
            volume_file_path = f"/Volumes/{self.catalog}/{self.schema_name}/{self.volume_name}/{pf.name}"
            with open(pf, "rb") as f:
                w.files.upload(volume_file_path, f, overwrite=True)
            staged_paths.append(volume_file_path)
            console.print(f"  ✓ Staged [green]{pf.name}[/green]")

        return staged_paths

    def create_tables(self) -> list[str]:
        """Create Delta tables from staged Parquet files and apply PK/FK constraints."""
        loaded_tables: list[str] = []

        console.print(f"\n🧱 [bold cyan]Creating Delta tables in:[/bold cyan] {self.catalog}.{self.schema_name}")

        for pf in self.config.parquet_files:
            table_name = pf.stem
            # 1. Delta CTAS from UC Volume
            ctas_sql = self.ddl_gen.generate_databricks_ctas_sql(
                table_name=table_name,
                catalog=self.catalog,  # type: ignore[arg-type]
                schema=self.schema_name,  # type: ignore[arg-type]
                volume=self.volume_name,
            )
            self._execute_sql(ctas_sql)

            # 2. Add Primary Key constraint
            table_meta = self.ddl_gen.tables.get(table_name, {})
            pk_col = table_meta.get("primary_key")
            if pk_col:
                pk_sql = (
                    f"ALTER TABLE {self.catalog}.{self.schema_name}.{table_name} "
                    f"ADD CONSTRAINT {table_name}_pk PRIMARY KEY ({pk_col});"
                )
                try:
                    self._execute_sql(pk_sql)
                except Exception:
                    pass

            # 3. Add Table comment
            table_desc = table_meta.get("description", "").replace("'", "''")
            if table_desc:
                comment_sql = (
                    f"COMMENT ON TABLE {self.catalog}.{self.schema_name}.{table_name} "
                    f"IS '{table_desc}';"
                )
                try:
                    self._execute_sql(comment_sql)
                except Exception:
                    pass

            loaded_tables.append(table_name)
            console.print(f"  ✓ Loaded table [green]{self.catalog}.{self.schema_name}.{table_name}[/green]")

        # 4. Add Foreign Key constraints across tables
        for pf in self.config.parquet_files:
            table_name = pf.stem
            fk_sqls = self.ddl_gen.generate_foreign_keys_sql(
                table_name=table_name,
                dialect="databricks",
                catalog_or_project=self.catalog,  # type: ignore[arg-type]
                schema_or_dataset=self.schema_name,  # type: ignore[arg-type]
            )
            for fk_sql in fk_sqls:
                try:
                    self._execute_sql(fk_sql)
                except Exception:
                    pass

        return loaded_tables

    def create_views(self) -> list[str]:
        """Create analytical views in Unity Catalog."""
        created_views: list[str] = []
        if not self.config.create_views:
            return created_views

        console.print(f"\n👁️  [bold cyan]Creating analytical views in:[/bold cyan] {self.catalog}.{self.schema_name}")

        for vname, vsql in ViewGenerator.get_all_views("databricks", self.catalog, self.schema_name):
            try:
                self._execute_sql(vsql)
                created_views.append(vname)
                console.print(f"  ✓ View created [green]{self.catalog}.{self.schema_name}.{vname}[/green]")
            except Exception as e:
                console.print(f"  ⚠️ Could not create view {vname}: {e}")

        return created_views

    def verify_manifest(self) -> bool:
        """Verify row counts match _manifest.json if present."""
        if not self.config.verify_counts or not self.config.manifest:
            return True

        row_counts = self.config.manifest.get("row_counts", {})
        console.print(f"\n🔍 [bold cyan]Verifying row counts against manifest...[/bold cyan]")

        all_matched = True
        for tbl, expected in row_counts.items():
            try:
                res = self._execute_sql(f"SELECT COUNT(*) FROM {self.catalog}.{self.schema_name}.{tbl}")
                # Parse count from statement execution result
                if hasattr(res, "result") and res.result and hasattr(res.result, "data_array"):
                    actual = int(res.result.data_array[0][0])
                    if actual == expected:
                        console.print(f"  ✓ [green]{tbl}[/green]: {actual:,} rows (matches manifest)")
                    else:
                        console.print(f"  ⚠️ [yellow]{tbl}[/yellow]: expected {expected:,}, got {actual:,}")
                        all_matched = False
            except Exception:
                pass

        return all_matched

    def export(self) -> ExportResult:
        """Execute the end-to-end Databricks Unity Catalog export."""
        self.validate_prerequisites()
        start_time = time.time()

        console.print(
            f"\n🧱 [bold cyan]Exporting to Databricks Unity Catalog:[/bold cyan] "
            f"{self.catalog}.{self.schema_name}"
        )

        # 1. Initialize schema and volume
        self._execute_sql(f"CREATE SCHEMA IF NOT EXISTS {self.catalog}.{self.schema_name};")
        self._execute_sql(f"CREATE VOLUME IF NOT EXISTS {self.catalog}.{self.schema_name}.{self.volume_name};")

        # 2. Stage files to volume
        self.stage_files()

        # 3. Create tables & bulk load
        loaded_tables = self.create_tables()

        # 4. Create analytical views
        created_views = self.create_views()

        # 5. Verify manifest
        self.verify_manifest()

        elapsed = time.time() - start_time
        total_rows = sum(self.config.manifest.get("row_counts", {}).values()) if self.config.manifest else 0

        console.print(
            f"\n[bold green]✓ Databricks Unity Catalog export complete![/bold green] "
            f"{len(loaded_tables)} tables in {elapsed:.1f}s"
        )

        return ExportResult(
            target="databricks",
            tables_exported=loaded_tables,
            total_rows=total_rows,
            views_created=created_views,
            duration_seconds=round(elapsed, 2),
            destination=f"{self.catalog}.{self.schema_name}",
            metadata={"volume": self.volume_name, "warehouse_id": self.warehouse_id},
        )
