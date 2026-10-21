"""Extract every company (GS, BLK, TROW, IVZ, MS, JPM, BEN) from the cached filing manifest into data/interim.

One entry point so a clean clone reproduces the warehouse inputs: `make extract` (needs `make ingest` first).
"""
from __future__ import annotations

import pandas as pd

from assetlens.extract import peers2, run_gs
from assetlens.extract import releases as R
from assetlens.extract.run_peers import INT, ROOT, meta, quarter_end_before, run_releases, run_trow
from assetlens.ingest import exhibits
from assetlens.ingest.edgar_client import EdgarClient


def release_manifests(client: EdgarClient, m: pd.DataFrame) -> None:
    """Exhibit 99.1 URLs for each earnings 8-K (cached, so cheap on reruns)."""
    for t in ("TROW", "IVZ", "BLK", "BEN"):
        exhibits.earnings_manifest(client, m, t).to_csv(INT / f"{t}_releases.csv", index=False)


def run_blk(client: EdgarClient) -> pd.DataFrame:
    rel = pd.read_csv(INT / "BLK_releases.csv", dtype={"cik": str})
    out = []
    for r in rel.itertuples():
        if not isinstance(r.release_url, str):
            continue
        pe = quarter_end_before(r.filingDate)
        if pe < "2019-03-31":
            continue
        out += R.parse_release(client.get(r.release_url), R.BLK_RULES,
                               meta("BLK", "Company", pe, r.release_url, r.accessionNumber, "8-K-EX99.1", r.filingDate))
    return pd.DataFrame(out)


def main() -> dict[str, int]:
    INT.mkdir(parents=True, exist_ok=True)
    client = EdgarClient()
    m = pd.read_csv(ROOT / "data" / "raw" / "manifest.csv", dtype={"cik": str})
    release_manifests(client, m)
    run_gs.main()
    counts: dict[str, int] = {}
    for t, df in {"TROW": run_trow(client, m),
                  "IVZ": run_releases(client, "IVZ", R.IVZ_RULES, ["Beginning Assets", "Ending Assets"]),
                  "BLK": run_blk(client)}.items():
        df.to_csv(INT / f"{t}_raw_facts.csv", index=False)
        counts[t] = len(df)
    for t, df in peers2.run_all().items():
        counts[t] = len(df)
    return counts


if __name__ == "__main__":
    print(main())
