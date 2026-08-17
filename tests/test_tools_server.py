"""Smoke tests for the sandboxed pandas/plot tools — no API key required."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from agent.tools_server import render_plot, run_pandas_query  # noqa: E402

SAMPLE_CSV = os.path.join(os.path.dirname(__file__), "..", "data", "world_population.csv")


def test_run_pandas_query_basic():
    out = run_pandas_query(csv_path=SAMPLE_CSV, code="result = len(df)")
    assert out.isdigit()


def test_run_pandas_query_blocks_imports():
    out = run_pandas_query(csv_path=SAMPLE_CSV, code="import os\nresult = 1")
    assert out.startswith("ERROR")


def test_run_pandas_query_requires_result():
    out = run_pandas_query(csv_path=SAMPLE_CSV, code="x = 1")
    assert out.startswith("ERROR")


def test_render_plot_basic():
    out = render_plot(
        csv_path=SAMPLE_CSV,
        code="fig = px.bar(df.head(5), x='Country/Territory', y='2022 Population')",
    )
    assert out.startswith("{")


def test_render_plot_requires_figure():
    out = render_plot(csv_path=SAMPLE_CSV, code="x = 1")
    assert out.startswith("ERROR")
