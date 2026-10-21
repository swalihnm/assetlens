"""Unify extracted facts -> DuckDB `fact_financials` (+ provenance, restatement log, FRED).

Rules: GS from latest-vintage consolidation (Q4 derived = FY - 9M); peers from releases/10-Qs.
AUM roll-forwards must chain (begin == prior end) or they are demoted to end-balance-only.
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from assetlens.extract import consolidate as C

ROOT = Path(__file__).resolve().parents[3]
INT = ROOT / "data" / "interim"
DB = ROOT / "data" / "warehouse" / "assetlens.duckdb"

PROV = ["ticker", "unit", "metric", "period_end", "period_type", "value", "currency", "scale",
        "source_url", "accession_no", "form_type", "filed_date", "document", "locator", "raw_text",
        "method", "confidence", "reviewed"]
ROLL = ["aum_begin", "net_flows", "market", "aum_other_change", "aum_end"]


def gs_long() -> pd.DataFrame:
    cur = pd.read_csv(INT / "gs_facts_latest.csv")
    w = C.quarterly(cur)
    c = cur[cur.perimeter == "AWM"].copy()
    rows = []
    for pe, r in w.iterrows():
        for m, v in r.items():
            if m in ("derived_q4",) or pd.isna(v):
                continue
            q = c[(c.metric == m) & (c.period_end == pe) & (c.period_type == "Q")]
            if len(q):
                x = q.iloc[0].to_dict()
            else:
                fy = c[(c.metric == m) & (c.period_end == pe) & (c.period_type == "FY")]
                ytd = c[(c.metric == m) & (c.period_end == pe[:4] + "-09-30") & (c.period_type == "YTD")]
                if len(fy) and len(ytd):
                    x = fy.iloc[0].to_dict()
                    x["locator"] = (f"DERIVED Q4 = FY ({fy.iloc[0].accession_no}, {fy.iloc[0].locator}) "
                                    f"- 9M YTD ({ytd.iloc[0].accession_no}, {ytd.iloc[0].locator})")
                    x["method"] = "derived"
                elif len(fy):
                    x = fy.iloc[0].to_dict()
                    x["locator"] += " (balance at year end)"
                else:  # aum_begin filled from prior-quarter end
                    x = dict(c.iloc[0].to_dict())
                    x.update(locator="DERIVED aum_begin = prior-quarter aum_end", method="derived",
                             raw_text="", source_url="", accession_no="", form_type="", filed_date="",
                             document="")
            x.update(metric=m, period_end=pe, period_type="Q", value=float(v), ticker="GS", unit="AWM")
            rows.append(x)
    df = pd.DataFrame(rows)
    df = df[~df.metric.isin(["aus_end_check"])]
    df["metric"] = df.metric.replace({"aus_end": "aum_end", "aus_begin": "aum_begin",
                                      "aus_total": "aum_total_check"})
    return df[[c for c in PROV if c in df.columns]]


def peer_long(t: str) -> pd.DataFrame:
    d = pd.read_csv(INT / f"{t}_raw_facts.csv")
    d = d[d.metric.notna() & ~d.metric.str.startswith("_")]
    d = d.sort_values("filed_date").drop_duplicates(["ticker", "metric", "period_end"], keep="last")
    return d[[c for c in PROV if c in d.columns]]


def chain_filter(df: pd.DataFrame, gaps: list[dict]) -> pd.DataFrame:
    """Keep roll-forwards that chain with the prior quarter; else demote to end-balance only."""
    out = []
    for t, g in df.groupby("ticker"):
        w = g[g.metric.isin(ROLL)].pivot_table(index="period_end", columns="metric", values="value", aggfunc="first")
        pes = sorted(w.index)
        mism: dict[str, int] = {pe: 0 for pe in pes}
        for p0, p1 in zip(pes, pes[1:]):
            if (pd.Period(p1, "Q") - pd.Period(p0, "Q")).n != 1:
                continue
            e0, b1 = w.loc[p0].get("aum_end"), w.loc[p1].get("aum_begin")
            if pd.notna(e0) and pd.notna(b1) and abs(b1 - e0) > max(1000, 0.001 * e0):
                mism[p0] += 1
                mism[p1] += 1
        # drop the quarter that disagrees with BOTH neighbours; an isolated pair drops the later one
        bad = [pe for pe in pes if mism[pe] >= 2]
        for p0, p1 in zip(pes, pes[1:]):
            if mism[p0] == 1 and mism[p1] == 1 and p0 not in bad and p1 not in bad:
                bad.append(p1)
        for pe in bad:
            gaps.append(dict(ticker=t, period_end=pe, issue="AUM roll-forward does not chain with prior quarter; "
                             "flows/market dropped, end balance kept only if chain consistent"))
        mask = (g.period_end.isin(bad)) & g.metric.isin(["aum_begin", "net_flows", "market", "aum_other_change", "aum_end"])
        out.append(g[~mask])
    return pd.concat(out, ignore_index=True)


def build() -> dict:
    gaps: list[dict] = []
    df = pd.concat([gs_long(), peer_long("BLK"), peer_long("TROW"), peer_long("IVZ")], ignore_index=True)
    df = chain_filter(df, gaps)
    df["currency"] = df.currency.fillna("USD")
    df["scale"] = df.scale.fillna("millions")
    df["retrieved_at"] = pd.Timestamp.now(tz="UTC").isoformat()
    df = df.reset_index(drop=True)
    df.insert(0, "fact_id", range(1, len(df) + 1))
    DB.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB))
    con.register("f", df)
    con.execute("create or replace table fact_financials as select * from f")
    prov_cols = ["fact_id", "source_url", "accession_no", "form_type", "filed_date", "document", "locator",
                 "raw_text", "method", "confidence", "reviewed", "retrieved_at"]
    con.execute(f"create or replace table fact_provenance as select {', '.join(prov_cols)} from fact_financials")
    con.execute("alter table fact_financials drop column source_url")  # kept in fact_provenance
    for col in ["accession_no", "form_type", "filed_date", "document", "locator", "raw_text", "method",
                "confidence", "reviewed", "retrieved_at"]:
        con.execute(f"alter table fact_financials drop column {col}")
    log = pd.read_csv(INT / "gs_restatement_log.csv")
    con.register("rl", log)
    con.execute("create or replace table restatement_log as select * from rl")
    fq = pd.read_csv(INT / "fred_quarterly.csv", index_col=0, parse_dates=True)
    fq = fq[fq.index <= "2026-09-30"].reset_index(names="period_end")  # drop the incomplete Q4-2026
    con.register("fq", fq)
    con.execute("create or replace table fact_market as select * from fq")
    pd.DataFrame(gaps).to_csv(INT / "chain_gaps.csv", index=False)
    n = con.execute("select ticker, count(*) from fact_financials group by 1 order by 1").fetchall()
    con.close()
    return {"facts": n, "chain_gaps": gaps}


if __name__ == "__main__":
    print(build())
