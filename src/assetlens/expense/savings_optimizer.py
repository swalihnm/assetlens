"""M13 - savings programme optimiser (CP-SAT integer programme) and roll-up into the M6 forecast.

Choose initiatives so that EXPECTED savings (target x confidence) meet a goal at minimum implementation cost plus a
risk charge, subject to a headcount-impact cap and dependencies (an initiative needs its prerequisite).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from ortools.sat.python import cp_model

from assetlens.expense.analytics import savings_tracker

SCALE = 100          # work in $0.01m integers
RISK_WEIGHT = 0.25   # $ of risk charge per $ of unachieved (1 - confidence) savings


def optimise(goal_musd: float | None = None, goal_share: float = 0.6, headcount_cap: int = 150,
             s: pd.DataFrame | None = None, time_limit: float = 20.0) -> dict:
    s = savings_tracker() if s is None else s.copy()
    s = s.reset_index(drop=True)
    exp = (s.target_savings_musd * s.confidence * SCALE).round().astype(int).values
    cost = ((s.implementation_cost_musd + RISK_WEIGHT * s.target_savings_musd * (1 - s.confidence)) * SCALE).round().astype(int).values
    goal = int(round((goal_musd if goal_musd is not None else goal_share * exp.sum() / SCALE) * SCALE))
    m = cp_model.CpModel()
    x = [m.NewBoolVar(f"x{i}") for i in range(len(s))]
    m.Add(sum(int(exp[i]) * x[i] for i in range(len(s))) >= goal)
    m.Add(sum(int(s.headcount_impact[i]) * x[i] for i in range(len(s))) <= headcount_cap)
    idx = {k: i for i, k in enumerate(s.initiative_id)}
    for i, dep in enumerate(s.depends_on):
        if dep:
            m.AddImplication(x[i], x[idx[dep]])
    m.Minimize(sum(int(cost[i]) * x[i] for i in range(len(s))))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.random_seed = 1
    status = solver.Solve(m)
    ok = status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    chosen = [i for i in range(len(s)) if ok and solver.Value(x[i])]
    sel = s.loc[chosen]
    return dict(status=solver.StatusName(status), feasible=ok, goal_musd=goal / SCALE,
                expected_savings=float((sel.target_savings_musd * sel.confidence).sum()),
                implementation_cost=float(sel.implementation_cost_musd.sum()), objective_musd=(solver.ObjectiveValue() / SCALE) if ok else None,
                headcount=int(sel.headcount_impact.sum()), headcount_cap=headcount_cap, n_selected=len(sel),
                selected=sel[["initiative_id", "category", "target_savings_musd", "confidence", "implementation_cost_musd", "headcount_impact", "depends_on"]])


def forecast_rollup(selected: pd.DataFrame, scenario: str = "base", ramp_quarters: int = 4) -> pd.DataFrame:
    """Reduce forecast non-comp by the programme's expected annual savings, phased in linearly over `ramp_quarters`."""
    from assetlens.forecast.engine import load_base, run_scenario
    f = run_scenario(scenario, load_base())
    annual = float((selected.target_savings_musd * selected.confidence).sum())
    phase = np.minimum(f.t.values / ramp_quarters, 1.0)
    f["savings"] = annual / 4 * phase
    f["pretax_after_savings"] = f.pretax + f.savings
    f["margin_after_savings"] = f.pretax_after_savings / f.net_revenues
    return f[["t", "period_end", "pretax", "savings", "pretax_after_savings", "pretax_margin", "margin_after_savings"]]


if __name__ == "__main__":
    r = optimise()
    print({k: v for k, v in r.items() if k != "selected"})
    print(forecast_rollup(r["selected"]).round(3).tail(3))
