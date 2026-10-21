"""M11 - compensation strategy: ratio benchmarking, accrual with Q4 true-up, scenario sensitivity,
pay-for-performance (synthetic advisors) and pool allocation across businesses (synthetic)."""
from __future__ import annotations

import duckdb
import numpy as np
import pandas as pd
import statsmodels.api as sm

from assetlens.forecast.engine import CFG, load_base, run_scenario
from assetlens.warehouse.build import DB

FIXED_SHARE = 0.35        # share of base comp that is fixed salary / benefits (assumption)
PAYOUT_RATE = 0.28        # advisor payout on revenue (assumption, synthetic)
NNA_BONUS = 0.0015        # bonus per $ of net new assets (assumption, synthetic)
BASE_SALARY_MUSD = 0.12


def _q(sql):
    con = duckdb.connect(str(DB), read_only=True)
    try:
        return con.execute(sql).df()
    finally:
        con.close()


def ratio_benchmark() -> pd.DataFrame:
    """Peer T4Q comp ratios (latest) plus GS segment annual comp ratio FY2022-25 (ASU 2023-07 disclosure)."""
    peers = _q("""select ticker, period_end, comp_ratio_t4q from mart_peer_benchmark where comp_ratio_t4q is not null
                  qualify row_number() over (partition by ticker order by period_end desc) = 1""")
    peers["basis"] = "T4Q, company"
    f = _q("select metric, period_end, value from fact_provenance p join fact_financials f using(fact_id) "
           "where f.ticker='GS' and f.metric in ('comp_benefits')")
    cur = pd.read_csv(f"{DB.parents[2]}/data/interim/gs_facts_latest.csv")
    a = cur[(cur.perimeter == "AWM") & (cur.period_type == "FY") & cur.metric.isin(["comp_benefits", "net_revenues"])]
    a = a.pivot_table(index="period_end", columns="metric", values="value", aggfunc="first").dropna()
    gs = pd.DataFrame(dict(ticker="GS", period_end=a.index, comp_ratio_t4q=(a.comp_benefits / a.net_revenues).values, basis="FY, AWM segment"))
    return pd.concat([peers, gs], ignore_index=True)


def accrual_model(fy_revenue_quarters: list[float], target_ratio: float = CFG["comp_ratio_target"], base_comp: float | None = None,
                  final_adjustment: float = 0.0) -> pd.DataFrame:
    """Accrue the VARIABLE pool each quarter at the YTD target ratio; Q4 true-up to the final pool.
    pool_final = target_ratio x FY revenue x (1 + final_adjustment) - fixed comp (fixed = FIXED_SHARE of target comp at budget)."""
    rev = np.array(fy_revenue_quarters, dtype=float)
    budget_rev = rev.sum() if base_comp is None else base_comp / target_ratio
    fixed_q = FIXED_SHARE * target_ratio * budget_rev / 4
    var_ratio = (target_ratio * budget_rev - 4 * fixed_q) / budget_rev      # variable pool as % of revenue
    rows, cum_accr = [], 0.0
    final_pool = max(0.0, target_ratio * rev.sum() * (1 + final_adjustment) - 4 * fixed_q)
    for q in range(4):
        accrual = var_ratio * rev[q]
        trueup = (final_pool - (cum_accr + accrual)) if q == 3 else 0.0
        cum_accr += accrual + trueup
        rows.append(dict(quarter=q + 1, revenue=rev[q], fixed_comp=fixed_q, variable_accrual=accrual, true_up=trueup,
                         total_comp=fixed_q + accrual + trueup, comp_ratio=(fixed_q + accrual + trueup) / rev[q]))
    d = pd.DataFrame(rows)
    d.attrs["final_pool"] = final_pool
    d.attrs["fixed_total"] = 4 * fixed_q
    return d


def scenario_sensitivity() -> pd.DataFrame:
    b = load_base()
    rows = []
    for s in ("bull", "base", "bear", "stress"):
        f = run_scenario(s, b).head(4)                                    # next four quarters
        rows.append(dict(scenario=s, revenue=f.net_revenues.sum(), comp_pool=f.comp.sum(), comp_ratio=f.comp.sum() / f.net_revenues.sum(),
                         pretax=f.pretax.sum(), pretax_margin=f.pretax.sum() / f.net_revenues.sum()))
    d = pd.DataFrame(rows)
    base = d[d.scenario == "base"].iloc[0]
    d["pool_vs_base"] = d.comp_pool - base.comp_pool
    d["margin_vs_base_pp"] = (d.pretax_margin - base.pretax_margin) * 100
    return d


def build_fact_comp(seed: int = 11) -> pd.DataFrame:
    """Synthetic annual advisor compensation: salary + payout x revenue + NNA bonus + noise (seeded)."""
    rng = np.random.default_rng(seed)
    fa = _q("select advisor_id, extract(year from cast(period_end as date)) as year, sum(revenue_musd) revenue, sum(nna_musd) nna, "
            "avg(tenure_years) tenure from fact_advisor_monthly group by 1, 2")
    adv = _q("select advisor_id, region from dim_advisor")
    d = fa.merge(adv, on="advisor_id")
    noise = rng.normal(0, 0.12, len(d)) * (BASE_SALARY_MUSD + PAYOUT_RATE * d.revenue)
    outlier = rng.random(len(d)) < 0.02
    d["comp_musd"] = (BASE_SALARY_MUSD + PAYOUT_RATE * d.revenue + NNA_BONUS * d.nna.clip(lower=0) + noise
                      + np.where(outlier, rng.choice([-1, 1], len(d)) * 0.25 * (BASE_SALARY_MUSD + PAYOUT_RATE * d.revenue), 0)).clip(lower=0.05)
    d["synthetic"] = True
    con = duckdb.connect(str(DB))
    con.register("x", d)
    con.execute("create or replace table fact_comp as select * from x")
    con.close()
    return d


def pay_for_performance(d: pd.DataFrame | None = None) -> dict:
    d = build_fact_comp() if d is None else d
    d = d[d.revenue > 0.2].copy()
    X = sm.add_constant(d[["revenue", "nna"]])
    res = sm.OLS(d.comp_musd, X).fit(cov_type="HC3")
    infl = res.get_influence()
    d["student_resid"] = infl.resid_studentized_external
    d["outlier"] = d.student_resid.abs() > 3
    d["payout_ratio"] = d.comp_musd / d.revenue
    q1, rev75 = d.payout_ratio.quantile(0.25), d.revenue.quantile(0.75)
    d["retention_risk"] = (d.payout_ratio < q1) & (d.revenue > rev75)
    return dict(coef=res.params.to_dict(), r2=float(res.rsquared), n=len(d), p_value_revenue=float(res.pvalues["revenue"]),
                outliers=int(d.outlier.sum()), retention_risk=int(d.retention_risk.sum()), flagged=d[d.outlier | d.retention_risk])


def pool_allocation() -> pd.DataFrame:
    """Allocate the T4Q direct-comp pool by revenue share vs contribution share; compare resulting margins."""
    p = _q("select business, sum(net_revenues) rev, sum(contribution_margin + direct_comp) pre_comp_contrib, sum(direct_comp) comp "
           "from fact_business_pnl where period_end in (select distinct period_end from fact_business_pnl order by 1 desc limit 4) group by 1")
    pool = p.comp.sum()
    p["pool_revenue_based"] = pool * p.rev / p.rev.sum()
    p["pool_contribution_based"] = pool * p.pre_comp_contrib / p.pre_comp_contrib.sum()
    p["margin_revenue_based"] = (p.pre_comp_contrib - p.pool_revenue_based) / p.rev
    p["margin_contribution_based"] = (p.pre_comp_contrib - p.pool_contribution_based) / p.rev
    p["margin_delta_pp"] = (p.margin_contribution_based - p.margin_revenue_based) * 100
    return p


if __name__ == "__main__":
    pd.set_option("display.width", 220)
    print(ratio_benchmark().round(3))
    a = accrual_model([4078, 4597, 5051, 5400], base_comp=0.446 * 19000, final_adjustment=-0.02)   # budget revenue 19.0bn, -2% discretionary
    print(a.round(1), a.attrs)
    print(scenario_sensitivity().round(3))
    r = pay_for_performance()
    print({k: v for k, v in r.items() if k != "flagged"})
    print(pool_allocation().round(3))
