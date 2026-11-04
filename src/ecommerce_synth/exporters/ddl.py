"""Universal DDL compiler for Databricks, Snowflake, and BigQuery.

Reads config/schema.json and generates target-native table schemas,
column descriptions, primary key, and foreign key constraints.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


class DDLGenerator:
    """Compiles config/schema.json into native SQL DDL for various warehouse engines."""

    def __init__(self, schema_path: Path | str | None = None) -> None:
        if schema_path is None:
            # Default to repo root config/schema.json
            repo_root = Path(__file__).resolve().parent.parent.parent.parent
            schema_path = repo_root / "config" / "schema.json"
        
        self.schema_path = Path(schema_path)
        if not self.schema_path.exists():
            raise FileNotFoundError(f"Schema definition not found at: {self.schema_path}")
        
        with open(self.schema_path) as f:
            self.schema_data: dict[str, Any] = json.load(f)
        
        self.tables: dict[str, Any] = self.schema_data.get("tables", {})

    def get_column_type(self, raw_type: str, dialect: str) -> str:
        """Map logical schema type to target warehouse SQL type."""
        d = dialect.lower()
        t = raw_type.lower()

        if "string" in t or "uuid" in t:
            return "STRING" if d in ("databricks", "bigquery") else "VARCHAR"
        elif "integer" in t:
            return "INT64" if d == "bigquery" else "INT"
        elif "bigint" in t:
            return "INT64" if d == "bigquery" else "BIGINT"
        elif "float" in t or "double" in t:
            return "FLOAT64" if d == "bigquery" else "DOUBLE" if d == "databricks" else "FLOAT"
        elif "bool" in t:
            return "BOOL" if d == "bigquery" else "BOOLEAN"
        elif "date" in t:
            return "DATE"
        elif "timestamp" in t:
            return "TIMESTAMP" if d in ("databricks", "bigquery") else "TIMESTAMP_NTZ"
        elif "json" in t:
            return "JSON" if d == "bigquery" else "VARIANT" if d == "snowflake" else "STRING"
        
        return "STRING"

    def parse_foreign_key(self, fk_val: str) -> tuple[str, str] | None:
        """Parse foreign key reference like 'customers.customer_id (nullable)'.
        
        Returns (target_table, target_column) or None if polymorphic ('or').
        """
        if " or " in fk_val:
            # Polymorphic relationship cannot be a standard hard foreign key
            return None
        
        match = re.match(r"^([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)", fk_val.strip())
        if match:
            return match.group(1), match.group(2)
        return None

    def generate_create_table_sql(
        self,
        table_name: str,
        dialect: str,
        catalog_or_project: str,
        schema_or_dataset: str,
    ) -> str:
        """Generate CREATE TABLE DDL with columns, types, nullability, and primary key."""
        table_meta = self.tables.get(table_name)
        if not table_meta:
            raise KeyError(f"Table '{table_name}' not defined in schema.json")

        d = dialect.lower()
        cols_meta = table_meta.get("columns", {})
        pk_col = table_meta.get("primary_key")
        table_desc = table_meta.get("description", "").replace("'", "''")

        col_defs: list[str] = []
        for col_name, cinfo in cols_meta.items():
            ctype = self.get_column_type(cinfo.get("type", "string"), d)
            nullable = cinfo.get("nullable", True)
            null_clause = "" if nullable else " NOT NULL"
            cdesc = cinfo.get("description", "").replace("'", "''")

            if d == "databricks":
                col_defs.append(f"  {col_name} {ctype}{null_clause} COMMENT '{cdesc}'")
            elif d == "snowflake":
                col_defs.append(f"  {col_name} {ctype}{null_clause} COMMENT '{cdesc}'")
            elif d == "bigquery":
                col_defs.append(f"  `{col_name}` {ctype}{null_clause} OPTIONS(description='{cdesc}')")

        # Primary key constraint clause inside CREATE TABLE
        if pk_col:
            if d == "databricks":
                col_defs.append(f"  CONSTRAINT {table_name}_pk PRIMARY KEY ({pk_col})")
            elif d == "snowflake":
                col_defs.append(f"  CONSTRAINT {table_name}_pk PRIMARY KEY ({pk_col})")
            elif d == "bigquery":
                col_defs.append(f"  PRIMARY KEY (`{pk_col}`) NOT ENFORCED")

        cols_body = ",\n".join(col_defs)

        if d == "databricks":
            qual = f"{catalog_or_project}.{schema_or_dataset}.{table_name}"
            return (
                f"CREATE TABLE IF NOT EXISTS {qual} (\n"
                f"{cols_body}\n"
                f")\n"
                f"COMMENT '{table_desc}';"
            )
        elif d == "snowflake":
            qual = f"{catalog_or_project}.{schema_or_dataset}.{table_name}"
            return (
                f"CREATE TABLE IF NOT EXISTS {qual} (\n"
                f"{cols_body}\n"
                f")\n"
                f"COMMENT = '{table_desc}';"
            )
        elif d == "bigquery":
            qual = f"{catalog_or_project}.{schema_or_dataset}.{table_name}"
            return (
                f"CREATE TABLE IF NOT EXISTS `{qual}` (\n"
                f"{cols_body}\n"
                f")\n"
                f"OPTIONS(description='{table_desc}');"
            )
        else:
            raise ValueError(f"Unsupported dialect: {dialect}")

    def generate_foreign_keys_sql(
        self,
        table_name: str,
        dialect: str,
        catalog_or_project: str,
        schema_or_dataset: str,
    ) -> list[str]:
        """Generate ALTER TABLE ADD CONSTRAINT statements for valid foreign keys."""
        table_meta = self.tables.get(table_name)
        if not table_meta:
            return []

        d = dialect.lower()
        fks_meta = table_meta.get("foreign_keys", {})
        statements: list[str] = []

        for fk_col, fk_ref in fks_meta.items():
            parsed = self.parse_foreign_key(fk_ref)
            if not parsed:
                continue
            
            target_table, target_col = parsed
            fk_name = f"fk_{table_name}_{fk_col}_{target_table}"

            if d in ("databricks", "snowflake"):
                src_qual = f"{catalog_or_project}.{schema_or_dataset}.{table_name}"
                ref_qual = f"{catalog_or_project}.{schema_or_dataset}.{target_table}"
                statements.append(
                    f"ALTER TABLE {src_qual} ADD CONSTRAINT {fk_name} "
                    f"FOREIGN KEY ({fk_col}) REFERENCES {ref_qual} ({target_col});"
                )
            elif d == "bigquery":
                src_qual = f"{catalog_or_project}.{schema_or_dataset}.{table_name}"
                ref_qual = f"{catalog_or_project}.{schema_or_dataset}.{target_table}"
                statements.append(
                    f"ALTER TABLE `{src_qual}` ADD CONSTRAINT `{fk_name}` "
                    f"FOREIGN KEY (`{fk_col}`) REFERENCES `{ref_qual}` (`{target_col}`) NOT ENFORCED;"
                )

        return statements

    def generate_databricks_ctas_sql(
        self,
        table_name: str,
        catalog: str,
        schema: str,
        volume: str,
    ) -> str:
        """Generate Databricks Delta CTAS from UC Volume Parquet file."""
        qual = f"{catalog}.{schema}.{table_name}"
        vol_path = f"/Volumes/{catalog}/{schema}/{volume}/{table_name}.parquet"
        return f"CREATE OR REPLACE TABLE {qual} USING DELTA AS SELECT * FROM read_files('{vol_path}');"

    def generate_snowflake_copy_sql(
        self,
        table_name: str,
        database: str,
        schema: str,
        stage: str,
    ) -> str:
        """Generate Snowflake COPY INTO table from internal/external stage."""
        qual = f"{database}.{schema}.{table_name}"
        return (
            f"COPY INTO {qual} FROM @{stage}/{table_name}.parquet "
            f"FILE_FORMAT = (TYPE = PARQUET) MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE;"
        )
