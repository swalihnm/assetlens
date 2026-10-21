"""FRED download (public CSV endpoint, no key needed) and quarterly conversion."""
from __future__ import annotations

import io
from pathlib import Path

import httpx
import pandas as pd

RAW = Path(__file__).resolve().parents[3] / "data" / "raw" / "fred"
SERIES = ["SP500", "BAMLCC0A0CMTRIV", "BAMLHYH0A0HYM2TRIV", "DGS10", "DGS2", "DFF",
          "DEXUSEU", "CPIAUCSL"]
LEVEL_SERIES = {"SP500", "BAMLCC0A0CMTRIV", "BAMLHYH0A0HYM2TRIV"}


def fetch(series: str) -> pd.DataFrame:
    RAW.mkdir(parents=True, exist_ok=True)
    f = RAW / f"{series}.csv"
    if not f.exists():
        r = httpx.get("https://fred.stlouisfed.org/graph/fredgraph.csv",
                      params={"id": series}, timeout=60, follow_redirects=True)
        r.raise_for_status()
        f.write_bytes(r.content)
    df = pd.read_csv(io.BytesIO(f.read_bytes()))
    df.columns = ["date", "value"]
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df.dropna().set_index("date")["value"].rename(series).to_frame()


def quarterly() -> pd.DataFrame:
    """Quarterly returns for index-level series, quarterly averages for rates."""
    out = {}
    for s in SERIES:
        d = fetch(s)[s]
        if s in LEVEL_SERIES:
            q = d.resample("QE").last()
            out[f"{s}_ret"] = q.pct_change()
        else:
            out[f"{s}_avg"] = d.resample("QE").mean()
    return pd.DataFrame(out)
