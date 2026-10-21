"""M6 budget process: top-down vs bottom-up, budget vs actual vs prior year, PVM bridges, run/exit-rate."""
from __future__ import annotations

import duckdb
import numpy as np
import pandas as pd

from assetlens.forecast import bridges
from assetlens.forecast.engine import CFG, CLASSES, calibrate_yields, load_base, run_scenario
from assetlens.warehouse.build import DB

THRESH_PCT, THRESH_ABS = 0.05, 100.0      # flag variances beyond +/-5% and $100m (assumption)


def _gs() -> pd.DataFrame:
    con = duckdb.connect(str(DB), read_only=True)
    f = con.execute("select period_end, metric, value from fact_financials where ticker='GS'").df()
    con.close()
    w = f.pivot_table(index="period_end", columns="metric", values="value", aggfunc="first").sort_index()
    w.index = pd.to_datetime(w.index)
    return w


def class_aum_fees(w: pd.DataFrame, pe: pd.Timestamp) -> tuple[np.ndarray, np.ndarray]:
    """Average AUS and fees by class. Class fees = avg_k * rel_yield_k * s_t, s_t chosen so that the sum
    equals reported management fees (class yields are relative ASSUMPTIONS; totals are public)."""
    cols = ["aus_alternatives", "aus_equity", "aus_fixed_income", "aus_liquidity"]
    prev = w.index[w.index.get_loc(pe) - 1]
    avg = np.array([(w.loc[pe, c] + w.loc[prev, c]) / 2 for c in cols])
    rel = np.array([CFG["asset_classes"][k]["rel_yield"] for k in CLASSES])
    s = w.loc[pe, "rev_mgmt_other_fees"] / (avg * rel).sum()
    return avg, avg * rel * s


def fee_bridge(p0: str, p1: str) -> dict[str, float]:
    w = _gs()
    a0, f0 = class_aum_fees(w, pd.Timestamp(p0))
    a1, f1 = class_aum_fees(w, pd.Timestamp(p1))
    return bridges.pvm(a0, f0, a1, f1)


def scenario_fee_bridge(base: str = "base", other: str = "bear", t: int = 8) -> dict[str, float]:
    b = load_base()
    x, y = run_scenario(base, b), run_scenario(other, b)
    cols = [f"aus_{k}" for k in CLASSES]

    def avg(df):  # average AUS by class in quarter t
        return np.array([(df.loc[df.t == t - 1, c].iloc[0] + df.loc[df.t == t, c].iloc[0]) / 2 for c in cols])

    def yld(df):  # period yield by class
        return np.array([df.loc[df.t == t, f"yield_{k}_bps"].iloc[0] / 1e4 / 4 for k in CLASSES])

    a0, a1 = avg(x), avg(y)
    return bridges.pvm(a0, a0 * yld(x), a1, a1 * yld(y))


def budget_vs_actual(fy: int = 2026) -> pd.DataFrame:
    w = _gs()
    py = w[(w.index.year == fy - 1)]
    py_rev = py.net_revenues.sum()
    tgt = CFG["budget_targets"]
    td_rev = py_rev * (1 + tgt["revenue_growth"])
    seas = (py.net_revenues / py_rev).values
    rows = []
    for i, pe in enumerate(pd.date_range(f"{fy}-03-31", periods=4, freq="QE")):
        bud_rev = td_rev * seas[i]
        bud_pt = bud_rev * tgt["pretax_margin"]
        act = w.loc[pe] if pe in w.index else None
        rows.append(dict(
            period_end=pe, budget_revenue=bud_rev, budget_pretax=bud_pt,
            actual_revenue=act.net_revenues if act is not None else np.nan,
            actual_pretax=act.pretax_earnings if act is not None else np.nan,
            prior_year_revenue=py.net_revenues.iloc[i], prior_year_pretax=py.pretax_earnings.iloc[i]))
    d = pd.DataFrame(rows)
    d["rev_variance"] = d.actual_revenue - d.budget_revenue
    d["rev_variance_pct"] = d.rev_variance / d.budget_revenue
    d["pretax_variance"] = d.actual_pretax - d.budget_pretax
    d["pretax_variance_pct"] = d.pretax_variance / d.budget_pretax
    d["flag"] = ((d.rev_variance_pct.abs() > THRESH_PCT) & (d.rev_variance.abs() > THRESH_ABS)) | \
                ((d.pretax_variance_pct.abs() > THRESH_PCT) & (d.pretax_variance.abs() > THRESH_ABS))
    d["owner_commentary"] = np.where(d.flag, "REQUIRED - owner to explain variance", "")
    return d


def top_down_vs_bottom_up(fy: int = 2026, seed: int = 7) -> pd.DataFrame:
    """Bottom-up submissions by business (synthetic: owners sandbag ~3-6%) vs the top-down target."""
    con = duckdb.connect(str(DB), read_only=True)
    p = con.execute("select business, period_end, net_revenues from fact_business_pnl").df()
    con.close()
    p["period_end"] = pd.to_datetime(p.period_end)
    py = p[p.period_end.dt.year == fy - 1].groupby("business").net_revenues.sum()
    if py.empty:
        py = p[p.period_end >= p.period_end.max() - pd.DateOffset(months=11)].groupby("business").net_revenues.sum()
    rng = np.random.default_rng(seed)
    g = CFG["budget_targets"]["revenue_growth"]
    bu = py * (1 + g - rng.uniform(0.03, 0.06, len(py)) + rng.normal(0, 0.02, len(py)))
    td = py * (1 + g)
    d = pd.DataFrame(dict(prior_year=py, top_down=td, bottom_up=bu))
    d["gap"] = d.bottom_up - d.top_down
    d["gap_pct"] = d.gap / d.top_down
    d["synthetic"] = True
    return d.reset_index()


def run_exit_rate() -> dict[str, float]:
    """Run-rate = last quarter's fees x4; exit-rate = period-end AUS x current yields (annualised)."""
    b = load_base()
    y = calibrate_yields(b)
    exit_fees = sum(b.aus[k] * y[k] for k in CLASSES)
    return dict(run_rate_fees=b.mgmt_fees * 4, exit_rate_fees=exit_fees, uplift=exit_fees / (b.mgmt_fees * 4) - 1)


def save() -> None:
    tables = [("mart_budget_variance", budget_vs_actual()),
              ("mart_top_down_vs_bottom_up", top_down_vs_bottom_up())]
    con = duckdb.connect(str(DB))
    for name, df in tables:
        con.register("x", df)
        con.execute(f"create or replace table {name} as select * from x")
        con.unregister("x")
    con.close()


if __name__ == "__main__":
    pd.set_option("display.width", 250)
    save()
    print(budget_vs_actual().round(1).to_string())
    print(top_down_vs_bottom_up().round(2).to_string())
    print("YoY fee bridge Q2'26 vs Q2'25:", {k: round(v, 1) for k, v in fee_bridge("2025-06-30", "2026-06-30").items()})
    print("Bear vs base Q8:", {k: round(v, 1) for k, v in scenario_fee_bridge().items()})
    print(run_exit_rate())
