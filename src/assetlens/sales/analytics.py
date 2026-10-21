"""M12 - sales and productivity analytics on the SYNTHETIC advisor data: KPIs, quota attainment, cohort ramp curves,
time to productivity, concentration (Lorenz / Gini), pipeline funnel with leading indicator, NNA forecast."""
from __future__ import annotations

import duckdb
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from assetlens.warehouse.build import DB


def _load() -> tuple[pd.DataFrame, pd.DataFrame]:
    con = duckdb.connect(str(DB), read_only=True)
    f = con.execute("select * from fact_advisor_monthly").df()
    a = con.execute("select * from dim_advisor").df()
    con.close()
    f["period_end"] = pd.to_datetime(f.period_end)
    return f.merge(a[["advisor_id", "region", "cohort"]], on="advisor_id"), a


def kpis(f: pd.DataFrame | None = None) -> pd.DataFrame:
    f = _load()[0] if f is None else f
    f = f.copy()
    f["band"] = pd.cut(f.tenure_years, [-1, 1, 2, 3, 99], labels=["0-1", "1-2", "2-3", "3+"])
    f["quota"] = 1.05 * f.groupby(["period_end", "band"], observed=True).revenue_musd.transform("median")
    f["attainment"] = f.revenue_musd / f.quota
    g = f.groupby(["period_end", "region"]).agg(advisors=("advisor_id", "nunique"), revenue=("revenue_musd", "sum"), nna=("nna_musd", "sum"),
                                                aum=("aum_musd", "sum"), clients=("clients", "sum"),
                                                quota_attainment=("attainment", "median")).reset_index()
    g["revenue_per_advisor"] = g.revenue / g.advisors
    g["aum_per_advisor"] = g.aum / g.advisors
    g["wallet_proxy_revenue_bps_of_aum"] = g.revenue * 4 / g.aum * 1e4
    g["synthetic"] = True
    return g


def cohort_ramp(f: pd.DataFrame | None = None) -> tuple[pd.DataFrame, dict]:
    f = _load()[0] if f is None else f
    f = f.copy()
    f["tenure_bucket"] = np.floor(f.tenure_years * 2) / 2                      # half-year buckets
    ramp = f.groupby(["cohort", "tenure_bucket"]).agg(revenue_per_advisor_q=("revenue_musd", "mean"), advisors=("advisor_id", "nunique")).reset_index()
    mature = f[f.tenure_years >= 3].revenue_musd.median()
    curve = f.groupby("tenure_bucket").revenue_musd.mean()
    ttp = next((float(t) for t, v in curve.items() if v >= 0.8 * mature), float("nan"))
    return ramp, dict(mature_median_revenue_q=float(mature), time_to_productivity_years=ttp)


def concentration(f: pd.DataFrame | None = None) -> dict:
    f = _load()[0] if f is None else f
    last4 = sorted(f.period_end.unique())[-4:]
    r = f[f.period_end.isin(last4)].groupby("advisor_id").revenue_musd.sum().sort_values()
    cum = r.cumsum() / r.sum()
    x = np.arange(1, len(r) + 1) / len(r)
    gini = float(1 - 2 * np.trapezoid(cum.values, x) + 1 / len(r))
    return dict(gini=gini, top10pct_share=float(r.tail(int(len(r) * 0.1)).sum() / r.sum()),
                top20pct_share=float(r.tail(int(len(r) * 0.2)).sum() / r.sum()), advisors=len(r),
                lorenz=pd.DataFrame(dict(population_share=x, revenue_share=cum.values)))


def pipeline(f: pd.DataFrame | None = None, seed: int = 21) -> pd.DataFrame:
    """Synthetic funnel: proposals LEAD next-quarter wins (and so NNA) by construction - documented, not a finding."""
    f = _load()[0] if f is None else f
    rng = np.random.default_rng(seed)
    nna = f.groupby("period_end").nna_musd.sum().sort_index()
    q = nna.index
    wins = np.maximum(1, ((nna.clip(lower=0) + 5) / 12.0)).round().astype(int)
    rows = []
    for i, pe in enumerate(q):
        nxt_wins = wins.iloc[i + 1] if i + 1 < len(q) else wins.iloc[i]
        proposals = int(max(5, rng.poisson(nxt_wins / 0.22)))
        meetings = int(proposals / rng.uniform(0.40, 0.50))
        leads = int(meetings / rng.uniform(0.45, 0.55))
        rows.append(dict(period_end=pe, leads=leads, meetings=meetings, proposals=proposals, wins=int(wins.iloc[i]), nna_musd=float(nna.iloc[i])))
    d = pd.DataFrame(rows)
    d["lead_to_meeting"], d["meeting_to_proposal"], d["proposal_to_win"] = d.meetings / d.leads, d.proposals / d.meetings, d.wins / d.proposals
    d["synthetic"] = True
    return d


def leading_indicator(p: pd.DataFrame | None = None) -> dict:
    p = pipeline() if p is None else p
    y = p.nna_musd.shift(-1).dropna()
    X = sm.add_constant(p.proposals.iloc[:-1].reset_index(drop=True))
    res = sm.OLS(y.reset_index(drop=True), X).fit(cov_type="HC3")
    return dict(beta_proposals=float(res.params.iloc[1]), p_value=float(res.pvalues.iloc[1]), r2=float(res.rsquared), n=int(res.nobs))


def nna_forecast(f: pd.DataFrame | None = None, h: int = 4, n_boot: int = 1000, seed: int = 5) -> pd.DataFrame:
    f = _load()[0] if f is None else f
    y = f.groupby("period_end").nna_musd.sum().sort_index()
    y.index = pd.PeriodIndex(y.index, freq="Q")
    fit = ExponentialSmoothing(y.values, trend="add", damped_trend=True).fit()
    point = fit.forecast(h)
    resid = y.values - fit.fittedvalues
    rng = np.random.default_rng(seed)
    sims = point[None, :] + rng.choice(resid, (n_boot, h))
    idx = [y.index[-1] + i for i in range(1, h + 1)]
    return pd.DataFrame(dict(quarter=[str(i) for i in idx], forecast=point, p10=np.percentile(sims, 10, axis=0), p90=np.percentile(sims, 90, axis=0)))


def save() -> None:
    f, _ = _load()
    ramp, _ = cohort_ramp(f)
    tabs = {"mart_sales_productivity": kpis(f), "mart_cohort_ramp": ramp.assign(synthetic=True), "fact_pipeline": pipeline(f),
            "mart_nna_forecast": nna_forecast(f).assign(synthetic=True)}
    con = duckdb.connect(str(DB))
    for n, d in tabs.items():
        con.register("x", d)
        con.execute(f"create or replace table {n} as select * from x")
        con.unregister("x")
    con.close()


if __name__ == "__main__":
    save()
    f, _ = _load()
    print(kpis(f).tail(3).round(2).to_string())
    print(cohort_ramp(f)[1])
    c = concentration(f)
    print({k: round(v, 3) if isinstance(v, float) else v for k, v in c.items() if k != "lorenz"})
    print(leading_indicator())
    print(nna_forecast(f).round(2))
