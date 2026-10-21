"""Run GS extraction end to end -> data/interim (raw facts, latest, quarterly, reconciliation)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from assetlens.extract import consolidate as C
from assetlens.extract import gs
from assetlens.ingest.edgar_client import EdgarClient

ROOT = Path(__file__).resolve().parents[3]
# Q3 2026 10-Q not filed yet (as of 2026-10-21): use the earnings release, 8-K Ex 99.1
RELEASES = [("https://www.sec.gov/Archives/edgar/data/0000886982/000088698226000529/a3q26gsearningsresults.htm",
             "0000886982-26-000529", "2026-10-13", "2026-09-30")]


def main() -> None:
    client = EdgarClient()
    m = pd.read_csv(ROOT / "data" / "raw" / "manifest.csv")
    df = gs.run(client, m)
    for url, acc, filed, pe in RELEASES:
        q10 = m[(m.ticker == "GS") & (m.form == "10-Q") & (m.reportDate == pe)]
        if q10.empty:
            r = pd.DataFrame(gs.extract_release(client, url, acc, filed, pe))
            r["perimeter"] = "AWM"
            df = pd.concat([df, r], ignore_index=True)
    out = ROOT / "data" / "interim"
    df.to_csv(out / "gs_raw_facts.csv", index=False)
    cur, log = C.latest(df)
    cur.to_csv(out / "gs_facts_latest.csv", index=False)
    log.to_csv(out / "gs_restatement_log.csv", index=False)
    w = C.quarterly(cur)
    w.to_csv(out / "gs_awm_quarterly.csv")
    rec = C.reconcile(w)
    rec.to_csv(out / "gs_reconciliation.csv", index=False)
    print(rec.groupby("check").passed.agg(["sum", "count"]))
    print(rec[~rec.passed].to_string())


if __name__ == "__main__":
    main()
