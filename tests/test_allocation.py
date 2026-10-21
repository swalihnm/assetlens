import duckdb
import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from assetlens.allocation import methods as M
from assetlens.warehouse.build import DB


def _inputs(seed, P=5, B=6):
    r = np.random.default_rng(seed)
    cost = r.uniform(10, 500, P)
    usage = r.uniform(0, 0.12, (P, P))
    np.fill_diagonal(usage, 0)
    shares = r.dirichlet(np.ones(B), P)
    return cost, usage, shares


@settings(max_examples=60, deadline=None)
@given(st.integers(0, 10_000))
def test_every_method_conserves_total_cost(seed):
    cost, usage, shares = _inputs(seed)
    order = list(np.random.default_rng(seed).permutation(len(cost)))
    for mat in (M.direct_alloc(cost, shares), M.reciprocal_alloc(cost, usage, shares),
                M.step_down_alloc(cost, usage, shares, order)):
        assert mat.sum() == pytest.approx(cost.sum(), rel=1e-9)
        assert (mat >= -1e-9).all()


def test_reciprocal_equals_direct_when_no_inter_pool_usage():
    cost, _, shares = _inputs(1)
    z = np.zeros((5, 5))
    assert np.allclose(M.reciprocal_alloc(cost, z, shares), M.direct_alloc(cost, shares))
    assert np.allclose(M.step_down_alloc(cost, z, shares, [0, 1, 2, 3, 4]), M.direct_alloc(cost, shares))


@pytest.mark.skipif(not DB.exists(), reason="warehouse not built")
def test_fully_allocated_pretax_reconciles_to_public_segment():
    con = duckdb.connect(str(DB), read_only=True)
    d = con.execute("""select p.method, p.period_end, sum(p.fully_allocated_pretax) syn, max(f.value) pub
        from mart_profitability_by_business p join fact_financials f
          on f.ticker='GS' and f.metric='pretax_earnings' and f.period_end=p.period_end
        group by 1,2""").df()
    con.close()
    assert len(d) > 50 and ((d.syn - d.pub).abs() < 1.0).all()
