"""Snowflake warehouse exporter implementation."""

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


class SnowflakeExporter(BaseExporter):
    """Exports synthetic datasets to Snowflake native tables via internal staging."""

    def __init__(self, config: ExportConfig) -> None:
        super().__init__(config)
        self.database = config.database or config.catalog
        self.schema_name = config.schema_name
        self.warehouse = config.warehouse or os.getenv("SNOWFLAKE_WAREHOUSE")
        self.stage_name = config.stage_or_volume or "ecommerce_stage"
        self.connection_name = config.extra_params.get("connection") or config.extra_params.get("profile")
        self.ddl_gen = DDLGenerator()
        self._conn: Any = None

    def _discover_connection_name(self) -> str | None:
        """Find default or available connection name from ~/.snowflake/connections.toml or config.toml."""
        if self.connection_name:
            return self.connection_name

        try:
            from snowflake.connector.config_manager import CONFIG_MANAGER
            conns = CONFIG_MANAGER.get("connections", {})
            if not conns:
                return None
            conn_keys = list(conns.keys())
            if "default" in conn_keys:
                return "default"
            if "defautlt" in conn_keys:  # common typo fallback
                return "defautlt"
            if len(conn_keys) == 1:
                return conn_keys[0]
        except Exception:
            pass
        return None

    def validate_prerequisites(self) -> None:
        """Check for snowflake-connector-python and required target parameters."""
        try:
            import snowflake.connector  # noqa: F401
        except ImportError:
            raise ImportError(
                "Snowflake connector is required for Snowflake export. "
                "Install it using: pip install 'ecommerce-synth[snowflake]'"
            )

        if not self.database:
            raise ValueError(
                "Snowflake database name is required. Specify via --database <database_name>."
            )
        if not self.schema_name:
            raise ValueError(
                "Snowflake schema name is required. Specify via --schema <schema_name>."
            )

        conn_name = self._discover_connection_name()
        has_env_auth = bool(
            self.config.extra_params.get("user")
            or os.getenv("SNOWFLAKE_USER")
            or (self.config.extra_params.get("account") and self.config.extra_params.get("password"))
        )

        if not conn_name and not has_env_auth:
            available_conns = []
            try:
                from snowflake.connector.config_manager import CONFIG_MANAGER
                available_conns = list(CONFIG_MANAGER.get("connections", {}).keys())
            except Exception:
                pass

            if available_conns:
                conn_list = ", ".join(f"'{c}'" for c in available_conns)
                raise ValueError(
                    f"Snowflake credentials not specified. Available connections in ~/.snowflake/connections.toml: "
                    f"[{conn_list}]. Specify one via --profile <name> (e.g. --profile {available_conns[0]}), "
                    f"or set SNOWFLAKE_USER and SNOWFLAKE_ACCOUNT."
                )
            else:
                raise ValueError(
                    "Snowflake credentials not found. Please provide --profile <connection_name>, "
                    "or set environment variables SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, and SNOWFLAKE_PASSWORD."
                )

    def _get_connection(self) -> Any:
        """Lazy-initialize and return Snowflake connection."""
        if self._conn is None:
            import snowflake.connector

            authenticator = self.config.extra_params.get("authenticator") or os.getenv("SNOWFLAKE_AUTHENTICATOR")
            role = self.config.extra_params.get("role") or os.getenv("SNOWFLAKE_ROLE")
            passcode = self.config.extra_params.get("passcode") or os.getenv("SNOWFLAKE_PASSCODE")
            private_key_file = self.config.extra_params.get("private_key_file") or os.getenv("SNOWFLAKE_PRIVATE_KEY_FILE")

            private_key_bytes = None
            if private_key_file and os.path.exists(private_key_file):
                from cryptography.hazmat.primitives import serialization
                with open(private_key_file, "rb") as kf:
                    p_key = serialization.load_pem_private_key(kf.read(), password=None)
                private_key_bytes = p_key.private_bytes(
                    encoding=serialization.Encoding.DER,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption(),
                )

            def _connect(kwargs: dict[str, Any]) -> Any:
                kwargs.setdefault("client_request_mfa_token", True)
                kwargs.setdefault("client_store_temporary_credential", True)
                try:
                    return snowflake.connector.connect(**kwargs)
                except Exception as e:
                    err_msg = str(e)
                    # Check for MFA / passcode requirement
                    is_mfa_error = (
                        "Internal error" in err_msg
                        or "Multi-factor authentication" in err_msg
                        or "250001" in err_msg
                    )
                    if is_mfa_error and not kwargs.get("passcode"):
                        import sys
                        if sys.stdin.isatty():
                            import getpass
                            try:
                                prompted_code = getpass.getpass("Enter Snowflake MFA 6-digit passcode (TOTP): ").strip()
                                if prompted_code:
                                    kwargs["passcode"] = prompted_code
                                    return snowflake.connector.connect(**kwargs)
                            except Exception:
                                pass
                        raise RuntimeError(
                            "Snowflake MFA passcode required. Please supply your 6-digit TOTP authenticator code "
                            "using `--passcode <code>` (e.g. `--passcode 123456`) or export `SNOWFLAKE_PASSCODE=<code>`."
                        ) from e
                    raise

            conn_name = self._discover_connection_name()
            if conn_name:
                conn_kwargs: dict[str, Any] = {
                    "connection_name": conn_name,
                    "database": self.database,
                    "schema": self.schema_name,
                }
                if self.warehouse:
                    conn_kwargs["warehouse"] = self.warehouse
                if role:
                    conn_kwargs["role"] = role
                if authenticator:
                    conn_kwargs["authenticator"] = authenticator
                if passcode:
                    conn_kwargs["passcode"] = passcode
                if private_key_bytes:
                    conn_kwargs["private_key"] = private_key_bytes
                self._conn = _connect(conn_kwargs)
            else:
                account = self.config.extra_params.get("account") or os.getenv("SNOWFLAKE_ACCOUNT")
                user = self.config.extra_params.get("user") or os.getenv("SNOWFLAKE_USER")
                password = self.config.extra_params.get("password") or os.getenv("SNOWFLAKE_PASSWORD")

                conn_kwargs = {
                    "database": self.database,
                    "schema": self.schema_name,
                }
                if account:
                    conn_kwargs["account"] = account
                if user:
                    conn_kwargs["user"] = user
                if password:
                    conn_kwargs["password"] = password
                if self.warehouse:
                    conn_kwargs["warehouse"] = self.warehouse
                if role:
                    conn_kwargs["role"] = role
                if authenticator:
                    conn_kwargs["authenticator"] = authenticator
                if passcode:
                    conn_kwargs["passcode"] = passcode
                if private_key_bytes:
                    conn_kwargs["private_key"] = private_key_bytes

                self._conn = _connect(conn_kwargs)

        return self._conn

    def _execute_sql(self, statement: str) -> list[tuple[Any, ...]]:
        """Execute SQL via Snowflake cursor."""
        conn = self._get_connection()
        with conn.cursor() as cur:
            cur.execute(statement)
            try:
                return cur.fetchall()
            except Exception:
                return []

    def stage_files(self) -> list[str]:
        """Upload local Parquet files to Snowflake stage using PUT."""
        staged_paths: list[str] = []
        stage_qual = f"{self.database}.{self.schema_name}.{self.stage_name}"

        console.print(f"\n📦 [bold cyan]Staging files to Snowflake Stage:[/bold cyan] @{stage_qual}/")

        for pf in self.config.parquet_files:
            abs_path = str(pf.resolve())
            put_sql = f"PUT file://{abs_path} @{stage_qual} AUTO_COMPRESS=FALSE OVERWRITE=TRUE;"
            self._execute_sql(put_sql)
            staged_paths.append(f"@{stage_qual}/{pf.name}")
            console.print(f"  ✓ Staged [green]{pf.name}[/green]")

        return staged_paths

    def create_tables(self) -> list[str]:
        """Create Snowflake tables, run COPY INTO, and apply PK/FK constraints."""
        loaded_tables: list[str] = []
        stage_qual = f"{self.database}.{self.schema_name}.{self.stage_name}"

        console.print(f"\n❄️  [bold cyan]Creating tables in Snowflake:[/bold cyan] {self.database}.{self.schema_name}")

        for pf in self.config.parquet_files:
            table_name = pf.stem
            # 1. Create Table DDL
            create_sql = self.ddl_gen.generate_create_table_sql(
                table_name=table_name,
                dialect="snowflake",
                catalog_or_project=self.database,  # type: ignore[arg-type]
                schema_or_dataset=self.schema_name,  # type: ignore[arg-type]
            )
            self._execute_sql(create_sql)

            # 2. Bulk load with COPY INTO
            copy_sql = (
                f"COPY INTO {self.database}.{self.schema_name}.{table_name} "
                f"FROM @{stage_qual}/{table_name}.parquet "
                f"FILE_FORMAT = (TYPE = PARQUET) MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE;"
            )
            self._execute_sql(copy_sql)
            loaded_tables.append(table_name)
            console.print(f"  ✓ Loaded table [green]{self.database}.{self.schema_name}.{table_name}[/green]")

        # 3. Apply Foreign Key constraints
        for pf in self.config.parquet_files:
            table_name = pf.stem
            fk_sqls = self.ddl_gen.generate_foreign_keys_sql(
                table_name=table_name,
                dialect="snowflake",
                catalog_or_project=self.database,  # type: ignore[arg-type]
                schema_or_dataset=self.schema_name,  # type: ignore[arg-type]
            )
            for fk_sql in fk_sqls:
                try:
                    self._execute_sql(fk_sql)
                except Exception:
                    pass

        return loaded_tables

    def create_views(self) -> list[str]:
        """Create analytical views in Snowflake."""
        created_views: list[str] = []
        if not self.config.create_views:
            return created_views

        console.print(f"\n👁️  [bold cyan]Creating analytical views in:[/bold cyan] {self.database}.{self.schema_name}")

        for vname, vsql in ViewGenerator.get_all_views("snowflake", self.database, self.schema_name):
            try:
                self._execute_sql(vsql)
                created_views.append(vname)
                console.print(f"  ✓ View created [green]{self.database}.{self.schema_name}.{vname}[/green]")
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
                res = self._execute_sql(f"SELECT COUNT(*) FROM {self.database}.{self.schema_name}.{tbl};")
                if res and len(res) > 0:
                    actual = int(res[0][0])
                    if actual == expected:
                        console.print(f"  ✓ [green]{tbl}[/green]: {actual:,} rows (matches manifest)")
                    else:
                        console.print(f"  ⚠️ [yellow]{tbl}[/yellow]: expected {expected:,}, got {actual:,}")
                        all_matched = False
            except Exception:
                pass

        return all_matched

    def export(self) -> ExportResult:
        """Execute the end-to-end Snowflake export."""
        self.validate_prerequisites()
        start_time = time.time()

        console.print(
            f"\n❄️  [bold cyan]Exporting to Snowflake:[/bold cyan] "
            f"{self.database}.{self.schema_name}"
        )

        try:
            # 1. Initialize database, schema and stage
            try:
                self._execute_sql(f"CREATE DATABASE IF NOT EXISTS {self.database};")
            except Exception:
                pass

            self._execute_sql(f"CREATE SCHEMA IF NOT EXISTS {self.database}.{self.schema_name};")
            stage_qual = f"{self.database}.{self.schema_name}.{self.stage_name}"
            self._execute_sql(f"CREATE STAGE IF NOT EXISTS {stage_qual};")

            # 2. Stage files
            self.stage_files()

            # 3. Create tables & bulk load
            loaded_tables = self.create_tables()

            # 4. Create analytical views
            created_views = self.create_views()

            # 5. Verify manifest
            self.verify_manifest()

        finally:
            if self._conn is not None:
                try:
                    self._conn.close()
                except Exception:
                    pass

        elapsed = time.time() - start_time
        total_rows = sum(self.config.manifest.get("row_counts", {}).values()) if self.config.manifest else 0

        console.print(
            f"\n[bold green]✓ Snowflake export complete![/bold green] "
            f"{len(loaded_tables)} tables in {elapsed:.1f}s"
        )

        return ExportResult(
            target="snowflake",
            tables_exported=loaded_tables,
            total_rows=total_rows,
            views_created=created_views,
            duration_seconds=round(elapsed, 2),
            destination=f"{self.database}.{self.schema_name}",
            metadata={"stage": self.stage_name, "warehouse": self.warehouse},
        )

