"""Auto-generate RECONCILIATION_REPORT.md, DATA_DICTIONARY.md and ASSUMPTIONS_REGISTER.csv from the warehouse/config."""
from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd
import yaml

from assetlens.extract import consolidate as C
from assetlens.warehouse.build import DB, INT

ROOT = Path(__file__).resolve().parents[3]


def reconciliation_report() -> str:
    cur = pd.read_csv(INT / "gs_facts_latest.csv")
    w = C.quarterly(cur)
    rec = C.reconcile(w)
    s = rec.groupby("check").passed.agg(passed="sum", total="count").reset_index()
    lines = ["# Reconciliation report (auto-generated)", "",
             f"_Generated {pd.Timestamp.now():%Y-%m-%d %H:%M}. GS AWM perimeter, {len(w)} quarters._", "",
             "## GS segment checks", "", "| Check | Passed | Total |", "|---|---|---|"]
    lines += [f"| {r.check} | {r.passed} | {r.total} |" for r in s.itertuples()]
    bad = rec[~rec.passed]
    lines += ["", f"Failures: **{len(bad)}**" + ("" if bad.empty else "") ]
    for r in bad.itertuples():
        lines.append(f"- {r.check} {r.period_end}: {r.detail}")
    con = duckdb.connect(str(DB), read_only=True)
    f = con.execute("select ticker, metric, period_end, value from fact_financials where metric in ('aum_begin','aum_end','net_flows','market','aum_other_change','acquisitions')").df()
    con.close()
    lines += ["", "## Peer AUM roll-forwards (closure and chaining)", "", "| Ticker | Quarters with roll-forward | Closing | Chaining breaks |", "|---|---|---|---|"]
    for t, g in f.groupby("ticker"):
        p = g.pivot_table(index="period_end", columns="metric", values="value", aggfunc="first").sort_index()
        if "aum_begin" not in p:
            p["aum_begin"] = float("nan")
        p["aum_begin"] = p.aum_begin.fillna(p.aum_end.shift(1))
        p = p.dropna(subset=["aum_begin", "aum_end"])
        acq = (p["aum_other_change"].fillna(0) if "aum_other_change" in p else 0) + (p["acquisitions"].fillna(0) if "acquisitions" in p else 0)
        mk = p["market"].fillna(0) if "market" in p else 0
        fl = p["net_flows"].fillna(0) if "net_flows" in p else 0
        closing = int(((p.aum_begin + fl + mk + acq - p.aum_end).abs() <= 0.0006 * p.aum_end + 400).sum())
        br = int(((p.aum_begin - p.aum_end.shift(1)).abs() > 0.001 * p.aum_end).iloc[1:].sum())
        lines.append(f"| {t} | {len(p)} | {'n/a (residual)' if t == 'BLK' else closing} | {br} |")
    lines += ["", "BLK has no begin/market table in its releases; its roll-forward is begin = prior end and market = residual, so closure is true by construction. "
              "TROW 2020-Q3 and 2021-Q4 roll-forwards are missing (see DATA_GAPS.md). Chaining breaks around missing quarters are expected.",
              "", "## Restatements", "", f"GS restatement log rows: {len(pd.read_csv(INT / 'gs_restatement_log.csv'))} (see `restatement_log` table)."]
    return "\n".join(lines) + "\n"


def data_dictionary() -> str:
    con = duckdb.connect(str(DB), read_only=True)
    tabs = con.execute("select table_name from information_schema.tables where table_schema='main' order by 1").df().table_name
    lines = ["# Data dictionary (auto-generated from DuckDB)", "", "Tables flagged **synthetic** carry a `synthetic = true` column.", ""]
    for t in tabs:
        cols = con.execute(f"describe {t}").df()
        n = con.execute(f"select count(*) from {t}").fetchone()[0]
        syn = " - **synthetic**" if "synthetic" in set(cols.column_name) else ""
        lines += [f"## {t}{syn}", f"{n:,} rows", "", "| Column | Type |", "|---|---|"]
        lines += [f"| {r.column_name} | {r.column_type} |" for r in cols.itertuples()]
        lines.append("")
    con.close()
    return "\n".join(lines)


def assumptions_register() -> pd.DataFrame:
    rows = []
    sc = yaml.safe_load((ROOT / "config" / "scenarios.yaml").read_text())
    ga = yaml.safe_load((ROOT / "config" / "assumptions.yaml").read_text())["growth_case"]
    sy = yaml.safe_load((ROOT / "config" / "synthetic.yaml").read_text())

    def add(name, val, unit, src, why, owner="Abdulla Swalih NM", rank=""):
        rows.append(dict(id=f"A{len(rows) + 1:03d}", assumption=name, value=val, unit=unit, source=src, rationale=why, owner=owner, sensitivity_rank=rank))

    add("Comp ratio target", sc["comp_ratio_target"], "% net revenue", "GS FY2025 10-K segment comp / net revenues (public)", "Latest annual segment disclosure", rank=1)
    add("Comp fixed floor share", sc["comp_fixed_floor_share"], "share of base comp", "assumption", "Fixed salary component", rank=6)
    add("Variable non-comp rate", sc["noncomp_variable_rate"], "% net revenue", "assumption", "Transaction-linked costs", rank=5)
    add("Cost inflation", sc["inflation_annual"], "p.a.", "assumption (CPI context from FRED)", "Non-comp growth", rank=7)
    for k, v in sc["asset_classes"].items():
        add(f"Relative fee yield {k}", v["rel_yield"], "x", "assumption", "GS discloses total fees only; relative yields calibrated to base fees", rank=3)
    for k, v in sc["fee_compression_annual"].items():
        add(f"Fee compression {k}", v, "p.a.", "assumption; peer slopes in mart_fee_compression", "Industry fee pressure", rank=2)
    for s, d in sc["scenarios"].items():
        add(f"Scenario {s}: organic growth", d["organic_annual"], "p.a. by class", "assumption", "Scenario design", rank=4)
        add(f"Scenario {s}: equity return path (qtr)", d["equity_ret_q"], "per quarter", "assumption", "Scenario design", rank=4)
    add("Budget growth target", sc["budget_targets"]["revenue_growth"], "p.a.", "AssetLens assumption (GS publishes no total revenue growth target)", "Top-down budget illustration")
    add("Budget pre-tax margin target", sc["budget_targets"]["pretax_margin"], "%", "GS 10-Q Jun-2026 (acc. 0000886982-26-000297): AWM pre-tax margin approx. 30% medium-term target (verified)", "Top-down budget illustration")
    for k, v in ga.items():
        if k != "locations":
            add(f"GCC: {k}", v, "", "assumption (illustrative)", "Growth case", rank="")
    for k, v in ga["locations"].items():
        add(f"GCC location {k}", v, "", "assumption - VERIFY tax rates", "Location comparison")
    for k, v in sy.items():
        add(f"Synthetic: {k}", v, "", "synthetic generator (config/synthetic.yaml)", "Calibrated to public segment totals")
    add("Mandate discount rate", 0.09, "p.a.", "assumption", "Pricing LTV")
    add("Mandate hurdle margin", 0.15, "over FA break-even", "assumption", "Recommendation rule")
    return pd.DataFrame(rows)


def run() -> None:
    d = ROOT / "docs"
    (d / "RECONCILIATION_REPORT.md").write_text(reconciliation_report(), encoding="utf8")
    (d / "DATA_DICTIONARY.md").write_text(data_dictionary(), encoding="utf8")
    assumptions_register().to_csv(d / "ASSUMPTIONS_REGISTER.csv", index=False)
    (ROOT / "outputs" / "reports").mkdir(parents=True, exist_ok=True)
    (ROOT / "outputs" / "reports" / "RECONCILIATION_REPORT.md").write_text(reconciliation_report(), encoding="utf8")


if __name__ == "__main__":
    run()
    print("docs generated")
