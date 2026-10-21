"""AssetLens Streamlit app - mirrors the eight Power BI pages. Run: streamlit run app/streamlit_app.py"""
from __future__ import annotations

from dataclasses import replace

import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st

from assetlens.growth import business_case as GC
from assetlens.pricing import inputs as pin
from assetlens.pricing import mandate as PM
from assetlens.warehouse.build import DB

DISC = ("AssetLens is an independent educational project built from publicly available SEC filings and FRED data. Not affiliated with or "
        "based on non-public information from any company named. Business-unit, headcount, advisor, expense and compensation data are "
        "synthetic. Nothing here is investment advice.")
COL = {"GS": "#2a78d6", "BLK": "#eb6834", "TROW": "#1baf7a", "IVZ": "#eda100"}

st.set_page_config(page_title="AssetLens", layout="wide")


@st.cache_data(show_spinner=False)
def q(sql: str) -> pd.DataFrame:
    con = duckdb.connect(str(DB), read_only=True)
    try:
        return con.execute(sql).df()
    finally:
        con.close()


PAGES = ["1 Executive overview", "2 Peer benchmarking", "3 P&L forecast & scenarios", "4 Profitability by business (synthetic)",
         "5 Mandate pricing", "6 Expense & savings (synthetic)", "7 Sales productivity & compensation (synthetic)", "8 Growth markets"]
page = st.sidebar.radio("Page", PAGES)
st.sidebar.caption("Data: SEC EDGAR + FRED. Synthetic where marked.")
st.title(page)

b = q("select * from mart_peer_benchmark")
b["period_end"] = pd.to_datetime(b.period_end)

if page == PAGES[0]:
    gs = b[(b.ticker == "GS")].sort_values("period_end")
    last = gs[gs.fee_yield_t4q_bps.notna()].iloc[-1]
    c = st.columns(4)
    c[0].metric("GS AUS ($tn)", f"{last.aum_end / 1e6:.2f}")
    c[1].metric("Fee yield T4Q (bps)", f"{last.fee_yield_t4q_bps:.1f}")
    c[2].metric("Organic growth T4Q", f"{last.organic_growth_t4q:.1%}")
    m = gs[gs.op_margin_t4q.notna()].iloc[-1]
    c[3].metric("Pre-tax margin T4Q", f"{m.op_margin_t4q:.1%}", help=f"as of {m.period_end:%Y-%m-%d}")
    st.plotly_chart(px.line(gs, x="period_end", y="aum_end", title="GS assets under supervision ($m)"), use_container_width=True)
    f = q("select * from fact_forecast")
    st.plotly_chart(px.line(f, x="period_end", y="pretax_margin", color="scenario", title="Forecast pre-tax margin by scenario"),
                    use_container_width=True)

elif page == PAGES[1]:
    metric = st.selectbox("Metric", ["fee_yield_t4q_bps", "organic_growth_t4q", "op_margin_t4q", "comp_ratio_t4q", "aum_end"])
    st.plotly_chart(px.line(b.dropna(subset=[metric]), x="period_end", y=metric, color="ticker", color_discrete_map=COL), use_container_width=True)
    lt = b.dropna(subset=["op_margin_t4q", "organic_growth_t4q"]).sort_values("period_end").groupby("ticker").tail(1)
    st.plotly_chart(px.scatter(lt, x="organic_growth_t4q", y="op_margin_t4q", color="ticker", text="ticker", color_discrete_map=COL,
                               title="Operating margin vs organic growth (T4Q, latest)"), use_container_width=True)
    st.subheader("Fee compression (OLS, HAC)")
    st.dataframe(q("select * from mart_fee_compression"))
    st.subheader("Comparability notes")
    st.dataframe(q("select * from comparability_flags"), use_container_width=True)
    st.subheader("Market sensitivity of AUM")
    st.dataframe(q("select * from mart_market_sensitivity"))

elif page == PAGES[2]:
    f = q("select * from fact_forecast")
    sc = st.multiselect("Scenarios", ["bull", "base", "bear", "stress"], ["base", "bear", "stress"])
    d = f[f.scenario.isin(sc)]
    st.plotly_chart(px.line(d, x="period_end", y="net_revenues", color="scenario", title="Net revenues ($m)"), use_container_width=True)
    st.plotly_chart(px.line(d, x="period_end", y="pretax", color="scenario", title="Pre-tax earnings ($m)"), use_container_width=True)
    st.subheader("Monte Carlo fan (10,000 paths)")
    fan = q("select * from mart_montecarlo_fan where metric='margin'")
    st.line_chart(fan.set_index("t")[["p10", "p50", "p90"]])
    st.caption(f"P(margin < 25% at Q8) = {q('select margin_below_threshold_q8 from mart_montecarlo_prob').iloc[0, 0]:.1%}")
    st.subheader("Budget vs actual")
    st.dataframe(q("select * from mart_budget_variance"))
    st.subheader("Backtest MAPE")
    st.dataframe(q("select * from mart_backtest_summary").pivot(index="model", columns="horizon", values="mape").style.format("{:.1%}"))

elif page == PAGES[3]:
    method = st.selectbox("Allocation method", ["revenue", "headcount", "abc", "step_down", "reciprocal"], 2)
    p = q(f"select * from mart_profitability_by_business where method='{method}'")
    last4 = sorted(p.period_end.unique())[-4:]
    t = p[p.period_end.isin(last4)].groupby("business").agg(revenue=("net_revenues", "sum"), contribution=("contribution_margin", "sum"),
                                                              allocated=("allocated_musd", "sum"), pretax=("fully_allocated_pretax", "sum"))
    t["fa_margin"] = t.pretax / t.revenue
    t["rank"] = t.fa_margin.rank(ascending=False).astype(int)
    st.dataframe(t.style.format({"fa_margin": "{:.1%}", "revenue": "{:,.0f}", "contribution": "{:,.0f}", "allocated": "{:,.0f}", "pretax": "{:,.0f}"}))
    r = q("select * from mart_allocation_rank_sensitivity")
    st.plotly_chart(px.bar(r, x="business", y="margin", color="method", barmode="group", title="Margin by allocation method (T4Q)"),
                    use_container_width=True)

elif page == PAGES[4]:
    cls = st.selectbox("Asset class", ["equity", "fixed_income", "alternatives", "liquidity"])
    d = pin.defaults(cls)
    c = st.columns(3)
    aum = c[0].number_input("Initial AUM ($m)", 50.0, 20000.0, 1000.0, 50.0)
    t1, t2, t3 = c[1].number_input("Tier 1 bps (first $250m)", 1.0, 150.0, 40.0), c[1].number_input("Tier 2 bps (to $750m)", 1.0, 150.0, 32.0), c[1].number_input("Tier 3 bps (above)", 1.0, 150.0, 24.0)
    hz = c[2].slider("Annual termination hazard", 0.01, 0.5, 0.08)
    m = replace(PM.Mandate(), asset_class=cls, initial_aum=aum, tiers=[(250.0, t1), (750.0, t2), (float("inf"), t3)], hazard_annual=hz,
                cost_per_fte=d["cost_per_fte"], allocated_bps=d["allocated_bps"])
    r = PM.recommend(m, competitor_band_bps=d["competitor_band_bps"])
    k = st.columns(4)
    k[0].metric("Proposed fee (bps)", f"{r['proposed_bps']:.1f}")
    k[1].metric("Marginal break-even", f"{r['marginal_be_bps']:.1f}")
    k[2].metric("Fully allocated break-even", f"{r['fully_allocated_be_bps']:.1f}")
    k[3].metric("Target (+15%)", f"{r['target_bps']:.1f}")
    st.info(r["verdict"] + f"  | peer fee-yield band {d['competitor_band_bps']} bps (company-level, context only)")
    grid = pd.DataFrame(PM.pricing_grid(m, [250, 500, 1000, 2000, 4000], [0.6, 0.8, 1.0, 1.2, 1.4]))
    st.plotly_chart(px.density_heatmap(grid, x="aum", y="eff_bps", z="ltv_fully_allocated", histfunc="avg", title="LTV (fully allocated, $m): fee x AUM"),
                    use_container_width=True)
    st.dataframe(pd.DataFrame(PM.tornado(m)))
    st.caption("Cost inputs (cost per FTE, allocated rate) come from the synthetic M7/M8 tables.")

elif page == PAGES[5]:
    from assetlens.expense import analytics as E
    from assetlens.expense.savings_optimizer import optimise
    st.write(E.run_exit_rate())
    bva = E.budget_vs_actual()
    st.plotly_chart(px.bar(bva.groupby("month")[["actual", "budget"]].sum().reset_index().melt("month"), x="month", y="value", color="variable",
                           barmode="group", title="Spend vs budget ($m)"), use_container_width=True)
    st.write({k: v for k, v in E.vendor_concentration().items() if k != "category_hhi"})
    st.dataframe(E.tracker_summary())
    share = st.slider("Savings goal (share of expected savings)", 0.3, 0.9, 0.6)
    cap = st.slider("Headcount-impact cap", 50, 400, 150)
    r = optimise(goal_share=share, headcount_cap=cap)
    st.write({k: v for k, v in r.items() if k != "selected"})
    st.dataframe(r["selected"])

elif page == PAGES[6]:
    k = q("select * from mart_sales_productivity")
    st.plotly_chart(px.line(k, x="period_end", y="revenue_per_advisor", color="region", title="Revenue per advisor ($m / quarter)"), use_container_width=True)
    st.plotly_chart(px.line(q("select * from mart_cohort_ramp"), x="tenure_bucket", y="revenue_per_advisor_q", color="cohort", title="Cohort ramp curves"),
                    use_container_width=True)
    st.dataframe(q("select * from mart_nna_forecast"))
    from assetlens.comp import analysis as C
    st.subheader("Compensation")
    st.dataframe(C.ratio_benchmark())
    st.dataframe(C.scenario_sensitivity())

else:
    loc = st.selectbox("Location", list(GC.CFG["locations"]))
    g = GC.run(loc)
    c = st.columns(4)
    c[0].metric("NPV incl. TV ($m)", f"{g['npv']:.0f}")
    c[1].metric("NPV explicit ($m)", f"{g['npv_explicit']:.0f}")
    c[2].metric("IRR", f"{g['irr']:.0%}")
    c[3].metric("Payback (yrs)", f"{g['payback_years']:.1f}" if g["payback_years"] else "n/a")
    d = pd.DataFrame(dict(year=g["years"], aum_end=g["aum_end"], revenue=g["revenue"], ebitda=g["ebitda"]))
    st.plotly_chart(px.bar(d, x="year", y=["revenue", "ebitda"], barmode="group", title="Revenue and EBITDA ($m)"), use_container_width=True)
    st.caption("Illustrative assumptions (config/assumptions.yaml); verify tax rates. Terminal value is most of the NPV.")

st.divider()
st.caption(DISC)
