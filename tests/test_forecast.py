import duckdb
import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from assetlens.forecast import bridges
from assetlens.warehouse.build import DB


@settings(max_examples=100, deadline=None)
@given(st.integers(0, 100_000))
def test_pvm_sums_exactly(seed):
    r = np.random.default_rng(seed)
    a0, a1 = r.uniform(10, 500, 4), r.uniform(10, 500, 4)
    y0, y1 = r.uniform(0.0001, 0.01, 4), r.uniform(0.0001, 0.01, 4)
    out = bridges.pvm(a0, a0 * y0, a1, a1 * y1)
    assert out["total"] == pytest.approx(out["actual_change"], abs=1e-9)


@settings(max_examples=100, deadline=None)
@given(st.floats(100, 5000), st.floats(0.05, 0.5), st.floats(100, 5000), st.floats(0.05, 0.5))
def test_expense_bridge_sums_exactly(h0, c0, h1, c1):
    out = bridges.expense_bridge(h0, c0, h1, c1, 10.0, 12.0)
    assert out["total"] == pytest.approx(out["actual_change"], rel=1e-9, abs=1e-9)


pytestmark_db = pytest.mark.skipif(not DB.exists(), reason="warehouse not built")


@pytestmark_db
def test_model_reproduces_last_reported_quarter_within_tolerance():
    from assetlens.forecast.engine import reproduce_quarter
    assert abs(reproduce_quarter("2026-06-30")["error_pct"]) < 0.05


@pytestmark_db
def test_scenarios_ordered_and_stored():
    from assetlens.forecast.engine import run_all
    d = run_all()
    last = d[d.t == 8].set_index("scenario")
    assert last.pretax_margin["bull"] > last.pretax_margin["base"] > last.pretax_margin["bear"] > last.pretax_margin["stress"]
    assert set(d.scenario) == {"base", "bull", "bear", "stress"} and (d.groupby("scenario").size() == 8).all()
    # comp respects the fixed floor
    assert (d.comp / d.net_revenues >= 0.446 - 1e-9).all()  # comp = max(floor, ratio x revenue)
    con = duckdb.connect(str(DB), read_only=True)
    assert con.execute("select count(*) from fact_forecast").fetchone()[0] == 32
    con.close()
