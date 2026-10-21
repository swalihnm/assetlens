"""M4 - peer benchmark mart. All definitions follow docs/METRICS.md (Section 6 of the spec)."""
from __future__ import annotations

import duckdb
import numpy as np
import pandas as pd
import statsmodels.api as sm

from assetlens.warehouse.build import DB

FEE_METRIC = {"GS": "rev_mgmt_other_fees", "BLK": "fees_base_sec_lending",
              "TROW": "fees_investment_advisory", "IVZ": "fees_investment_management",
              "MS": "fees_asset_management", "JPM": "fees_asset_management", "BEN": "fees_investment_management"}
# operating-profit measure used for the like-for-like margin
OPINC_METRIC = {"GS": "pretax_earnings", "BLK": "operating_income", "TROW": "operating_income",
                "IVZ": "operating_income", "MS": "pretax_income", "JPM": "pretax_income", "BEN": "operating_income"}

COMPARABILITY = pd.DataFrame([
    ("GS", "Unit", "Asset & Wealth Management segment only (not firm); perimeter re-based Q4-2022 (see DECISIONS)."),
    ("GS", "Asset base", "Assets under supervision (AUS) - includes advisory/third-party-distributed and liquidity products; not strictly AUM."),
    ("GS", "Fee yield", "Management and other fees / average AUS. 'Other fees' includes some non-AUM-linked fees, so yield is an upper bound."),
    ("GS", "Margin", "Segment pre-tax earnings / net revenues, after provision for credit losses; includes volatile Investments and lending lines."),
    ("GS", "Compensation", "Segment comp ratio only annual FY2022-25 (ASU 2023-07 disclosure)."),
    ("BLK", "Unit", "Whole company; two CIKs stitched at 2024-10-01 (GIP/HPS acquisitions inflate acquisition-related comp from 2025)."),
    ("BLK", "Fee yield", "Base fees + securities lending revenue / average AUM ((begin+end)/2)."),
    ("BLK", "Flows", "Market/FX/acquisition movement is a RESIDUAL (end - begin - net flows); the release has no begin/market table."),
    ("BLK", "Margin", "GAAP operating margin; 'as adjusted' margin stored separately (excludes acquisition costs, comp appreciation)."),
    ("TROW", "Unit", "Whole company; revenue = investment advisory + admin/distribution fees."),
    ("TROW", "Fee yield", "Investment advisory fees / average AUM (average as reported from 2023 Q2; (begin+end)/2 earlier)."),
    ("TROW", "Margin", "GAAP net operating income / net revenues; adjusted basis excludes market-related deferred comp & acquisition items."),
    ("IVZ", "Unit", "Whole company; GAAP revenues include pass-through service/distribution fees; non-GAAP 'net revenues' stored separately."),
    ("IVZ", "Fee yield", "Investment management fees (gross, GAAP) / average AUM, not net of third-party distribution."),
    ("IVZ", "Margin", "GAAP operating income / GAAP operating revenues; adjusted operating margin on net revenues is higher."),
    ("MS", "Unit", "Investment Management segment; AUM roll-forward parsed for 2021-26 in three layouts (a few quarters missing); P&L from 2021."),
    ("MS", "Margin", "Segment income before taxes / net revenues; compensation ratio available at segment level."),
    ("JPM", "Unit", "Asset & Wealth Management segment; AUM roll-forward 2019-2026; segment P&L 2019-26 (Q4 2019-22 missing). The fee line is relabelled in 2023: 'Asset management, administration and commissions' (to 2022) became 'Asset management fees' (from 2023), a definitional break in fee yield."),
    ("JPM", "Fee yield", "Asset management fees / average AUM; segment also includes Global Private Bank (lending, deposits) so yield is not like-for-like."),
    ("BEN", "Unit", "Whole company; fiscal year ends 30 Sep but fiscal quarters end Mar/Jun/Sep/Dec, so quarterly data are already calendar-aligned. AUM jumped on the 2020 Legg Mason acquisition (in 'other')."),
    ("BEN", "Fee yield", "Investment management fees (gross) / reported average AUM; roll-forward available from 2020-Q3."),
], columns=["ticker", "topic", "note"])


def load() -> pd.DataFrame:
    con = duckdb.connect(str(DB), read_only=True)
    f = con.execute("select ticker, metric, period_end, value from fact_financials").df()
    con.close()
    f["period_end"] = pd.to_datetime(f.period_end)
    return f.pivot_table(index=["ticker", "period_end"], columns="metric", values="value", aggfunc="first")


def _col(g: pd.DataFrame, name: str) -> pd.Series:
    return g[name] if name in g else pd.Series(np.nan, index=g.index)


def build_mart() -> pd.DataFrame:
    w = load()
    out = []
    for t, g in w.groupby(level=0):
        if t not in FEE_METRIC:          # e.g. MSWM (no AUM series)
            continue
        g = g.droplevel(0).sort_index()
        g = g.reindex(pd.date_range(g.index.min(), g.index.max(), freq="QE"))
        d = pd.DataFrame(index=g.index)
        d["ticker"] = t
        d["aum_end"] = _col(g, "aum_end")
        d["aum_begin"] = _col(g, "aum_begin").fillna(d.aum_end.shift(1))
        reported_avg = _col(g, "aum_avg")
        d["aum_avg"] = reported_avg.fillna((d.aum_begin + d.aum_end) / 2)
        d["aum_avg_method"] = np.where(reported_avg.notna(), "reported", "(begin+end)/2")
        d["net_flows"] = _col(g, "net_flows")
        d["market_other"] = d.aum_end - d.aum_begin - d.net_flows
        d["fees"] = _col(g, FEE_METRIC[t])
        d["net_revenues"] = _col(g, "net_revenues")
        d["op_income"] = _col(g, OPINC_METRIC[t])
        d["opex"] = _col(g, "opex")
        d["comp"] = _col(g, "comp_total")
        d["op_income_adj"] = _col(g, "operating_income_adj")
        d["fee_yield_bps"] = d.fees * 4 / d.aum_avg * 10000
        d["organic_growth_ann"] = d.net_flows * 4 / d.aum_begin
        d["market_impact_pct"] = d.market_other / d.aum_begin
        d["op_margin"] = d.op_income / d.net_revenues
        d["comp_ratio"] = d.comp / d.net_revenues
        d["efficiency_ratio"] = d.opex / d.net_revenues
        d["fee_share_of_revenue"] = d.fees / d.net_revenues

        def r4(s):
            return s.rolling(4, min_periods=4).sum()

        d["fee_yield_t4q_bps"] = r4(d.fees) / d.aum_avg.rolling(4, min_periods=4).mean() * 10000
        d["organic_growth_t4q"] = r4(d.net_flows) / d.aum_begin.shift(3)
        d["op_margin_t4q"] = r4(d.op_income) / r4(d.net_revenues)
        d["comp_ratio_t4q"] = r4(d.comp) / r4(d.net_revenues)
        rev_yoy = d.net_revenues.pct_change(4, fill_method=None)
        opx_yoy = d.opex.pct_change(4, fill_method=None)
        d["operating_leverage_yoy"] = rev_yoy - opx_yoy
        d["revenue_yoy"] = rev_yoy
        d["aum_yoy"] = d.aum_end.pct_change(4, fill_method=None)
        out.append(d)
    return pd.concat(out).rename_axis("period_end").reset_index()


def zscores(m: pd.DataFrame) -> pd.DataFrame:
    z = m.copy()
    for c in ["fee_yield_t4q_bps", "organic_growth_t4q", "op_margin_t4q"]:
        grp = z.groupby("period_end")[c]
        z[f"z_{c}"] = (z[c] - grp.transform("mean")) / grp.transform("std")
    return z


def fee_compression(m: pd.DataFrame) -> pd.DataFrame:
    """OLS of T4Q fee yield on time (years): slope in bps/yr with HAC 95% CI."""
    rows = []
    for t, g in m.dropna(subset=["fee_yield_t4q_bps"]).groupby("ticker"):
        x = (g.period_end - g.period_end.min()).dt.days / 365.25
        res = sm.OLS(g.fee_yield_t4q_bps.values, sm.add_constant(x.values)).fit(
            cov_type="HAC", cov_kwds={"maxlags": 4})
        lo, hi = res.conf_int()[1]
        rows.append(dict(ticker=t, start=g.period_end.min().date(), end=g.period_end.max().date(), n=len(g),
                         slope_bps_per_year=res.params[1], ci_low=lo, ci_high=hi,
                         pct_per_year=res.params[1] / g.fee_yield_t4q_bps.mean() * 100,
                         significant=bool(lo > 0 or hi < 0)))
    return pd.DataFrame(rows)


def aum_decomposition(m: pd.DataFrame, since: str = "2022-03-31") -> pd.DataFrame:
    rows = []
    for t, g in m[m.period_end >= since].groupby("ticker"):
        g = g.sort_values("period_end").dropna(subset=["net_flows", "aum_begin", "aum_end"])
        begin, end, flows = g.aum_begin.iloc[0], g.aum_end.iloc[-1], g.net_flows.sum()
        rows.append(dict(ticker=t, start=g.period_end.min().date(), end=g.period_end.max().date(),
                         quarters=len(g), aum_begin=begin, aum_end=end, net_flows=flows,
                         market_fx_other=end - begin - flows,
                         organic_pct_of_begin=flows / begin,
                         market_pct_of_begin=(end - begin - flows) / begin))
    return pd.DataFrame(rows)


def run() -> dict:
    m = build_mart()
    z = zscores(m)
    fc = fee_compression(m)
    dec = aum_decomposition(m)
    con = duckdb.connect(str(DB))
    for name, df in [("mart_peer_benchmark", z), ("mart_fee_compression", fc),
                     ("mart_aum_decomposition", dec), ("comparability_flags", COMPARABILITY)]:
        con.register("x", df)
        con.execute(f"create or replace table {name} as select * from x")
        con.unregister("x")
    con.close()
    return {"fee_compression": fc, "decomp": dec, "mart": z}


if __name__ == "__main__":
    r = run()
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 30)
    print(r["fee_compression"].round(2).to_string())
    print(r["decomp"].round(3).to_string())
    mt = r["mart"]
    last = mt[mt.period_end == mt.period_end.max()]
    print(last[["ticker", "period_end", "aum_end", "fee_yield_t4q_bps", "organic_growth_t4q",
                "op_margin_t4q", "comp_ratio_t4q"]].round(3).to_string())
