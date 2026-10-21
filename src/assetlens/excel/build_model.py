"""M14 - AssetLens_PnL_Model.xlsx: every calculated cell is a live formula.

Blue = inputs (public data from the warehouse, or assumptions), black = formulas, green = cross-sheet links.
Inputs that come from the Python warehouse are pasted as values (they are data, not calculations).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter as L
from openpyxl.worksheet.datavalidation import DataValidation

from assetlens.forecast.engine import CFG as SC
from assetlens.forecast.engine import CLASSES, load_base

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "outputs" / "excel" / "AssetLens_PnL_Model.xlsx"
ASSUME = yaml.safe_load((ROOT / "config" / "assumptions.yaml").read_text())["growth_case"]
DISCLAIMER = ("AssetLens is an independent educational project built from publicly available SEC filings and FRED "
              "data. It is not affiliated with, endorsed by, or based on any non-public information from Goldman "
              "Sachs or any other company named. Business-unit, headcount, advisor, expense and compensation data "
              "are synthetic, generated to be consistent with public segment totals, and do not represent any "
              "company's internal figures. Nothing here is investment advice.")
BLUE, BLACK, GREEN = "0000FF", "000000", "006100"
HEAD = PatternFill("solid", fgColor="1F3864")
SECT = PatternFill("solid", fgColor="D9E1F2")
T8 = range(1, 9)
QCOLS = [L(2 + t) for t in T8]          # C..J
SCEN_PARAMS = ["equity_ret_q", "bond_ret_q", "short_rate", "org_alternatives", "org_equity", "org_fixed_income",
               "org_liquidity", "incentive_mult", "investments_mult", "provision_mult"]


def put(ws, addr, v, kind=None, fmt=None, bold=False):
    c = ws[addr]
    c.value = v
    if kind is None:
        kind = "formula" if isinstance(v, str) and v.startswith("=") else "label"
    if kind == "formula" and isinstance(v, str) and "!" in v:
        kind = "link"
    color = {"input": BLUE, "formula": BLACK, "link": GREEN, "label": BLACK}[kind]
    c.font = Font(color=color, bold=bold)
    if fmt:
        c.number_format = fmt
    return c


def header(ws, row, labels, start_col=1):
    for i, t in enumerate(labels):
        c = ws.cell(row, start_col + i, t)
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = HEAD
        c.alignment = Alignment(horizontal="center")


def section(ws, row, text, ncols=10):
    for i in range(1, ncols + 1):
        ws.cell(row, i).fill = SECT
    ws.cell(row, 1, text).font = Font(bold=True)


def qlabels(ws, row, first_col=3):
    base = pd.Timestamp(SC["start_after"])
    for t in T8:
        c = ws.cell(row, first_col + t - 1, f"Q{(base + pd.offsets.QuarterEnd(t)).quarter}-{str(base.year + (base.quarter + t - 1) // 4 - (1 if (base.quarter + t - 1) % 4 == 0 else 0))[-2:]}")
        c.font = Font(bold=True)
        c.alignment = Alignment(horizontal="center")


def widths(ws, a=38, rest=12, n=14):
    ws.column_dimensions["A"].width = a
    for i in range(2, n + 1):
        ws.column_dimensions[L(i)].width = rest


# ---------------------------------------------------------------- sheets
def sheet_inputs(wb, b):
    ws = wb.create_sheet("Inputs")
    widths(ws, 44, 14)
    put(ws, "A1", "Inputs - public base data and modelling assumptions ($ millions unless stated)", bold=True)
    header(ws, 3, ["Item", "Value", "Unit", "Source / note"])
    rows = [(4, "Base-quarter management & other fees (Q3-26)", b.mgmt_fees, "$m", "GS 8-K Ex.99.1 3Q26 (public)"),
            (5, "Base private banking & lending revenue (Q3-26)", b.pbl, "$m", "GS 8-K Ex.99.1 3Q26 (public)"),
            (6, "Investments revenue - average of last 8 quarters", b.investments_avg, "$m", "GS 10-Q/10-K AWM table (public)"),
            (7, "Incentive fees - trailing four quarters", b.incentive_t4q, "$m", "GS 10-Q/10-K (public)"),
            (8, "Average alternatives AUS - trailing four quarters", b.alt_avg_t4q, "$m", "GS (public)"),
            (9, "Provision for credit losses - avg last 4 full-P&L quarters", b.provision_avg, "$m", "GS (public)"),
            (10, "Operating expenses - avg last 4 full-P&L quarters", b.opex_avg, "$m", "GS (public)"),
            (11, "Net revenues - avg last 4 full-P&L quarters", b.netrev_avg, "$m", "GS (public)")]
    for r, a, v, u, s in rows:
        put(ws, f"A{r}", a); put(ws, f"B{r}", v, "input", "#,##0.0"); put(ws, f"C{r}", u); put(ws, f"D{r}", s)
    header(ws, 12, ["Asset class", "AUS prev (Q2-26) $m", "AUS base (Q3-26) $m", "Relative yield (x)", "Fee compression p.a.",
                    "Equity beta", "Carry / qtr", "Bond-return link (1=yes)", "Average AUS $m", "Initial annual yield"])
    for i, k in enumerate(CLASSES):
        r = 13 + i
        ac = SC["asset_classes"][k]
        put(ws, f"A{r}", k)
        put(ws, f"B{r}", b.aus_prev[k], "input", "#,##0"); put(ws, f"C{r}", b.aus[k], "input", "#,##0")
        put(ws, f"D{r}", ac["rel_yield"], "input", "0.00"); put(ws, f"E{r}", SC["fee_compression_annual"][k], "input", "0.0%")
        put(ws, f"F{r}", ac["equity_beta"], "input", "0.00"); put(ws, f"G{r}", ac["carry_q"], "input", "0.0%")
        put(ws, f"H{r}", 1 if k == "fixed_income" else 0, "input")
        put(ws, f"I{r}", f"=(B{r}+C{r})/2", fmt="#,##0"); put(ws, f"J{r}", f"=$B$18*D{r}", fmt="0.0000%")
    scal = [(18, "Fee-yield scale s (calibrates base fees)", "=B4*4/SUMPRODUCT(D13:D16,I13:I16)", "0.000000%"),
            (19, "Compensation ratio target", SC["comp_ratio_target"], "0.0%"),
            (20, "Comp fixed floor (share of base comp)", SC["comp_fixed_floor_share"], "0%"),
            (21, "Variable non-comp (% of net revenue)", SC["noncomp_variable_rate"], "0.0%"),
            (22, "Cost inflation p.a.", SC["inflation_annual"], "0.0%"),
            (23, "PBL base net interest margin", SC["pbl"]["nim0"], "0.00%"),
            (24, "PBL margin beta to short rate", SC["pbl"]["nim_beta_to_short_rate"], "0.00"),
            (25, "PBL loan growth p.a.", SC["pbl"]["loan_growth_annual"], "0.0%"),
            (26, "Base short rate r0", SC["scenarios"]["base"]["short_rate"][0], "0.00%"),
            (27, "Base-period compensation", "=B19*B11", "#,##0.0"),
            (28, "Compensation fixed floor ($m / qtr)", "=B20*B27", "#,##0.0"),
            (29, "Fixed non-comp ($m / qtr)", "=(B10-B27)-B21*B11", "#,##0.0"),
            (30, "Incentive rate (annual, on avg alternatives AUS)", "=B7/B8", "0.00%")]
    for r, a, v, f in scal:
        put(ws, f"A{r}", a)
        put(ws, f"B{r}", v, "input" if not str(v).startswith("=") else None, f)
    for q in range(4):
        put(ws, f"A{31 + q}", f"Incentive seasonality Q{q + 1}")
        put(ws, f"B{31 + q}", SC["incentive_seasonality"][q], "input", "0%")
    put(ws, "A35", "Quarter number of base quarter (Q3-26 = 3)"); put(ws, "B35", pd.Timestamp(SC["start_after"]).quarter, "input")
    put(ws, "D19", "GS FY2025 AWM segment comp / net revenues (public)")
    put(ws, "D28", "Formula"); ws.freeze_panes = "B4"
    return ws


def sheet_scenarios(wb):
    ws = wb.create_sheet("Scenarios")
    widths(ws, 26, 11, 13)
    put(ws, "A1", "Scenario selector - drives every sheet", bold=True)
    put(ws, "A2", "Selected scenario"); put(ws, "B2", "base", "input", bold=True)
    dv = DataValidation(type="list", formula1='"base,bull,bear,stress"', allow_blank=False)
    ws.add_data_validation(dv); dv.add("B2")
    header(ws, 4, ["Selected path", ""] + [f"t{t}" for t in T8])
    for i, p in enumerate(SCEN_PARAMS):
        r = 5 + i
        put(ws, f"A{r}", p)
        for c in QCOLS:
            put(ws, f"{c}{r}", f"=INDEX({c}$20:{c}$59,MATCH($B$2&\"|\"&$A{r},$L$20:$L$59,0))",
                fmt="0.0%" if i < 3 else ("0.0%" if i < 7 else "0.00"))
    header(ws, 19, ["Scenario", "Parameter"] + [f"t{t}" for t in T8] + ["", "key"])
    r = 20
    for s, d in SC["scenarios"].items():
        for p in SCEN_PARAMS:
            put(ws, f"A{r}", s); put(ws, f"B{r}", p)
            if p in ("equity_ret_q", "bond_ret_q", "short_rate"):
                vals = d[p]
            elif p.startswith("org_"):
                vals = [d["organic_annual"][p[4:]]] * 8
            else:
                vals = [d[p]] * 8
            for c, v in zip(QCOLS, vals):
                put(ws, f"{c}{r}", v, "input", "0.0%" if p.endswith(("_q", "rate")) or p.startswith("org_") else "0.00")
            put(ws, f"L{r}", f'=A{r}&"|"&B{r}')
            r += 1
    return ws


def tcols(ws, row=2):
    put(ws, f"A{row}", "t (quarters ahead)")
    for t in T8:
        put(ws, f"{QCOLS[t - 1]}{row}", t, "input")


def sheet_aum(wb):
    ws = wb.create_sheet("AUM_Rollforward")
    widths(ws, 34, 12)
    put(ws, "A1", "AUS roll-forward by asset class ($m)", bold=True)
    tcols(ws, 2)
    header(ws, 3, ["Line", "t0 (Q3-26)"] + [f"t{t}" for t in T8]); qlabels(ws, 4)
    put(ws, "A5", "Calendar quarter number")
    for c in QCOLS:
        put(ws, f"{c}5", f"=MOD(Inputs!$B$35+{c}$2-1,4)+1")
    for i, k in enumerate(CLASSES):
        r0 = 7 + 6 * i
        section(ws, r0, k, 10)
        put(ws, f"A{r0 + 1}", "Beginning AUS"); put(ws, f"A{r0 + 2}", "Market return (qtr)")
        put(ws, f"A{r0 + 3}", "Market impact"); put(ws, f"A{r0 + 4}", "Net flows"); put(ws, f"A{r0 + 5}", "Ending AUS")
        put(ws, f"B{r0 + 5}", f"=Inputs!C{13 + i}", fmt="#,##0")
        for j, c in enumerate(QCOLS):
            prev = L(2 + j)
            put(ws, f"{c}{r0 + 1}", f"={prev}{r0 + 5}", fmt="#,##0")
            put(ws, f"{c}{r0 + 2}", f"=Inputs!$F${13 + i}*Scenarios!{c}$5+Inputs!$G${13 + i}+Inputs!$H${13 + i}*Scenarios!{c}$6", fmt="0.00%")
            put(ws, f"{c}{r0 + 3}", f"={c}{r0 + 1}*{c}{r0 + 2}", fmt="#,##0")
            put(ws, f"{c}{r0 + 4}", f"=Scenarios!{c}${8 + i}/4*{c}{r0 + 1}", fmt="#,##0")
            put(ws, f"{c}{r0 + 5}", f"={c}{r0 + 1}+{c}{r0 + 3}+{c}{r0 + 4}", fmt="#,##0")
    section(ws, 31, "Total", 10)
    for r, lab, off in [(32, "Beginning AUS", 1), (33, "Net flows", 4), (34, "Market impact", 3), (35, "Ending AUS", 5)]:
        put(ws, f"A{r}", lab)
        for c in QCOLS:
            put(ws, f"{c}{r}", "=" + "+".join(f"{c}{7 + 6 * i + off}" for i in range(4)), fmt="#,##0")
    put(ws, "B35", "=" + "+".join(f"B{7 + 6 * i + 5}" for i in range(4)), fmt="#,##0")
    ws.freeze_panes = "C6"


def sheet_revenue(wb):
    ws = wb.create_sheet("Revenue")
    widths(ws, 40, 12)
    put(ws, "A1", "Revenue build ($m)", bold=True)
    tcols(ws, 2); header(ws, 3, ["Line", ""] + [f"t{t}" for t in T8]); qlabels(ws, 4)
    for i, k in enumerate(CLASSES):
        r = 5 + 3 * i
        put(ws, f"A{r}", f"{k}: average AUS"); put(ws, f"A{r + 1}", f"{k}: annual fee yield"); put(ws, f"A{r + 2}", f"{k}: management fees")
        for c in QCOLS:
            ar = 7 + 6 * i
            put(ws, f"{c}{r}", f"=(AUM_Rollforward!{c}{ar + 1}+AUM_Rollforward!{c}{ar + 5})/2", fmt="#,##0")
            put(ws, f"{c}{r + 1}", f"=Inputs!$J${13 + i}*(1-Inputs!$E${13 + i})^(0.25*{c}$2)", fmt="0.0000%")
            put(ws, f"{c}{r + 2}", f"={c}{r}*{c}{r + 1}/4", fmt="#,##0.0")
    lines = [(17, "Total management & other fees", lambda c: "=" + "+".join(f"{c}{7 + 3 * i}" for i in range(4)), "#,##0.0"),
             (18, "Incentive seasonality weight", lambda c: f"=INDEX(Inputs!$B$31:$B$34,AUM_Rollforward!{c}$5)", "0%"),
             (19, "Incentive fees", lambda c: f"=Inputs!$B$30*{c}5*{c}18*Scenarios!{c}$12", "#,##0.0"),
             (20, "Private banking & lending", lambda c: f"=Inputs!$B$5*(1+Inputs!$B$25)^({c}$2/4)*(1+Inputs!$B$24*(Scenarios!{c}$7-Inputs!$B$26)/Inputs!$B$23)", "#,##0.0"),
             (21, "Investments", lambda c: f"=Inputs!$B$6*Scenarios!{c}$13", "#,##0.0"),
             (22, "Net revenues", lambda c: f"={c}17+{c}19+{c}20+{c}21", "#,##0.0"),
             (23, "Total average AUS", lambda c: "=" + "+".join(f"{c}{5 + 3 * i}" for i in range(4)), "#,##0"),
             (24, "Effective fee yield (bps)", lambda c: f"={c}17*4/{c}23*10000", "0.00")]
    for r, lab, f, fmt in lines:
        put(ws, f"A{r}", lab, bold=(r in (17, 22)))
        for c in QCOLS:
            put(ws, f"{c}{r}", f(c), fmt=fmt)
    ws.freeze_panes = "C5"


def sheet_expenses(wb):
    ws = wb.create_sheet("Expenses")
    widths(ws, 40, 12)
    put(ws, "A1", "Expenses ($m, shown positive)", bold=True)
    tcols(ws, 2); header(ws, 3, ["Line", ""] + [f"t{t}" for t in T8]); qlabels(ws, 4)
    for r, lab, f in [(5, "Compensation = MAX(fixed floor, ratio x net revenue)", lambda c: f"=MAX(Inputs!$B$28,Inputs!$B$19*Revenue!{c}22)"),
                      (6, "Non-compensation", lambda c: f"=Inputs!$B$29*(1+Inputs!$B$22)^({c}$2/4)+Inputs!$B$21*Revenue!{c}22"),
                      (7, "Provision for credit losses", lambda c: f"=Inputs!$B$9*Scenarios!{c}$14"),
                      (8, "Total costs incl. provision", lambda c: f"=SUM({c}5:{c}7)")]:
        put(ws, f"A{r}", lab, bold=(r == 8))
        for c in QCOLS:
            put(ws, f"{c}{r}", f(c), fmt="#,##0.0")
    ws.freeze_panes = "C5"


def sheet_pnl(wb):
    ws = wb.create_sheet("PnL")
    widths(ws, 36, 12)
    put(ws, "A1", "P&L forecast - selected scenario ($m)", bold=True)
    put(ws, "A2", "Scenario:"); put(ws, "B2", "=Scenarios!B2", bold=True)
    header(ws, 3, ["Line", ""] + [f"t{t}" for t in T8] + ["Year 1", "Year 2"]); qlabels(ws, 4)
    lines = [(5, "Net revenues", lambda c: f"=Revenue!{c}22", "#,##0.0"),
             (6, "  of which investments", lambda c: f"=Revenue!{c}21", "#,##0.0"),
             (7, "Compensation", lambda c: f"=Expenses!{c}5", "#,##0.0"),
             (8, "Non-compensation", lambda c: f"=Expenses!{c}6", "#,##0.0"),
             (9, "Provision for credit losses", lambda c: f"=Expenses!{c}7", "#,##0.0"),
             (10, "Pre-tax earnings", lambda c: f"={c}5-{c}7-{c}8-{c}9", "#,##0.0"),
             (11, "Pre-tax margin", lambda c: f"={c}10/{c}5", "0.0%"),
             (12, "Core pre-tax margin (ex Investments)", lambda c: f"=({c}10-{c}6)/({c}5-{c}6)", "0.0%"),
             (13, "Compensation ratio", lambda c: f"={c}7/{c}5", "0.0%"),
             (14, "Ending AUS", lambda c: f"=AUM_Rollforward!{c}35", "#,##0")]
    for r, lab, f, fmt in lines:
        put(ws, f"A{r}", lab, bold=(r in (5, 10)))
        for c in QCOLS:
            put(ws, f"{c}{r}", f(c), fmt=fmt)
    for r in (5, 6, 7, 8, 9, 10):
        put(ws, f"K{r}", f"=SUM(C{r}:F{r})", fmt="#,##0.0"); put(ws, f"L{r}", f"=SUM(G{r}:J{r})", fmt="#,##0.0")
    for col in ("K", "L"):
        put(ws, f"{col}11", f"={col}10/{col}5", fmt="0.0%"); put(ws, f"{col}13", f"={col}7/{col}5", fmt="0.0%")
        put(ws, f"{col}12", f"=({col}10-{col}6)/({col}5-{col}6)", fmt="0.0%")
    put(ws, "A16", "Year-2 vs Year-1 net revenue growth"); put(ws, "B16", "=L5/K5-1", fmt="0.0%")
    ws.freeze_panes = "C5"


def sheet_budget(wb, py: pd.DataFrame):
    ws = wb.create_sheet("Budget_Variance")
    widths(ws, 46, 14)
    put(ws, "A1", "Budget vs forecast vs prior year; price-volume-mix fee bridge ($m)", bold=True)
    header(ws, 3, ["Prior-year quarter (T4Q with full P&L)", "Net revenues", "Pre-tax earnings"])
    for i, (lab, rv, pt) in enumerate(py.itertuples(index=False)):
        put(ws, f"A{4 + i}", lab); put(ws, f"B{4 + i}", rv, "input", "#,##0.0"); put(ws, f"C{4 + i}", pt, "input", "#,##0.0")
    put(ws, "A8", "Prior-year total", bold=True); put(ws, "B8", "=SUM(B4:B7)", fmt="#,##0.0"); put(ws, "C8", "=SUM(C4:C7)", fmt="#,##0.0")
    put(ws, "A10", "Top-down revenue growth target"); put(ws, "B10", SC["budget_targets"]["revenue_growth"], "input", "0.0%")
    put(ws, "C10", "Revenue growth 8% = AssetLens assumption (GS publishes none); 30% margin = GS 10-Q AWM target (verified)")
    put(ws, "A11", "Top-down pre-tax margin target"); put(ws, "B11", SC["budget_targets"]["pretax_margin"], "input", "0.0%")
    put(ws, "A12", "Variance threshold (%)"); put(ws, "B12", 0.05, "input", "0%")
    header(ws, 14, ["", "Prior year", "Budget (top-down)", "Forecast Year 1", "Variance vs budget", "Variance %", "Flag"])
    put(ws, "A15", "Net revenues"); put(ws, "B15", "=B8", fmt="#,##0.0"); put(ws, "C15", "=B15*(1+B10)", fmt="#,##0.0")
    put(ws, "D15", "=PnL!K5", fmt="#,##0.0")
    put(ws, "A16", "Pre-tax earnings"); put(ws, "B16", "=C8", fmt="#,##0.0"); put(ws, "C16", "=C15*B11", fmt="#,##0.0")
    put(ws, "D16", "=PnL!K10", fmt="#,##0.0")
    for r in (15, 16):
        put(ws, f"E{r}", f"=D{r}-C{r}", fmt="#,##0.0"); put(ws, f"F{r}", f"=E{r}/ABS(C{r})", fmt="0.0%")
        put(ws, f"G{r}", f'=IF(ABS(F{r})>$B$12,"REVIEW - owner commentary required","Within threshold")')
    section(ws, 19, "Price-volume-mix bridge of management fees: Year-2 Q4 (t8) vs Year-1 Q4 (t4)", 12)
    header(ws, 20, ["Asset class", "Avg AUS t4", "Fees t4", "Avg AUS t8", "Fees t8", "Yield t4", "Yield t8", "Weight t4", "Weight t8"])
    for i, k in enumerate(CLASSES):
        r = 21 + i
        rr = 5 + 3 * i
        put(ws, f"A{r}", k)
        put(ws, f"B{r}", f"=Revenue!F{rr}", fmt="#,##0"); put(ws, f"C{r}", f"=Revenue!F{rr + 2}", fmt="#,##0.0")
        put(ws, f"D{r}", f"=Revenue!J{rr}", fmt="#,##0"); put(ws, f"E{r}", f"=Revenue!J{rr + 2}", fmt="#,##0.0")
        put(ws, f"F{r}", f"=C{r}/B{r}", fmt="0.0000%"); put(ws, f"G{r}", f"=E{r}/D{r}", fmt="0.0000%")
        put(ws, f"H{r}", f"=B{r}/B$25", fmt="0.0%"); put(ws, f"I{r}", f"=D{r}/D$25", fmt="0.0%")
    put(ws, "A25", "Total", bold=True)
    for col in "BCDE":
        put(ws, f"{col}25", f"=SUM({col}21:{col}24)", fmt="#,##0.0")
    put(ws, "A27", "Volume effect = (A1-A0) x y0"); put(ws, "B27", "=(D25-B25)*SUMPRODUCT(H21:H24,F21:F24)", fmt="#,##0.0")
    put(ws, "A28", "Mix effect = A1 x sum((w1-w0) x y0)"); put(ws, "B28", "=D25*SUMPRODUCT(I21:I24-H21:H24,F21:F24)", fmt="#,##0.0")
    put(ws, "A29", "Rate effect = A1 x sum(w1 x (y1-y0))"); put(ws, "B29", "=D25*SUMPRODUCT(I21:I24,G21:G24-F21:F24)", fmt="#,##0.0")
    put(ws, "A30", "Total bridge", bold=True); put(ws, "B30", "=SUM(B27:B29)", fmt="#,##0.0")
    put(ws, "A31", "Actual change in fees"); put(ws, "B31", "=E25-C25", fmt="#,##0.0")


def sheet_profitability(wb, prof: pd.DataFrame, pub_pretax: float):
    ws = wb.create_sheet("Profitability")
    widths(ws, 34, 14)
    put(ws, "A1", "Fully allocated profitability by business - trailing four quarters ($m) - SYNTHETIC business split", bold=True)
    put(ws, "A2", "Allocation method"); put(ws, "B2", "abc", "input", bold=True)
    methods = ["revenue", "headcount", "abc", "step_down", "reciprocal"]
    dv = DataValidation(type="list", formula1='"' + ",".join(methods) + '"')
    ws.add_data_validation(dv); dv.add("B2")
    header(ws, 4, ["Business", "Revenue T4Q", "Contribution T4Q"] + methods + ["Selected allocation", "Fully allocated pre-tax",
                                                                             "Fully allocated margin", "Rank", "Contribution margin %"])
    for i, row in enumerate(prof.itertuples()):
        r = 5 + i
        put(ws, f"A{r}", row.business); put(ws, f"B{r}", row.rev_t4q, "input", "#,##0.0"); put(ws, f"C{r}", row.contrib_t4q, "input", "#,##0.0")
        for j, m in enumerate(methods):
            put(ws, f"{L(4 + j)}{r}", getattr(row, 'm_' + m), "input", "#,##0.0")
        put(ws, f"I{r}", f"=INDEX(D{r}:H{r},MATCH($B$2,$D$4:$H$4,0))", fmt="#,##0.0")
        put(ws, f"J{r}", f"=C{r}-I{r}", fmt="#,##0.0"); put(ws, f"K{r}", f"=J{r}/B{r}", fmt="0.0%")
        put(ws, f"L{r}", f"=RANK(K{r},K$5:K$10)"); put(ws, f"M{r}", f"=C{r}/B{r}", fmt="0.0%")
    put(ws, "A11", "Total", bold=True)
    for col in "BCDEFGHIJ":
        put(ws, f"{col}11", f"=SUM({col}5:{col}10)", fmt="#,##0.0")
    put(ws, "A13", "Public AWM pre-tax earnings, same four quarters"); put(ws, "B13", pub_pretax, "input", "#,##0.0")
    put(ws, "A14", "Reconciliation difference (must be 0)"); put(ws, "B14", "=J11-B13", fmt="#,##0.00")
    put(ws, "A16", "Businesses whose profit sign flips vs revenue-based method are flagged in the Python report (mart_allocation_rank_sensitivity).")


def sheet_mandate(wb, m, p):
    ws = wb.create_sheet("Mandate_Pricing")
    widths(ws, 50, 13)
    put(ws, "A1", "Mandate pricing - marginal vs fully allocated ($m; fees in bps). Cost inputs are SYNTHETIC (M7/M8).", bold=True)
    inp = [(4, "Initial AUM ($m)", m.initial_aum), (5, "Net AUM growth p.a.", m.growth_annual), (6, "Annual termination hazard", m.hazard_annual),
           (7, "Weibull shape (1 = exponential)", m.weibull_shape), (8, "Horizon (years, fixed)", 7), (9, "PM FTE", m.pm_fte),
           (10, "Client service FTE", m.service_fte), (11, "Loaded cost per FTE ($m)", m.cost_per_fte),
           (12, "Trading / execution (bps)", m.trading_bps), (13, "Custody & admin (bps)", m.custody_admin_bps),
           (14, "Data licences ($m / yr)", m.data_licence), (15, "Onboarding one-off ($m)", m.onboarding),
           (16, "Sales commission (% of first-year revenue)", m.commission_pct_first_year), (17, "Seed capital ($m)", m.seed_capital),
           (18, "Cost of capital", m.cost_of_capital), (19, "Allocated shared cost, ABC rate (bps of AUM)", m.allocated_bps),
           (20, "Discount rate", m.discount_rate), (21, "Fee schedule scale lambda (Goal Seek this to hit profit = 0)", 1.0)]
    for r, a, v in inp:
        put(ws, f"A{r}", a); put(ws, f"B{r}", v, "input", "0.0000" if r in (5, 6, 16, 18, 20) else "#,##0.00")
    put(ws, "A22", "Weibull scale (from hazard)"); put(ws, "B22", "=1/(-LN(1-B6))^(1/B7)", fmt="0.0000")
    header(ws, 23, ["Fee tiers: lower bound $m", "Upper bound $m", "bps"])
    lo = 0.0
    for i, (hi, bps) in enumerate(m.tiers):
        put(ws, f"A{24 + i}", lo, "input"); put(ws, f"B{24 + i}", 1e12 if hi == float("inf") else hi, "input"); put(ws, f"C{24 + i}", bps, "input")
        lo = hi
    header(ws, 28, ["Year", ""] + [str(t) for t in range(1, 8)])
    yc = [L(2 + t) for t in range(1, 8)]
    put(ws, "A29", "t")
    for t, c in enumerate(yc, 1):
        put(ws, f"{c}29", t, "input")
    rows = {30: "End AUM", 31: "Start AUM", 32: "Average AUM", 33: "Revenue at lambda=1", 34: "Revenue (scaled)", 35: "People cost",
            36: "Trading + custody", 37: "Data licences", 38: "Sales commission", 39: "Capital charge", 40: "Direct costs",
            41: "Allocated shared costs", 42: "Marginal (contribution) profit", 43: "Fully allocated profit",
            44: "Survival S(t-0.5)", 45: "Discount factor", 46: "PV marginal", 47: "PV fully allocated",
            48: "Direct costs excl. commission"}
    for r, lab in rows.items():
        put(ws, f"A{r}", lab, bold=r in (42, 43))
    for j, c in enumerate(yc):
        put(ws, f"{c}30", f"=$B$4*(1+$B$5)^{c}29", fmt="#,##0.0")
        put(ws, f"{c}31", f"={L(2 + j)}30" if j else "=$B$4", fmt="#,##0.0")
        put(ws, f"{c}32", f"=({c}30+{c}31)/2", fmt="#,##0.0")
        put(ws, f"{c}33", f"=SUMPRODUCT(({c}32>$A$24:$A$26)*(({c}32<$B$24:$B$26)*{c}32+({c}32>=$B$24:$B$26)*$B$24:$B$26-$A$24:$A$26)*$C$24:$C$26)/10000", fmt="#,##0.000")
        put(ws, f"{c}34", f"=$B$21*{c}33", fmt="#,##0.000")
        put(ws, f"{c}35", f"=($B$9+$B$10)*$B$11*1.03^({c}29-1)", fmt="#,##0.000")
        put(ws, f"{c}36", f"={c}32*($B$12+$B$13)/10000", fmt="#,##0.000")
        put(ws, f"{c}37", "=$B$14", fmt="#,##0.000")
        put(ws, f"{c}38", f"=IF({c}29=1,$B$16*{c}34,0)", fmt="#,##0.000")
        put(ws, f"{c}39", "=$B$17*$B$18", fmt="#,##0.000")
        put(ws, f"{c}40", f"=SUM({c}35:{c}39)", fmt="#,##0.000")
        put(ws, f"{c}41", f"={c}32*$B$19/10000", fmt="#,##0.000")
        put(ws, f"{c}42", f"={c}34-{c}40", fmt="#,##0.000"); put(ws, f"{c}43", f"={c}42-{c}41", fmt="#,##0.000")
        put(ws, f"{c}44", f"=EXP(-(({c}29-0.5)/$B$22)^$B$7)", fmt="0.0000")
        put(ws, f"{c}45", f"=(1+$B$20)^-({c}29-0.5)", fmt="0.0000")
        put(ws, f"{c}46", f"={c}44*{c}45*{c}42", fmt="#,##0.000"); put(ws, f"{c}47", f"={c}44*{c}45*{c}43", fmt="#,##0.000")
        put(ws, f"{c}48", f"={c}35+{c}36+{c}37+{c}39", fmt="#,##0.000")
    section(ws, 50, "Outputs", 9)
    outs = [(51, "Lifetime value - marginal ($m)", "=SUM(C46:I46)-B15", "#,##0.000"),
            (52, "Lifetime value - fully allocated ($m)", "=SUM(C47:I47)-B15", "#,##0.000"),
            (53, "Proposed effective fee, year 1 (bps)", "=C34/C32*10000", "0.00"),
            (54, "Break-even lambda, marginal (year 1)", "=C48/(C33*(1-B16))", "0.0000"),
            (55, "Break-even lambda, fully allocated (year 1)", "=(C48+C41)/(C33*(1-B16))", "0.0000"),
            (56, "Break-even fee, marginal (bps, year 1)", "=B54*C33/C32*10000", "0.00"),
            (57, "Break-even fee, fully allocated (bps, year 1)", "=B55*C33/C32*10000", "0.00"),
            (58, "Hurdle margin over fully allocated break-even", 0.15, "0%"),
            (59, "Target fee (bps)", "=B57*(1+B58)", "0.00"),
            (60, "Lifetime break-even lambda, marginal", "=(B15+SUMPRODUCT(C44:I44,C45:I45,C48:I48))/(SUMPRODUCT(C44:I44,C45:I45,C33:I33)-C44*C45*B16*C33)", "0.0000"),
            (61, "Lifetime break-even lambda, fully allocated", "=(B15+SUMPRODUCT(C44:I44,C45:I45,C48:I48+C41:I41))/(SUMPRODUCT(C44:I44,C45:I45,C33:I33)-C44*C45*B16*C33)", "0.0000"),
            (62, "Lifetime break-even fee, marginal (bps)", "=B60*C33/C32*10000", "0.00"),
            (63, "Lifetime break-even fee, fully allocated (bps)", "=B61*C33/C32*10000", "0.00"),
            (64, "Recommendation", '=IF(B53<B56,"REJECT - below marginal break-even",IF(B53<B57,"EXCEPTION ONLY - covers marginal not fully allocated",IF(B53<B59,"APPROVE WITH CAUTION","APPROVE - meets hurdle")))', None)]
    for r, a, f, fmt in outs:
        put(ws, f"A{r}", a, bold=(r == 64))
        put(ws, f"B{r}", f, "input" if r == 58 else None, fmt)
    put(ws, "A66", "Competitor fee-yield band (bps, T4Q peers, company level - context only)")
    put(ws, "B66", p["competitor_band_bps"][0], "input", "0.0"); put(ws, "C66", p["competitor_band_bps"][1], "input", "0.0")


def sheet_growth(wb):
    A = ASSUME
    ws = wb.create_sheet("Growth_Case")
    widths(ws, 46, 12)
    put(ws, "A1", "Growth Markets: GCC private wealth office - 7-year business case ($m). ILLUSTRATIVE assumptions.", bold=True)
    put(ws, "A2", "Location"); put(ws, "B2", A["base_location"], "input", bold=True)
    dv = DataValidation(type="list", formula1='"' + ",".join(A["locations"]) + '"')
    ws.add_data_validation(dv); dv.add("B2")
    header(ws, 4, ["Location", "Cost index", "Set-up capex", "Licence $m/yr", "Tax rate", "Note (VERIFY tax)"])
    for i, (loc, d) in enumerate(A["locations"].items()):
        r = 5 + i
        put(ws, f"A{r}", loc); put(ws, f"B{r}", d["cost_index"], "input"); put(ws, f"C{r}", d["setup_capex_musd"], "input")
        put(ws, f"D{r}", d["licence_musd_yr"], "input"); put(ws, f"E{r}", d["tax_rate"], "input", "0%"); put(ws, f"F{r}", d["note"])
    sel = [(9, "Selected cost index", "=INDEX(B5:B7,MATCH(B2,A5:A7,0))"), (10, "Selected set-up capex", "=INDEX(C5:C7,MATCH(B2,A5:A7,0))"),
           (11, "Selected licence $m/yr", "=INDEX(D5:D7,MATCH(B2,A5:A7,0))"), (12, "Selected tax rate", "=INDEX(E5:E7,MATCH(B2,A5:A7,0))")]
    for r, a, f in sel:
        put(ws, f"A{r}", a); put(ws, f"B{r}", f)
    par = [(14, "Advisor attrition p.a.", A["advisor_attrition"]), (15, "Support staff per advisor", A["support_per_advisor"]),
           (16, "Core staff (fixed)", A["core_staff"]), (17, "Mature AUM per advisor ($m)", A["mature_aum_per_advisor_musd"]),
           (18, "Ramp midpoint (years)", A["ramp_midpoint_years"]), (19, "Ramp steepness", A["ramp_steepness"]),
           (20, "Client attrition p.a.", A["client_attrition"]), (21, "Net revenue (bps of AUM)", A["net_revenue_bps"]),
           (22, "Advisor cost ($m)", A["advisor_cost_musd"]), (23, "Support cost ($m)", A["support_cost_musd"]),
           (24, "Premises & tech per head ($m)", A["premises_tech_per_head_musd"]), (25, "Cost inflation", A["cost_inflation"]),
           (26, "Regulatory capital ($m)", A["regulatory_capital_musd"]), (27, "Discount rate", A["discount_rate"]),
           (28, "Terminal growth", A["terminal_growth"]), (29, "Variable comp (% of revenue)", A["variable_comp_pct_of_revenue"])]
    for r, a, v in par:
        put(ws, f"A{r}", a); put(ws, f"B{r}", v, "input")
    yc = [L(2 + t) for t in range(1, 8)]            # C..I = years 1..7 ; B = year 0
    header(ws, 31, ["Year", "0"] + [str(t) for t in range(1, 8)])
    put(ws, "A32", "Gross advisor hires")
    for t, c in enumerate(yc):
        put(ws, f"{c}32", A["advisors_hired"][t], "input")
    put(ws, "A33", "Year index")
    for t, c in enumerate(yc, 1):
        put(ws, f"{c}33", t, "input")
    section(ws, 35, "Advisors alive by hire cohort (rows) and year (columns)", 9)
    section(ws, 44, "Client AUM at year end by cohort ($m)", 9)
    for h, hc in enumerate(yc):
        r1, r2 = 36 + h, 45 + h
        put(ws, f"A{r1}", f"Cohort hired Y{h + 1}"); put(ws, f"A{r2}", f"Cohort hired Y{h + 1}")
        for t, tc in enumerate(yc):
            if t >= h:
                put(ws, f"{tc}{r1}", f"={hc}$32*(1-$B$14)^({tc}$33-{hc}$33)", fmt="0.00")
                put(ws, f"{tc}{r2}", f"={tc}{r1}*$B$17/(1+EXP(-$B$19*(({tc}$33-{hc}$33+0.5)-$B$18)))*(1-$B$20)^({tc}$33-{hc}$33)", fmt="#,##0.0")
            else:
                put(ws, f"{tc}{r1}", 0, "input"); put(ws, f"{tc}{r2}", 0, "input")
    lines = {54: "Advisors", 55: "Support headcount", 56: "AUM start", 57: "AUM end", 58: "Average AUM", 59: "Net revenue",
             60: "Inflation factor", 61: "Compensation (fixed) ", 62: "Variable comp", 63: "Premises, tech & licence",
             64: "EBITDA", 65: "Tax", 66: "Free cash flow", 67: "Cumulative FCF", 68: "Discount factor", 69: "Discounted cumulative FCF",
             70: "Payback crossing (year)", 71: "Discounted payback crossing", 72: "EBITDA > 0 flag"}
    for r, lab in lines.items():
        put(ws, f"A{r}", lab, bold=r in (59, 64, 66))
    put(ws, "B66", "=-(B10+B26)", fmt="#,##0.0"); put(ws, "B67", "=B66", fmt="#,##0.0")
    put(ws, "B68", 1, "input"); put(ws, "B69", "=B66", fmt="#,##0.0"); put(ws, "B57", 0, "input")
    for t, c in enumerate(yc):
        p = L(2 + t)
        put(ws, f"{c}54", f"=SUM({c}36:{c}42)", fmt="0.0")
        put(ws, f"{c}55", f"={c}54*$B$15+$B$16", fmt="0.0")
        put(ws, f"{c}56", f"={p}57", fmt="#,##0.0")
        put(ws, f"{c}57", f"=SUM({c}45:{c}51)", fmt="#,##0.0")
        put(ws, f"{c}58", f"=({c}56+{c}57)/2", fmt="#,##0.0")
        put(ws, f"{c}59", f"={c}58*$B$21/10000", fmt="#,##0.0")
        put(ws, f"{c}60", f"=(1+$B$25)^({c}33-1)", fmt="0.000")
        put(ws, f"{c}61", f"=({c}54*$B$22+{c}55*$B$23)*$B$9*{c}60", fmt="#,##0.0")
        put(ws, f"{c}62", f"={c}59*$B$29", fmt="#,##0.0")
        put(ws, f"{c}63", f"=({c}54+{c}55)*$B$24*$B$9*{c}60+$B$11", fmt="#,##0.0")
        put(ws, f"{c}64", f"={c}59-{c}61-{c}62-{c}63", fmt="#,##0.0")
        put(ws, f"{c}65", f"=MAX({c}64,0)*$B$12", fmt="#,##0.0")
        put(ws, f"{c}66", f"={c}64-{c}65" + ("+$B$26" if t == 6 else ""), fmt="#,##0.0")
        put(ws, f"{c}67", f"={p}67+{c}66", fmt="#,##0.0")
        put(ws, f"{c}68", f"=(1+$B$27)^-{c}33", fmt="0.0000")
        put(ws, f"{c}69", f"={p}69+{c}66*{c}68", fmt="#,##0.0")
        put(ws, f"{c}70", f'=IF(AND({p}67<0,{c}67>=0),{c}33-1+(-{p}67)/({c}67-{p}67),"")', fmt="0.00")
        put(ws, f"{c}71", f'=IF(AND({p}69<0,{c}69>=0),{c}33-1+(-{p}69)/({c}69-{p}69),"")', fmt="0.00")
        put(ws, f"{c}72", f"=IF({c}64>0,1,0)")
    section(ws, 74, "Valuation outputs", 9)
    outs = [(75, "Terminal value (Gordon growth, year 7)", "=(I64-I65)*(1+B28)/(B27-B28)", "#,##0.0"),
            (76, "NPV explicit period ($m)", "=B66+NPV(B27,C66:I66)", "#,##0.0"),
            (77, "NPV incl. terminal value ($m)", "=B76+B75/(1+B27)^7", "#,##0.0"),
            (78, "IRR incl. terminal value", "=IRR(B79:I79)", "0.0%"),
            (80, "Payback (years)", '=IF(COUNT(C70:I70)=0,"n/a",MIN(C70:I70))', "0.00"),
            (81, "Discounted payback (years)", '=IF(COUNT(C71:I71)=0,"n/a",MIN(C71:I71))', "0.00"),
            (82, "Break-even year (first EBITDA > 0)", '=IF(SUM(C72:I72)=0,"n/a",MATCH(1,C72:I72,0))', "0"),
            (83, "Peak funding requirement ($m)", "=-MIN(B67:I67)", "#,##0.0"),
            (84, "Share of NPV from terminal value", "=1-B76/B77", "0%")]
    for r, a, f, fmt in outs:
        put(ws, f"A{r}", a, bold=r in (77, 78)); put(ws, f"B{r}", f, fmt=fmt)
    put(ws, "A79", "FCF stream incl. terminal value (for IRR)")
    put(ws, "B79", "=B66", fmt="#,##0.0")
    for t, c in enumerate(yc):
        put(ws, f"{c}79", f"={c}66" + ("+B75" if t == 6 else ""), fmt="#,##0.0")


def sheet_sensitivity(wb):
    ws = wb.create_sheet("Sensitivity")
    widths(ws, 40, 12)
    put(ws, "A1", "First-order sensitivity of Year-2 Q4 (t8) pre-tax earnings to fee yield and equity-market shock ($m)", bold=True)
    put(ws, "A2", "Approximation: dRev = fees x dYield + shock x sum(fees_k x beta_k); dPreTax = dRev x (1 - comp ratio - variable non-comp). Valid while the comp floor is not binding.")
    put(ws, "A4", "Pre-tax t8 (model)"); put(ws, "B4", "=PnL!J10", fmt="#,##0.0")
    put(ws, "A5", "Management fees t8"); put(ws, "B5", "=Revenue!J17", fmt="#,##0.0")
    put(ws, "A6", "Equity-beta-weighted fees t8"); put(ws, "B6", "=Revenue!J7*Inputs!F13+Revenue!J10*Inputs!F14+Revenue!J13*Inputs!F15+Revenue!J16*Inputs!F16", fmt="#,##0.0")
    put(ws, "A7", "Pre-tax flow-through (1 - comp ratio - variable non-comp)"); put(ws, "B7", "=1-Inputs!B19-Inputs!B21", fmt="0.0%")
    header(ws, 9, ["Fee-yield change  \\  equity shock"] + [""] * 5)
    shocks = [-0.20, -0.10, 0.0, 0.10, 0.20]
    for j, s in enumerate(shocks):
        put(ws, f"{L(2 + j)}9", s, "input", "0%")
    for i, dy in enumerate([-0.10, -0.05, 0.0, 0.05, 0.10]):
        r = 10 + i
        put(ws, f"A{r}", dy, "input", "0%")
        for j in range(5):
            c = L(2 + j)
            put(ws, f"{c}{r}", f"=$B$4+($B$5*$A{r}+{c}$9*$B$6)*$B$7", fmt="#,##0.0")


def sheet_benchmarks(wb, bm: pd.DataFrame):
    ws = wb.create_sheet("Benchmarks")
    widths(ws, 16, 16, 12)
    put(ws, "A1", "Peer benchmarks - latest quarter with data, trailing-four-quarter basis. Pasted from the warehouse (mart_peer_benchmark).", bold=True)
    cols = ["Ticker", "Period", "AUM/AUS $m", "Fee yield T4Q (bps)", "Organic growth T4Q", "Op margin T4Q", "Comp ratio T4Q"]
    header(ws, 3, cols + ["z fee yield", "z organic", "z margin"])
    for i, r in enumerate(bm.itertuples()):
        row = 4 + i
        put(ws, f"A{row}", r.ticker); put(ws, f"B{row}", str(r.period_end)[:10], "input")
        for j, (v, f) in enumerate([(r.aum_end, "#,##0"), (r.fee_yield_t4q_bps, "0.0"), (r.organic_growth_t4q, "0.0%"),
                                    (r.op_margin_t4q, "0.0%"), (r.comp_ratio_t4q, "0.0%")]):
            if pd.notna(v):
                put(ws, f"{L(3 + j)}{row}", float(v), "input", f)
        n = 3 + len(bm)
        for k, col in enumerate("DEF"):
            put(ws, f"{L(8 + k)}{row}", f'=IF(ISNUMBER({col}{row}),({col}{row}-AVERAGE({col}$4:{col}${n}))/STDEV({col}$4:{col}${n}),"")', fmt="0.00")
    put(ws, f"A{6 + len(bm)}", "Comparability: see warehouse table comparability_flags. GS = AWM segment/AUS; BLK = whole firm, residual market; IVZ gross fees; margins are GAAP-operating.")


def sheet_checks(wb):
    ws = wb.create_sheet("Checks")
    widths(ws, 70, 16)
    put(ws, "A1", "Model integrity checks - every value must be 0", bold=True)
    header(ws, 3, ["Check", "Value (0 = pass)"])
    checks = [
        ("AUS roll-forward closes in every quarter", "=SUMPRODUCT(ABS(AUM_Rollforward!C35:J35-AUM_Rollforward!C32:J32-AUM_Rollforward!C33:J33-AUM_Rollforward!C34:J34))"),
        ("Fee-yield calibration reproduces base-quarter fees", "=ABS(Inputs!B4-SUMPRODUCT(Inputs!I13:I16,Inputs!J13:J16)/4)"),
        ("Net revenue = fees + incentive + PBL + investments", "=SUMPRODUCT(ABS(Revenue!C22:J22-Revenue!C17:J17-Revenue!C19:J19-Revenue!C20:J20-Revenue!C21:J21))"),
        ("Pre-tax = revenue - comp - non-comp - provision", "=SUMPRODUCT(ABS(PnL!C10:J10-PnL!C5:J5+Expenses!C8:J8))"),
        ("Costs are non-negative (sign convention)", "=SUMPRODUCT(--(Expenses!C5:J8<0))"),
        ("Compensation never below the fixed floor", "=SUMPRODUCT(--(Expenses!C5:J5<Inputs!B28-0.000001))"),
        ("Price-volume-mix effects sum to the fee change", "=ABS(Budget_Variance!B30-Budget_Variance!B31)"),
        ("Fully allocated pre-tax reconciles to the public segment", "=ABS(Profitability!B14)"),
        ("Mandate: profit is zero at the year-1 marginal break-even fee", "=ABS(Mandate_Pricing!B54*Mandate_Pricing!C33*(1-Mandate_Pricing!B16)-Mandate_Pricing!C48)"),
        ("Mandate: profit is zero at the year-1 fully allocated break-even fee", "=ABS(Mandate_Pricing!B55*Mandate_Pricing!C33*(1-Mandate_Pricing!B16)-Mandate_Pricing!C48-Mandate_Pricing!C41)"),
        ("Growth case: NPV at the IRR is zero", "=ABS(Growth_Case!B66+NPV(Growth_Case!B78,Growth_Case!C79:I79))"),
        ("Scenario selector is a valid scenario name", "=IF(COUNTIF(Scenarios!A20:A59,Scenarios!B2)>0,0,1)"),
        ("Growth-case location is valid", "=IF(COUNTIF(Growth_Case!A5:A7,Growth_Case!B2)>0,0,1)"),
    ]
    for i, (a, f) in enumerate(checks):
        put(ws, f"A{4 + i}", a); put(ws, f"B{4 + i}", f, fmt="0.000000")
    n = 3 + len(checks)
    put(ws, f"A{n + 2}", "Number of checks"); put(ws, f"B{n + 2}", len(checks), "input")
    put(ws, f"A{n + 3}", "Sum of absolute check values", bold=True); put(ws, f"B{n + 3}", f"=SUMPRODUCT(ABS(B4:B{n}))", fmt="0.000000")
    return n + 3


def sheet_cover(wb, master_row):
    ws = wb["Cover"]
    widths(ws, 30, 80, 2)
    put(ws, "A1", "AssetLens - Asset & Wealth Management P&L, profitability and pricing model", bold=True)
    ws["A1"].font = Font(bold=True, size=14)
    put(ws, "A3", "Version"); put(ws, "B3", "1.0 (Phase 1) - built " + pd.Timestamp.now().strftime("%Y-%m-%d"))
    put(ws, "A4", "Master check"); put(ws, "B4", f'=IF(Checks!B{master_row}<0.001,"ALL CHECKS PASS","CHECK FAILURE - see Checks sheet")', bold=True)
    put(ws, "A5", "Scenario"); put(ws, "B5", "=Scenarios!B2")
    put(ws, "A7", "Purpose"); put(ws, "B7", "Driver-based 8-quarter P&L forecast of the GS AWM segment under bull/base/bear/stress scenarios, with budget variance, fully allocated profitability, mandate pricing and a GCC expansion case.")
    put(ws, "A8", "Colour code"); put(ws, "B8", "Blue = input / pasted data; black = formula; green = link to another sheet.")
    put(ws, "A9", "Sheets"); put(ws, "B9", "Inputs · Scenarios · AUM_Rollforward · Revenue · Expenses · PnL · Budget_Variance · Profitability · Mandate_Pricing · Growth_Case · Sensitivity · Benchmarks · Checks")
    put(ws, "A10", "Sign convention"); put(ws, "B10", "Revenues positive; costs shown positive in Expenses and subtracted in PnL; $ millions unless stated.")
    put(ws, "A12", "Disclaimer", bold=True)
    c = put(ws, "B12", DISCLAIMER)
    c.alignment = Alignment(wrap_text=True, vertical="top")
    ws.row_dimensions[12].height = 120
    for r in (7, 9):
        ws[f"B{r}"].alignment = Alignment(wrap_text=True, vertical="top")
        ws.row_dimensions[r].height = 48


def build() -> Path:
    import duckdb

    from assetlens.pricing import inputs as pin
    from assetlens.pricing import mandate as PM
    from assetlens.warehouse.build import DB

    b = load_base()
    con = duckdb.connect(str(DB), read_only=True)
    gs = con.execute("select period_end, metric, value from fact_financials where ticker='GS' and metric in ('net_revenues','pretax_earnings')").df()
    pw = gs.pivot_table(index="period_end", columns="metric", values="value", aggfunc="first").sort_index().dropna()
    py = pw.iloc[-4:]
    py_tbl = pd.DataFrame({"lab": [f"Q ending {d}" for d in py.index], "rev": py.net_revenues.values, "pt": py.pretax_earnings.values})
    alloc = con.execute("""select business, method, sum(allocated_musd) a from fact_allocation
                           where period_end in (select distinct period_end from fact_business_pnl order by 1 desc limit 4)
                           group by 1,2""").df().pivot(index="business", columns="method", values="a").add_prefix("m_")
    pnl4 = con.execute("""select business, sum(net_revenues) rev_t4q, sum(contribution_margin) contrib_t4q from fact_business_pnl
                          where period_end in (select distinct period_end from fact_business_pnl order by 1 desc limit 4)
                          group by 1""").df().set_index("business")
    prof = pnl4.join(alloc).reset_index()
    pub_pt = float(gs[(gs.metric == "pretax_earnings")].sort_values("period_end").tail(4).value.sum())
    bm = con.execute("""select * from mart_peer_benchmark where fee_yield_t4q_bps is not null qualify
                        row_number() over (partition by ticker order by period_end desc)=1 order by ticker""").df()
    con.close()
    d = pin.defaults("equity")
    from dataclasses import replace
    m = replace(PM.Mandate(), cost_per_fte=d["cost_per_fte"], allocated_bps=d["allocated_bps"])
    rec = dict(competitor_band_bps=d["competitor_band_bps"])

    wb = Workbook()
    wb.active.title = "Cover"
    sheet_inputs(wb, b); sheet_scenarios(wb); sheet_aum(wb); sheet_revenue(wb); sheet_expenses(wb); sheet_pnl(wb)
    sheet_budget(wb, py_tbl); sheet_profitability(wb, prof, pub_pt); sheet_mandate(wb, m, rec); sheet_growth(wb)
    sheet_sensitivity(wb); sheet_benchmarks(wb, bm)
    master = sheet_checks(wb)
    sheet_cover(wb, master)
    wb.calculation.fullCalcOnLoad = True
    OUT.parent.mkdir(parents=True, exist_ok=True)
    wb.save(OUT)
    return OUT


if __name__ == "__main__":
    print(build())
