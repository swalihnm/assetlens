import numpy as np
import pytest

from assetlens.warehouse.build import DB

pytestmark = pytest.mark.skipif(not DB.exists(), reason="warehouse not built")


def test_detection_metrics_and_per_type_recall():
    from assetlens.expense.anomaly import evaluate
    r = evaluate(n_estimators=60)
    assert r["rules_binary"]["recall"] > 0.75 and r["rules_binary"]["precision"] > 0.6
    assert r["combined"]["precision_at_k"] >= r["isolation_forest"]["precision_at_k"]
    for t in ("over_limit", "duplicate", "split_transaction"):
        assert r["per_type"][t]["recall_rules"] > 0.95


def test_optimiser_feasible_and_beats_greedy():
    from assetlens.expense.analytics import savings_tracker
    from assetlens.expense.savings_optimizer import RISK_WEIGHT, optimise
    s = savings_tracker()
    r = optimise(s=s)
    sel = r["selected"]
    assert r["feasible"] and r["expected_savings"] >= r["goal_musd"] - 0.01
    assert r["headcount"] <= r["headcount_cap"]
    chosen = set(sel.initiative_id)
    assert all((d == "" or d in chosen) for d in sel.depends_on)       # dependencies respected
    # greedy by cost-per-expected-saving (ignoring caps) can't be cheaper than the optimum when it satisfies the caps
    s = s.assign(c=s.implementation_cost_musd + RISK_WEIGHT * s.target_savings_musd * (1 - s.confidence),
                 e=s.target_savings_musd * s.confidence)
    g = s.assign(ratio=s.c / s.e).sort_values("ratio").assign(cum=lambda x: x.e.cumsum())
    greedy = g[g.cum.shift(fill_value=0) < r["goal_musd"]]
    if greedy.headcount_impact.sum() <= 150 and all((d == "" or d in set(greedy.initiative_id)) for d in greedy.depends_on):
        assert r["objective_musd"] <= greedy.c.sum() + 0.01


def test_vendor_metrics_bounds():
    from assetlens.expense.analytics import vendor_concentration
    v = vendor_concentration()
    assert 0 < v["hhi"] < 10_000 and 0 < v["tail_spend_share"] <= 0.25
