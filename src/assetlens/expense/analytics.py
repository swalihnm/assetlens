"""M13 - spend cube, budget vs actual with run/exit rate, vendor concentration (HHI, tail spend), savings tracker.
All inputs are synthetic (M7)."""
from __future__ import annotations

import duckdb
import pandas as pd

from assetlens.warehouse.build import DB

THRESH_PCT = 0.10


def _gl() -> pd.DataFrame:
    con = duckdb.connect(str(DB), read_only=True)
    g = con.execute("select posting_date, owner, region, category, vendor_id, is_comp, amount_musd from fact_gl").df()
    con.close()
    g["month"] = pd.to_datetime(g.posting_date).dt.to_period("M").astype(str)
    return g


def spend_cube(g: pd.DataFrame | None = None) -> pd.DataFrame:
    g = _gl() if g is None else g
    return g.groupby(["month", "owner", "region", "category"], as_index=False).amount_musd.sum()


def budget_vs_actual(g: pd.DataFrame | None = None) -> pd.DataFrame:
    """Budget for month m = same month of the prior year x (1 + 8% plan growth); available where the GL has both years."""
    g = _gl() if g is None else g
    m = g.groupby(["month", "owner"], as_index=False).amount_musd.sum()
    m["prev"] = (pd.PeriodIndex(m.month, freq="M") - 12).astype(str)
    b = m.merge(m[["month", "owner", "amount_musd"]].rename(columns={"month": "prev", "amount_musd": "py"}), on=["prev", "owner"])
    b["budget"] = b.py * 1.08   # plan growth = top-down budget growth target (assumption)
    b["variance"] = b.amount_musd - b.budget
    b["variance_pct"] = b.variance / b.budget
    b["flag"] = b.variance_pct.abs() > THRESH_PCT
    return b.rename(columns={"amount_musd": "actual"}).drop(columns=["prev"])


def run_exit_rate(g: pd.DataFrame | None = None) -> dict:
    g = _gl() if g is None else g
    mon = g.groupby("month").amount_musd.sum().sort_index()
    return dict(last_month=mon.index[-1], run_rate_3m_annualised=float(mon.iloc[-3:].sum() * 4),
                exit_rate_last_month_annualised=float(mon.iloc[-1] * 12), t12m=float(mon.iloc[-12:].sum()))


def vendor_concentration(g: pd.DataFrame | None = None) -> dict:
    g = _gl() if g is None else g
    v = g[(~g.is_comp) & (g.vendor_id != "")].groupby("vendor_id").amount_musd.sum().sort_values(ascending=False)
    share = v / v.sum()
    hhi = float((share ** 2).sum() * 10_000)
    n80 = int((share.cumsum() < 0.8).sum() + 1)
    tail = v[v.index.isin(share[share.cumsum() > 0.8].index)]
    cat = (g[(~g.is_comp) & (g.vendor_id != "")].groupby(["category", "vendor_id"]).amount_musd.sum().reset_index())
    cat_hhi = cat.groupby("category").apply(lambda x: float(((x.amount_musd / x.amount_musd.sum()) ** 2).sum() * 10_000), include_groups=False)
    return dict(vendors=len(v), hhi=hhi, vendors_for_80pct=n80, tail_vendors=len(tail), tail_spend_share=float(tail.sum() / v.sum()),
                category_hhi=cat_hhi.round(0).to_dict())


def savings_tracker() -> pd.DataFrame:
    con = duckdb.connect(str(DB), read_only=True)
    s = con.execute("select * from fact_savings").df()
    con.close()
    s["realisation"] = s.realised_to_date_musd / s.target_savings_musd
    s["expected_savings"] = s.target_savings_musd * s.confidence
    return s


def tracker_summary(s: pd.DataFrame | None = None) -> pd.DataFrame:
    s = savings_tracker() if s is None else s
    return s.groupby("owner").agg(initiatives=("initiative_id", "count"), target=("target_savings_musd", "sum"),
                                  realised=("realised_to_date_musd", "sum"), expected=("expected_savings", "sum"),
                                  headcount=("headcount_impact", "sum")).assign(realisation=lambda x: x.realised / x.target).reset_index()


if __name__ == "__main__":
    g = _gl()
    print(run_exit_rate(g))
    vc = vendor_concentration(g)
    print({k: v for k, v in vc.items() if k != "category_hhi"})
    print(budget_vs_actual(g).flag.mean())
    print(tracker_summary().round(2))
