"""Locate Exhibit 99.1 (earnings release) documents for 8-K Item 2.02 filings."""
from __future__ import annotations

import pandas as pd

from assetlens.ingest.edgar_client import EdgarClient


def release_url(client: EdgarClient, cik: str, accession: str) -> str | None:
    base = f"https://www.sec.gov/Archives/edgar/data/{cik.lstrip('0')}/{accession.replace('-', '')}/"
    idx = client.get_json(base + "index.json")
    names = [i["name"] for i in idx["directory"]["item"]]
    htm = [n for n in names if n.lower().endswith((".htm", ".html"))
           and "index" not in n.lower() and "r1.htm" != n.lower()]
    # prefer files that look like an earnings exhibit (ex99/ex-99/pressrelease), else 2nd htm
    for n in htm:
        low = n.lower()
        if any(k in low for k in ("ex99", "ex-99", "exhibit99", "pressrelease", "earnings", "ex_99")):
            return base + n
    return base + htm[1] if len(htm) > 1 else (base + htm[0] if htm else None)


def earnings_manifest(client: EdgarClient, manifest: pd.DataFrame, ticker: str) -> pd.DataFrame:
    m = manifest[(manifest.ticker == ticker) & (manifest.form == "8-K")
                 & manifest["items"].astype(str).str.contains("2.02")].copy()
    m["release_url"] = [release_url(client, r.cik if isinstance(r.cik, str) else f"{r.cik:010d}",
                                    r.accessionNumber) for r in m.itertuples()]
    return m
