"""Peer extraction: P&L rules (8-K release / 10-Q tables) + closure-gated AUM roll-forward."""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from assetlens.extract import releases as R
from assetlens.extract import rollforward as RF
from assetlens.extract.tables import soup
from assetlens.ingest.edgar_client import EdgarClient

ROOT = Path(__file__).resolve().parents[3]
INT = ROOT / "data" / "interim"


def meta(ticker, unit, pe, url, acc, form, filed):
    return dict(ticker=ticker, unit=unit, period_end=pe, source_url=url, accession_no=acc,
                form_type=form, filed_date=filed, document=url.split("/")[-1])


def rf_facts(roll: RF.Roll | None, mt: dict, scale: float = 1000) -> list[dict]:
    if roll is None:
        return []
    base = {**mt, "currency": "USD", "scale": "millions", "period_type": "Q",
            "method": "html_table", "confidence": 1.0, "reviewed": True,
            "locator": f"table#{roll.table} col={roll.col} (closure-checked)", "raw_text": roll.raw}
    vals = {"aum_begin": roll.begin, "net_flows": roll.flows, "market": roll.market,
            "aum_other_change": roll.other, "aum_end": roll.end}
    return [{**base, "metric": k, "value": v * scale} for k, v in vals.items()]


def quarter_end_before(filed: str) -> str:
    """Latest calendar quarter end strictly before the filing date (earnings releases follow quarter end)."""
    d = pd.Timestamp(filed) - pd.Timedelta(days=1)
    return (d.to_period("Q") - (0 if d == d.to_period("Q").end_time.normalize() else 1)).end_time.strftime("%Y-%m-%d")


def run_trow(client: EdgarClient, m: pd.DataFrame) -> pd.DataFrame:
    out, have = [], set()
    rel = pd.read_csv(INT / "TROW_releases.csv", dtype={"cik": str})
    for r in rel.itertuples():
        if not isinstance(r.release_url, str):
            continue
        html = client.get(r.release_url)
        pe = quarter_end_before(r.filingDate)
        if pe < "2019-03-31":
            continue
        mt = meta("TROW", "Company", pe, r.release_url, r.accessionNumber, "8-K-EX99.1", r.filingDate)
        f = R.parse_release(html, R.TROW_RULES, mt)
        f += rf_facts(RF.best(soup(html), ["Three months ended", "Net cash flows"], 500), mt)
        out += f
        have.add(pe)
    for r in m[(m.ticker == "TROW") & (m.form == "10-Q")].itertuples():
        if r.reportDate in have:
            continue
        html = client.get(r.url)
        mt = meta("TROW", "Company", r.reportDate, r.url, r.accessionNumber, "10-Q", r.filingDate)
        out += R.parse_release(html, R.TROW_10Q_RULES, mt)
        out += rf_facts(RF.best(soup(html), ["Net cash flows", "Net market"], 500), mt)
    return pd.DataFrame(out)


if __name__ == "__main__":
    c = EdgarClient()
    mf = pd.read_csv(ROOT / "data" / "raw" / "manifest.csv", dtype={"cik": str})
    df = run_trow(c, mf)
    df.to_csv(INT / "TROW_raw_facts.csv", index=False)
    w = df.pivot_table(index="period_end", columns="metric", values="value", aggfunc="first")
    pd.set_option("display.width", 250)
    print(w[["net_revenues", "comp_total", "pretax_income", "aum_begin", "net_flows", "market", "aum_end"]].round(0).to_string())


def run_releases(client: EdgarClient, ticker: str, rules, rf_anchors, unit="Company") -> pd.DataFrame:
    out = []
    rel = pd.read_csv(INT / f"{ticker}_releases.csv", dtype={"cik": str})
    for r in rel.itertuples():
        if not isinstance(r.release_url, str):
            continue
        pe = quarter_end_before(r.filingDate)
        if pe < "2019-03-31":
            continue
        html = client.get(r.release_url)
        mt = meta(ticker, unit, pe, r.release_url, r.accessionNumber, "8-K-EX99.1", r.filingDate)
        out += R.parse_release(html, rules, mt)
        out += rf_facts(RF.best(soup(html), rf_anchors, 100, cols={0}), mt)
    return pd.DataFrame(out)
