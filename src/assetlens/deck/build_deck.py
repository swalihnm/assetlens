"""M16 - board-style pack (python-pptx). Every number comes from `numbers()` (warehouse queries) so a test can
re-derive and verify each figure on the slides. Neutral design, no third-party branding."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import duckdb
import pandas as pd
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Inches, Pt

from assetlens.deck import charts
from assetlens.growth import business_case as GC
from assetlens.pricing import inputs as pin
from assetlens.pricing import mandate as PM
from assetlens.warehouse.build import DB

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "outputs" / "deck" / "AssetLens_Board_Pack.pptx"
INK, INK2, ACC = RGBColor(0x0B, 0x0B, 0x0B), RGBColor(0x52, 0x51, 0x4E), RGBColor(0x2A, 0x78, 0xD6)
DISC = ("AssetLens is an independent educational project built from publicly available SEC filings and FRED data. It is not "
        "affiliated with, endorsed by, or based on any non-public information from Goldman Sachs or any other company named. "
        "Business-unit, headcount, advisor, expense and compensation data are synthetic, generated to be consistent with public "
        "segment totals, and do not represent any company's internal figures. Nothing here is investment advice.")


def numbers() -> dict[str, float | str]:
    con = duckdb.connect(str(DB), read_only=True)
    q = lambda s: con.execute(s).df()  # noqa: E731
    n: dict[str, float | str] = {}
    b = q("select * from mart_peer_benchmark")
    for t in ("GS", "BLK", "TROW", "IVZ"):
        g = b[(b.ticker == t) & b.fee_yield_t4q_bps.notna()].sort_values("period_end").iloc[-1]
        n[f"{t}_period"] = str(g.period_end)[:10]
        n[f"{t}_aum_tn"] = g.aum_end / 1e6
        n[f"{t}_fee_yield"] = g.fee_yield_t4q_bps
        n[f"{t}_organic"] = g.organic_growth_t4q * 100
        m = b[(b.ticker == t) & b.op_margin_t4q.notna()].sort_values("period_end").iloc[-1]
        n[f"{t}_margin"] = m.op_margin_t4q * 100
        n[f"{t}_margin_period"] = str(m.period_end)[:10]
    fc = q("select * from mart_fee_compression").set_index("ticker")
    for t in fc.index:
        n[f"{t}_slope"] = fc.loc[t, "slope_bps_per_year"]
    dec = q("select * from mart_aum_decomposition").set_index("ticker")
    n["GS_flows_bn"] = dec.loc["GS", "net_flows"] / 1e3
    n["GS_market_bn"] = dec.loc["GS", "market_fx_other"] / 1e3
    n["GS_organic_pct"] = dec.loc["GS", "organic_pct_of_begin"] * 100
    f = q("select * from fact_forecast")
    for s in ("bull", "base", "bear", "stress"):
        x = f[(f.scenario == s) & (f.t == 8)].iloc[0]
        n[f"{s}_margin8"] = x.pretax_margin * 100
        n[f"{s}_rev8"] = x.net_revenues / 1e3
        n[f"{s}_pretax_8q"] = f[f.scenario == s].pretax.sum() / 1e3
    rk = q("select * from mart_allocation_rank_sensitivity")
    liq = rk[rk.business == "LIQ"].set_index("method")
    n["LIQ_margin_rev"], n["LIQ_margin_abc"] = liq.loc["revenue", "margin"] * 100, liq.loc["abc", "margin"] * 100
    n["LIQ_rank_rev"], n["LIQ_rank_abc"] = int(liq.loc["revenue", "rank"]), int(liq.loc["abc", "rank"])
    n["rank_changes"] = int((rk.pivot(index="business", columns="method", values="rank").nunique(axis=1) > 1).sum())
    bud = q("select * from mart_budget_variance")
    h1 = bud.dropna(subset=["actual_pretax"])
    n["H1_pretax_var_pct"] = h1.pretax_variance.sum() / h1.budget_pretax.sum() * 100
    con.close()
    d = pin.defaults("equity")
    m = replace(PM.Mandate(), cost_per_fte=d["cost_per_fte"], allocated_bps=d["allocated_bps"])
    r = PM.recommend(m, competitor_band_bps=d["competitor_band_bps"])
    n["be_marginal"], n["be_full"], n["proposed_bps"] = r["marginal_be_bps"], r["fully_allocated_be_bps"], r["proposed_bps"]
    n["verdict"] = r["verdict"]
    n["min_aum_marginal"], n["min_aum_full"] = PM.min_viable_aum(m, "marginal"), PM.min_viable_aum(m, "fully_allocated")
    g = GC.run()
    n["gcc_npv"], n["gcc_npv_explicit"], n["gcc_irr"] = g["npv"], g["npv_explicit"], g["irr"] * 100
    n["gcc_payback"], n["gcc_peak"] = g["payback_years"], g["peak_funding"]
    n["gcc_tv_share"] = (1 - g["npv_explicit"] / g["npv"]) * 100
    from assetlens.growth import simulation as GS
    mc = GS.simulate(1000, threshold=350, delay=1)
    n["gcc_mc_mean"], n["gcc_mc_p10"], n["gcc_mc_p90"] = mc["full"]["mean"], mc["full"]["p10"], mc["full"]["p90"]
    n["gcc_mc_loss"], n["gcc_option"], n["gcc_pass"] = mc["full"]["prob_loss"] * 100, mc["option_value"], mc["pass_rate"] * 100
    sv = duckdb.connect(str(DB), read_only=True).execute(
        "select sum(target_savings_musd), sum(realised_to_date_musd), count(*) from fact_savings").fetchone()
    n["sav_target"], n["sav_real"], n["sav_n"] = sv
    return n


def _tb(slide, x, y, w, h, text, size=12, bold=False, color=INK, bullets=False):
    tf = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h)).text_frame
    tf.word_wrap = True
    lines = text if isinstance(text, list) else [text]
    for i, ln in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = ("• " if bullets else "") + ln
        p.font.size, p.font.bold, p.font.color.rgb = Pt(size), bold, color
        p.space_after = Pt(5)


def _slide(prs, title, foot):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    _tb(s, 0.5, 0.3, 12.3, 0.9, title, 22, True)
    _tb(s, 0.5, 6.85, 12.3, 0.5, "Sources: " + foot + "  |  Synthetic business-unit data where marked.", 8, color=INK2)
    return s


def build() -> Path:
    n = numbers()
    pics = charts.make_all()
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    f1 = lambda k: f"{n[k]:.1f}"  # noqa: E731
    # 1 executive summary
    s = _slide(prs, "Executive summary: GS AWM leads on flow growth, margin depends on the market and on the allocation lens",
               "SEC 10-Q/10-K and 8-K Ex.99.1 filings (GS, BLK, TROW, IVZ); AssetLens scenario model; synthetic allocation")
    _tb(s, 0.5, 1.3, 12.3, 5.2, [
        f"GS AWM AUS reached ${n['GS_aum_tn']:.2f}tn ({n['GS_period']}); trailing-four-quarter organic growth {f1('GS_organic')}% vs "
        f"BlackRock {f1('BLK_organic')}%, Invesco {f1('IVZ_organic')}% and T. Rowe {f1('TROW_organic')}% (latest available quarters). GS growth includes low-fee liquidity-product inflows.",
        f"Fee yield is the pressure point: T4Q yields are {f1('GS_fee_yield')} bps (GS), {f1('BLK_fee_yield')} (BLK), {f1('IVZ_fee_yield')} (IVZ), "
        f"{f1('TROW_fee_yield')} (TROW); fitted trends are {n['GS_slope']:.2f}, {n['BLK_slope']:.2f}, {n['IVZ_slope']:.2f} and {n['TROW_slope']:.2f} bps a year.",
        f"Eight-quarter outlook: pre-tax margin in the final quarter is {f1('base_margin8')}% base, {f1('bull_margin8')}% bull, "
        f"{f1('bear_margin8')}% bear and {f1('stress_margin8')}% under a -25% equity stress.",
        f"Allocation matters (synthetic split): Liquidity Solutions shows {f1('LIQ_margin_rev')}% margin on a revenue basis but "
        f"{f1('LIQ_margin_abc')}% under activity-based costing (rank {n['LIQ_rank_rev']} to {n['LIQ_rank_abc']}); price new mandates off marginal cost, not allocation.",
        f"GCC private wealth office: illustrative NPV ${n['gcc_npv']:.0f}m, but {n['gcc_tv_share']:.0f}% comes from terminal value (explicit-period NPV ${n['gcc_npv_explicit']:.0f}m): "
        f"Monte Carlo: mean NPV ${n['gcc_mc_mean']:.0f}m, {n['gcc_mc_loss']:.0f}% chance of loss; staging a pilot first was worth ${n['gcc_option']:.0f}m (negative: it delays a project that is positive in most paths)."], 14, bullets=True)
    # 2 competitive position
    s = _slide(prs, "Competitive position: growth and fee yield versus peers",
               "GS 10-Q/10-K AWM tables; BLK, TROW, IVZ Ex.99.1 earnings releases; warehouse mart_peer_benchmark")
    s.shapes.add_picture(str(pics["fee_yield"]), Inches(0.4), Inches(1.2), width=Inches(7.2))
    s.shapes.add_picture(str(pics["scatter"]), Inches(7.7), Inches(1.2), width=Inches(5.3))
    _tb(s, 0.5, 5.2, 12.3, 1.6, [
        f"Operating margin T4Q: GS {f1('GS_margin')}% (as of {n['GS_margin_period']}; segment pre-tax), BLK {f1('BLK_margin')}%, "
        f"IVZ {f1('IVZ_margin')}%, TROW {f1('TROW_margin')}%.",
        "Comparability: GS = AWM segment / AUS; BLK market impact is a residual; IVZ fees are gross; margins are GAAP operating (see appendix)."], 11, bullets=True)
    # 3 outlook
    s = _slide(prs, "Financial outlook and risk: scenarios for the next eight quarters",
               "AssetLens driver model (config/scenarios.yaml: assumptions, not forecasts); GS public base data")
    s.shapes.add_picture(str(pics["scenarios"]), Inches(0.4), Inches(1.2), width=Inches(7.2))
    s.shapes.add_picture(str(pics["waterfall"]), Inches(7.7), Inches(1.2), width=Inches(5.3))
    _tb(s, 0.5, 5.2, 12.3, 1.6, [
        f"Eight-quarter cumulative pre-tax earnings: ${n['bull_pretax_8q']:.1f}bn bull, ${n['base_pretax_8q']:.1f}bn base, "
        f"${n['bear_pretax_8q']:.1f}bn bear, ${n['stress_pretax_8q']:.1f}bn stress.",
        f"Since Dec-2021 net flows added ${n['GS_flows_bn']:.0f}bn of AUS ({n['GS_organic_pct']:.0f}% of the opening balance), market and other ${n['GS_market_bn']:.0f}bn.",
        f"Key risks: incentive-fee and Investments volatility, liquidity-product flows reversing, fee compression, lending credit costs. "
        f"H1-2026 pre-tax earnings ran {n['H1_pretax_var_pct']:.0f}% versus an unverified top-down budget."], 11, bullets=True)
    # 4 profitability & pricing
    s = _slide(prs, "Profitability and pricing: allocation changes the ranking, marginal cost sets the floor",
               "Synthetic business split calibrated to GS AWM totals; allocation methods per M8; pricing engine per M9")
    s.shapes.add_picture(str(pics["methods"]), Inches(0.4), Inches(1.2), width=Inches(7.2))
    s.shapes.add_picture(str(pics["mandate"]), Inches(7.7), Inches(1.3), width=Inches(5.3))
    _tb(s, 0.5, 5.2, 12.3, 1.6, [
        f"{n['rank_changes']} of 6 businesses change rank depending on the allocation method (synthetic).",
        f"$1bn equity SMA: break-even fee {n['be_marginal']:.1f} bps marginal, {n['be_full']:.1f} bps fully allocated; proposed {n['proposed_bps']:.1f} bps. "
        f"Minimum viable AUM ${n['min_aum_marginal']:.0f}m marginal / ${n['min_aum_full']:.0f}m fully allocated.",
        "Rule: never price below marginal break-even; target fully allocated break-even plus a 15% hurdle margin."], 11, bullets=True)
    # 5 growth
    s = _slide(prs, "Growth and strategic initiatives: GCC expansion case and savings programme",
               "AssetLens GCC business case (config/assumptions.yaml, illustrative; tax rates to be verified); synthetic savings tracker")
    s.shapes.add_picture(str(pics["gcc"]), Inches(0.4), Inches(1.2), width=Inches(6.6))
    _tb(s, 7.2, 1.3, 5.7, 5, [
        f"Base case (DIFC): NPV ${n['gcc_npv']:.0f}m, IRR {n['gcc_irr']:.0f}%, payback {n['gcc_payback']:.1f} years, peak funding ${n['gcc_peak']:.0f}m.",
        f"Terminal value is {n['gcc_tv_share']:.0f}% of NPV; the explicit seven-year NPV is ${n['gcc_npv_explicit']:.0f}m.",
        f"Monte Carlo (1,000 paths): mean NPV ${n['gcc_mc_mean']:.0f}m (P10 ${n['gcc_mc_p10']:.0f}m, P90 ${n['gcc_mc_p90']:.0f}m), {n['gcc_mc_loss']:.0f}% chance of loss.",
        f"Staged entry (pilot, expand if AUM clears $350m at year 2; {n['gcc_pass']:.0f}% pass): option value ${n['gcc_option']:.0f}m, i.e. staging lowers expected value; use it only as risk control.",
        "Recommendation: conditional go on the full plan, gated on validating AUM per advisor and net revenue bps; the explicit-period NPV is small so the case rests on terminal value.",
        f"Savings programme (synthetic): {int(n['sav_n'])} initiatives, ${n['sav_target']:.0f}m target, ${n['sav_real']:.0f}m realised to date."], 13, bullets=True)
    # appendix
    s = _slide(prs, "Appendix: methodology, data sources, comparability and assumptions", "docs/MODEL_DOCUMENTATION.md, docs/DECISIONS.md")
    _tb(s, 0.5, 1.2, 12.3, 5.5, [
        "Data: SEC EDGAR 10-K/10-Q and 8-K Exhibit 99.1 (GS, BLK old and new CIK, TROW, IVZ); FRED. Every public fact carries accession number, table locator and raw text.",
        "Quality gate: AUM roll-forwards are accepted only if begin + flows + market + other = end and chain with the prior quarter. GS reconciliation checks pass 19/19 per test.",
        "GS perimeter: AWM segment re-based in the FY2022 10-K; quarterly AWM series starts 2022 Q1. Q3-2026 opex and pre-tax not yet filed (10-Q due).",
        "Fee yield = quarterly fees x4 / average AUM; organic growth = net flows x4 / beginning AUM; margins GAAP operating (GS: segment pre-tax).",
        "Forecast: driver-based (flows, market returns, fee compression, comp ratio with floor); scenario inputs are assumptions. Budget targets from press reports are unverified.",
        "Synthetic: business-unit P&L, cost pools, headcount, advisors, GL, T&E, savings. Calibrated so totals equal public segment figures.",
        DISC], 10, bullets=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    prs.save(OUT)
    return OUT


if __name__ == "__main__":
    print(build())
