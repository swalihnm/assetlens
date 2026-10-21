import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from assetlens.comp import analysis as C
from assetlens.warehouse.build import DB


@settings(max_examples=60, deadline=None)
@given(st.lists(st.floats(2000, 8000), min_size=4, max_size=4), st.floats(15000, 25000), st.floats(-0.1, 0.1))
def test_accrual_and_trueup_reconcile_to_annual_pool(rev, budget_rev, adj):
    a = C.accrual_model(rev, base_comp=0.446 * budget_rev, final_adjustment=adj)
    final = a.attrs["final_pool"]
    assert (a.variable_accrual + a.true_up).sum() == pytest.approx(final, rel=1e-9)
    assert a.true_up.iloc[:3].abs().sum() == 0                      # true-up only in Q4
    assert a.fixed_comp.sum() == pytest.approx(a.attrs["fixed_total"])


db = pytest.mark.skipif(not DB.exists(), reason="warehouse not built")


@db
def test_pay_for_performance_recovers_planted_payout_and_scenarios_order():
    r = C.pay_for_performance()
    assert r["coef"]["revenue"] == pytest.approx(C.PAYOUT_RATE, abs=0.02) and r["r2"] > 0.9
    s = C.scenario_sensitivity().set_index("scenario")
    assert s.comp_pool["bull"] > s.comp_pool["base"] > s.comp_pool["bear"] > s.comp_pool["stress"]
    p = C.pool_allocation()
    assert p.pool_revenue_based.sum() == pytest.approx(p.pool_contribution_based.sum())


@db
def test_sales_metrics():
    from assetlens.sales import analytics as S
    c = S.concentration()
    assert 0 < c["gini"] < 1 and c["top10pct_share"] < c["top20pct_share"] <= 1
    k = S.kpis()
    assert (k.revenue_per_advisor > 0).all() and 20 < k.wallet_proxy_revenue_bps_of_aum.median() < 200
    f = S.nna_forecast()
    assert len(f) == 4 and (f.p10 <= f.forecast).all() and (f.forecast <= f.p90).all()
    assert S.leading_indicator()["beta_proposals"] > 0
