"""Tests for DuckDB export and Dataset Profiler modules."""

from pathlib import Path
import duckdb
import pytest

from ecommerce_synth.duckdb_exporter import export_to_duckdb
from ecommerce_synth.profiler import DatasetProfiler


def test_duckdb_export_and_views(tmp_path: Path):
    from ecommerce_synth.config import load_config
    from ecommerce_synth.orchestrator import Orchestrator

    output_dir = tmp_path / "duckdb_test_dataset"
    config = load_config(tier_name="small", seed=99, output_dir=output_dir)
    orchestrator = Orchestrator(config)
    orchestrator.run(only=["customers", "orders"])

    db_path = export_to_duckdb(output_dir)
    assert db_path.exists()

    conn = duckdb.connect(str(db_path))
    tables = conn.execute("SHOW TABLES").fetchall()
    table_names = [t[0] for t in tables]

    assert "customers" in table_names
    assert "orders_online" in table_names
    assert "v_omnichannel_sales" in table_names
    assert "v_customer_360" in table_names

    res = conn.execute("SELECT COUNT(*) FROM customers").fetchone()
    assert res[0] > 0
    conn.close()


def test_profiler_metrics_and_html(tmp_path: Path):
    from ecommerce_synth.config import load_config
    from ecommerce_synth.orchestrator import Orchestrator

    output_dir = tmp_path / "profiler_test_dataset"
    config = load_config(tier_name="small", seed=101, output_dir=output_dir)
    orchestrator = Orchestrator(config)
    orchestrator.run()

    profiler = DatasetProfiler(output_dir)
    metrics = profiler.profile()

    assert "financials" in metrics
    assert metrics["financials"]["total_gmv"] > 0
    assert "customers" in metrics
    assert metrics["customers"]["total_customers"] > 0
    assert "funnel" in metrics

    # HTML export
    html_path = output_dir / "test_report.html"
    profiler.export_html(html_path)
    assert html_path.exists()
    assert html_path.stat().st_size > 0
