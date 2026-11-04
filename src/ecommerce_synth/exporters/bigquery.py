"""Google Cloud BigQuery warehouse exporter implementation."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

from rich.console import Console

from .base import BaseExporter, ExportConfig, ExportResult
from .ddl import DDLGenerator
from .views import ViewGenerator

console = Console()


class BigQueryExporter(BaseExporter):
    """Exports synthetic datasets to Google Cloud BigQuery native tables."""

    def __init__(self, config: ExportConfig) -> None:
        super().__init__(config)
        self.project = config.project or config.catalog or os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT")
        self.dataset = config.dataset or config.schema_name
        self.gcs_bucket = config.stage_or_volume or config.extra_params.get("gcs_bucket")
        self.location = config.extra_params.get("location", "US")
        self.ddl_gen = DDLGenerator()
        self._client: Any = None

    def validate_prerequisites(self) -> None:
        """Check for google-cloud-bigquery and required target parameters."""
        try:
            import google.cloud.bigquery  # noqa: F401
        except ImportError:
            raise ImportError(
                "Google Cloud BigQuery library is required for BigQuery export. "
                "Install it using: pip install 'ecommerce-synth[bigquery]'"
            )

        if not self.project:
            raise ValueError(
                "GCP project ID is required for BigQuery export. Specify via --project <gcp_project_id>."
            )
        if not self.dataset:
            raise ValueError(
                "BigQuery dataset ID is required. Specify via --dataset <dataset_name>."
            )

    def _get_client(self) -> Any:
        """Lazy-initialize and return BigQuery client."""
        if self._client is None:
            from google.cloud import bigquery
            self._client = bigquery.Client(project=self.project, location=self.location)
        return self._client

    def stage_files(self) -> list[str]:
        """Upload to GCS if bucket is configured; otherwise direct load is used."""
        if not self.gcs_bucket:
            return []

        try:
            from google.cloud import storage
        except ImportError:
            raise ImportError(
                "Google Cloud Storage library is required for GCS staging. "
                "Install it using: pip install 'ecommerce-synth[bigquery]'"
            )

        storage_client = storage.Client(project=self.project)
        bucket = storage_client.bucket(self.gcs_bucket)
        staged_uris: list[str] = []

        console.print(f"\n📦 [bold cyan]Staging files to GCS:[/bold cyan] gs://{self.gcs_bucket}/{self.dataset}/")

        for pf in self.config.parquet_files:
            blob = bucket.blob(f"{self.dataset}/{pf.name}")
            blob.upload_from_filename(str(pf.resolve()))
            uri = f"gs://{self.gcs_bucket}/{self.dataset}/{pf.name}"
            staged_uris.append(uri)
            console.print(f"  ✓ Staged [green]{pf.name}[/green]")

        return staged_uris

    def create_tables(self) -> list[str]:
        """Load Parquet files into BigQuery native tables and apply descriptions & constraints."""
        from google.cloud import bigquery

        client = self._get_client()
        dataset_ref = bigquery.DatasetReference(self.project, self.dataset)
        loaded_tables: list[str] = []

        console.print(f"\n⚡ [bold cyan]Loading tables into BigQuery:[/bold cyan] {self.project}.{self.dataset}")

        for pf in self.config.parquet_files:
            table_name = pf.stem
            table_ref = dataset_ref.table(table_name)
            table_meta = self.ddl_gen.tables.get(table_name, {})

            job_config = bigquery.LoadJobConfig(
                source_format=bigquery.SourceFormat.PARQUET,
                write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
            )

            # 1. Load data
            if self.gcs_bucket:
                uri = f"gs://{self.gcs_bucket}/{self.dataset}/{pf.name}"
                load_job = client.load_table_from_uri(uri, table_ref, job_config=job_config)
            else:
                with open(pf, "rb") as source_file:
                    load_job = client.load_table_from_file(source_file, table_ref, job_config=job_config)

            load_job.result()  # Wait for job to complete

            # 2. Enrich table description
            table = client.get_table(table_ref)
            table_desc = table_meta.get("description")
            if table_desc:
                table.description = table_desc
                client.update_table(table, ["description"])

            # 3. Add primary key constraint
            pk_col = table_meta.get("primary_key")
            if pk_col:
                pk_sql = (
                    f"ALTER TABLE `{self.project}.{self.dataset}.{table_name}` "
                    f"ADD PRIMARY KEY (`{pk_col}`) NOT ENFORCED;"
                )
                try:
                    client.query(pk_sql).result()
                except Exception:
                    pass

            loaded_tables.append(table_name)
            console.print(f"  ✓ Loaded table [green]{self.project}.{self.dataset}.{table_name}[/green]")

        # 4. Apply Foreign Key constraints
        for pf in self.config.parquet_files:
            table_name = pf.stem
            fk_sqls = self.ddl_gen.generate_foreign_keys_sql(
                table_name=table_name,
                dialect="bigquery",
                catalog_or_project=self.project,  # type: ignore[arg-type]
                schema_or_dataset=self.dataset,  # type: ignore[arg-type]
            )
            for fk_sql in fk_sqls:
                try:
                    client.query(fk_sql).result()
                except Exception:
                    pass

        return loaded_tables

    def create_views(self) -> list[str]:
        """Create analytical views in BigQuery."""
        created_views: list[str] = []
        if not self.config.create_views:
            return created_views

        client = self._get_client()
        console.print(f"\n👁️  [bold cyan]Creating analytical views in:[/bold cyan] {self.project}.{self.dataset}")

        for vname, vsql in ViewGenerator.get_all_views("bigquery", self.project, self.dataset):
            try:
                client.query(vsql).result()
                created_views.append(vname)
                console.print(f"  ✓ View created [green]{self.project}.{self.dataset}.{vname}[/green]")
            except Exception as e:
                console.print(f"  ⚠️ Could not create view {vname}: {e}")

        return created_views

    def verify_manifest(self) -> bool:
        """Verify row counts match _manifest.json if present."""
        if not self.config.verify_counts or not self.config.manifest:
            return True

        client = self._get_client()
        row_counts = self.config.manifest.get("row_counts", {})
        console.print(f"\n🔍 [bold cyan]Verifying row counts against manifest...[/bold cyan]")

        all_matched = True
        for tbl, expected in row_counts.items():
            try:
                query = f"SELECT COUNT(*) as cnt FROM `{self.project}.{self.dataset}.{tbl}`;"
                query_job = client.query(query)
                rows = list(query_job.result())
                if rows:
                    actual = int(rows[0].cnt)
                    if actual == expected:
                        console.print(f"  ✓ [green]{tbl}[/green]: {actual:,} rows (matches manifest)")
                    else:
                        console.print(f"  ⚠️ [yellow]{tbl}[/yellow]: expected {expected:,}, got {actual:,}")
                        all_matched = False
            except Exception:
                pass

        return all_matched

    def export(self) -> ExportResult:
        """Execute the end-to-end BigQuery export."""
        self.validate_prerequisites()
        from google.cloud import bigquery

        start_time = time.time()

        console.print(
            f"\n⚡ [bold cyan]Exporting to BigQuery:[/bold cyan] "
            f"{self.project}.{self.dataset}"
        )

        client = self._get_client()

        # 1. Initialize dataset
        dataset_ref = bigquery.DatasetReference(self.project, self.dataset)
        dataset = bigquery.Dataset(dataset_ref)
        dataset.location = self.location
        client.create_dataset(dataset, exists_ok=True)

        # 2. Stage files (if GCS configured)
        if self.gcs_bucket:
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
            f"\n[bold green]✓ BigQuery export complete![/bold green] "
            f"{len(loaded_tables)} tables in {elapsed:.1f}s"
        )

        return ExportResult(
            target="bigquery",
            tables_exported=loaded_tables,
            total_rows=total_rows,
            views_created=created_views,
            duration_seconds=round(elapsed, 2),
            destination=f"{self.project}.{self.dataset}",
            metadata={"location": self.location, "gcs_bucket": self.gcs_bucket},
        )
