# Multi-Warehouse Exporter Framework (Databricks + Snowflake + BigQuery) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an extensible multi-warehouse exporter framework for `ecommerce-synth` that automates staging and native bulk-loading of all 19 synthetic tables and analytical views into Databricks (Unity Catalog), Snowflake, and Google Cloud BigQuery, while preserving the existing DuckDB export.

**Architecture:** A pluggable Two-Stage Staging + Bulk Load pattern (`BaseExporter`) driven by `config/schema.json` as the single source of truth for schema DDL, primary/foreign key constraints, and column comments. Staging uses target-native mechanisms (Databricks UC Volumes, Snowflake Stages, BigQuery Load/GCS), followed by native pushdown ingestion (`read_files`/Delta, `COPY INTO`, BigQuery Load Jobs) and automated row-count manifest verification.

**Tech Stack:** Python 3.11+, Polars, PyArrow, DuckDB, Typer, Rich; optional cloud SDKs (`databricks-sdk`, `databricks-sql-connector`, `snowflake-connector-python`, `google-cloud-bigquery`).

**Spec:** Two-stage decoupled architecture specification approved in discussion, compiling `config/schema.json` to native warehouse dialects.

## Global Constraints

- **Non-destructive & Backward Compatible:** Existing `generate --duckdb`, `export-duckdb`, and all 23 existing unit tests must remain 100% passing.
- **Lazy Cloud SDK Imports:** Core `ecommerce-synth` installation must not require Databricks, Snowflake, or BigQuery SDKs to be installed; cloud connectors must be optional extras and fail with clear, friendly installation instructions if missing.
- **100% Schema & Constraint Fidelity:** All 19 tables, column descriptions, and 29 primary/foreign key constraints must be translated accurately to each warehouse's native constraint syntax (`NOT ENFORCED` where appropriate).
- **Unit Test Coverage Without Live Credentials:** All exporter logic, DDL generation, staging commands, and error handling must be fully unit-tested with mocked clients so tests pass offline in any CI environment.

## Review Focus

1. **Missing Optional SDKs:** User runs `ecommerce-synth export <dir> --target databricks` without `databricks-sdk` installed; must display a friendly Rich prompt showing the exact `pip install 'ecommerce-synth[databricks]'` command instead of a raw traceback.
2. **Schema & Identifier Case Sensitivity:** Snowflake defaults to uppercase identifiers unless quoted, whereas Databricks and BigQuery are lowercase/case-preserving; DDL and column mappings must align without case mismatch.
3. **Data Type Translation Fidelity:** JSON columns (`metadata`, `details`), UUIDs, and Date/Timestamps must map cleanly into Databricks (`STRING`/`VARIANT`), Snowflake (`VARIANT`/`VARCHAR`), and BigQuery (`JSON`/`STRING`/`TIMESTAMP`).
4. **Volume/Stage Path Sanitization:** Trailing slashes or mismatched relative paths in Volume or Stage paths must not produce broken SQL syntax.
5. **Partial Failure & Cleanup:** If a table upload fails halfway through the 19 tables, the error must report the failing table and allow retrying without corrupting the target schema.

---

### Task 1: Core Exporter Base, Universal DDL & View Compiler

**Files:**
- Create: `src/ecommerce_synth/exporters/__init__.py`
- Create: `src/ecommerce_synth/exporters/base.py`
- Create: `src/ecommerce_synth/exporters/ddl.py`
- Create: `src/ecommerce_synth/exporters/views.py`
- Test: `tests/test_exporters_ddl.py`

- [ ] Define `ExportConfig`, `ExportResult`, and abstract `BaseExporter` in `src/ecommerce_synth/exporters/base.py`.
- [ ] Implement `DDLGenerator` in `src/ecommerce_synth/exporters/ddl.py` reading `config/schema.json`:
  - Type mapping for Databricks, Snowflake, BigQuery.
  - Primary key & foreign key constraint DDL generation (`ADD CONSTRAINT ... PRIMARY KEY ...`, `FOREIGN KEY ... REFERENCES ...`).
  - Column and table comment generation.
- [ ] Implement `ViewGenerator` in `src/ecommerce_synth/exporters/views.py` providing dialect-specific SQL for `v_omnichannel_sales` and `v_customer_360`.
- [ ] Write unit tests in `tests/test_exporters_ddl.py` verifying DDL and view SQL generated for all 19 tables across Databricks, Snowflake, and BigQuery.
- [ ] Run pytest to verify all tests pass.

---

### Task 2: Refactor DuckDB Exporter into Framework

**Files:**
- Create: `src/ecommerce_synth/exporters/duckdb.py`
- Modify: `src/ecommerce_synth/duckdb_exporter.py`
- Test: `tests/test_duckdb_and_profiler.py`

- [ ] Implement `DuckDBExporter(BaseExporter)` in `src/ecommerce_synth/exporters/duckdb.py`.
- [ ] Update `src/ecommerce_synth/duckdb_exporter.py` to delegate to `DuckDBExporter` ensuring 100% backward compatibility for existing code.
- [ ] Run existing `tests/test_duckdb_and_profiler.py` to confirm zero regression.

---

### Task 3: Databricks Unity Catalog Exporter

**Files:**
- Create: `src/ecommerce_synth/exporters/databricks.py`
- Test: `tests/test_databricks_exporter.py`

- [ ] Implement `DatabricksExporter(BaseExporter)` in `src/ecommerce_synth/exporters/databricks.py`:
  - Auth resolution: `~/.databrickscfg` profile or `DATABRICKS_HOST` / `DATABRICKS_TOKEN`.
  - Target initialization: `CREATE SCHEMA IF NOT EXISTS <catalog>.<schema>;` and `CREATE VOLUME IF NOT EXISTS <catalog>.<schema>.<volume>;`.
  - Automated staging: Upload Parquet files to `/Volumes/<catalog>/<schema>/<volume>/<file>.parquet` via `WorkspaceClient.files.upload`.
  - Bulk loading: Execute Delta CTAS using `read_files('/Volumes/...')` on SQL Warehouse, apply PK/FK constraints and table/column comments.
  - Create analytical views and verify row counts against `_manifest.json`.
  - Graceful ImportError handling if `databricks-sdk` or `databricks-sql-connector` is missing.
- [ ] Write unit tests in `tests/test_databricks_exporter.py` mocking `WorkspaceClient` and SQL execution.
- [ ] Run pytest to verify all tests pass.

---

### Task 4: Snowflake Exporter

**Files:**
- Create: `src/ecommerce_synth/exporters/snowflake.py`
- Test: `tests/test_snowflake_exporter.py`

- [ ] Implement `SnowflakeExporter(BaseExporter)` in `src/ecommerce_synth/exporters/snowflake.py`:
  - Auth resolution: `~/.snowflake/config.toml` connection or `SNOWFLAKE_*` env vars.
  - Target initialization: `CREATE SCHEMA IF NOT EXISTS <db>.<schema>;` and `CREATE STAGE IF NOT EXISTS <db>.<schema>.<stage>;`.
  - Automated staging: `PUT file://... @stage/` with parallel file upload.
  - Bulk loading: `CREATE TABLE IF NOT EXISTS`, followed by `COPY INTO <db>.<schema>.<table> FROM @stage/<table>.parquet FILE_FORMAT=(TYPE=PARQUET) MATCH_BY_COLUMN_NAME=CASE_INSENSITIVE`.
  - Apply table/column comments and PK/FK constraints.
  - Create analytical views and verify row counts against `_manifest.json`.
  - Graceful ImportError handling if `snowflake-connector-python` is missing.
- [ ] Write unit tests in `tests/test_snowflake_exporter.py` mocking Snowflake connection and cursor.
- [ ] Run pytest to verify all tests pass.

---

### Task 5: Google Cloud BigQuery Exporter

**Files:**
- Create: `src/ecommerce_synth/exporters/bigquery.py`
- Test: `tests/test_bigquery_exporter.py`

- [ ] Implement `BigQueryExporter(BaseExporter)` in `src/ecommerce_synth/exporters/bigquery.py`:
  - Auth resolution: Google Application Default Credentials (ADC) or `GOOGLE_APPLICATION_CREDENTIALS`.
  - Target initialization: `client.create_dataset(dataset_id, exists_ok=True)`.
  - Automated staging & loading: Direct `client.load_table_from_file(...)` with `source_format=PARQUET` (or GCS URI if `--gcs-bucket` provided).
  - Apply field descriptions from `config/schema.json` and Primary/Foreign key constraints via BigQuery DDL.
  - Create analytical views and verify row counts against `_manifest.json`.
  - Graceful ImportError handling if `google-cloud-bigquery` is missing.
- [ ] Write unit tests in `tests/test_bigquery_exporter.py` mocking BigQuery client and LoadJob.
- [ ] Run pytest to verify all tests pass.

---

### Task 6: CLI Integration & Optional Dependencies Packaging

**Files:**
- Modify: `pyproject.toml`
- Modify: `src/ecommerce_synth/cli.py`
- Test: `tests/test_cli_export.py`

- [ ] Add optional dependency extras in `pyproject.toml`:
  - `databricks = ["databricks-sdk>=0.20.0", "databricks-sql-connector>=3.0.0"]`
  - `snowflake = ["snowflake-connector-python>=3.0.0"]`
  - `bigquery = ["google-cloud-bigquery>=3.0.0", "google-cloud-storage>=2.0.0"]`
  - `all-targets = ["ecommerce-synth[databricks,snowflake,bigquery]"]`
- [ ] Add `ecommerce-synth export` command in `src/ecommerce_synth/cli.py`:
  - Support `--target [duckdb|databricks|snowflake|bigquery]`
  - Pass target-specific options (catalog, schema, database, warehouse, project, dataset, stage, volume).
- [ ] Update `ecommerce-synth generate` to support `--export-target` or `--databricks`, `--snowflake`, `--bigquery` shortcuts.
- [ ] Write unit tests in `tests/test_cli_export.py` testing CLI dispatch and parameter parsing.
- [ ] Run pytest on the full test suite.

---

### Task 7: End-to-End Documentation, Skill Playbook & Final Verification

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `.agents/skills/ecommerce-synthetic/SKILL.md`

- [ ] Update `README.md` with multi-warehouse export guides for Databricks, Snowflake, and BigQuery.
- [ ] Update `AGENTS.md` and `.agents/skills/ecommerce-synthetic/SKILL.md` with CLI recipes and connection setup instructions.
- [ ] Run full test suite across all 23 existing tests + new unit tests.
- [ ] Commit all changes to git.
