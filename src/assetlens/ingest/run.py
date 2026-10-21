"""Day-1 ingestion: verify CIKs, build filing manifest, pull FRED."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import yaml

from assetlens.ingest import fred
from assetlens.ingest.edgar_client import RAW, EdgarClient

ROOT = Path(__file__).resolve().parents[3]
FORMS = {"10-K", "10-Q", "8-K"}


def filings_for(client: EdgarClient, cik: str) -> pd.DataFrame:
    sub = client.get_json(f"https://data.sec.gov/submissions/CIK{cik}.json")
    blocks = [sub["filings"]["recent"]]
    for f in sub["filings"].get("files", []):
        blocks.append(client.get_json(f"https://data.sec.gov/submissions/{f['name']}"))
    df = pd.concat([pd.DataFrame(b) for b in blocks], ignore_index=True)
    df = df[df["form"].isin(FORMS) & (df["filingDate"] >= "2019-01-01")].copy()
    df["cik"] = cik
    df["entity"] = sub["name"]
    return df


def main(phase: int = 1) -> None:
    cfg = yaml.safe_load((ROOT / "config" / "peers.yaml").read_text())["peers"]
    client = EdgarClient()
    rows = []
    for tkr, p in cfg.items():
        if p["phase"] > phase:
            continue
        for cik in p["ciks"]:
            d = filings_for(client, cik)
            d["ticker"] = tkr
            rows.append(d)
            print(tkr, cik, d["entity"].iloc[0] if len(d) else "?", len(d), "filings")
    m = pd.concat(rows, ignore_index=True)
    m["url"] = ("https://www.sec.gov/Archives/edgar/data/" + m["cik"].str.lstrip("0") + "/"
                + m["accessionNumber"].str.replace("-", "") + "/" + m["primaryDocument"])
    keep = ["ticker", "cik", "entity", "form", "filingDate", "reportDate", "accessionNumber",
            "primaryDocument", "items", "url"]
    RAW.mkdir(parents=True, exist_ok=True)
    m[keep].sort_values(["ticker", "filingDate"]).to_csv(RAW / "manifest.csv", index=False)
    q = fred.quarterly()
    (ROOT / "data" / "interim").mkdir(parents=True, exist_ok=True)
    q.to_csv(ROOT / "data" / "interim" / "fred_quarterly.csv")
    print("manifest rows", len(m), "| FRED range", q.index.min().date(), q.index.max().date())
    print("network calls:", client.network_calls)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 1)
