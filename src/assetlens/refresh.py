"""Refresh when Goldman's next 10-Q appears on EDGAR.

`python -m assetlens.refresh` is cheap when nothing is new (one cached-bypassing submissions request). When a GS 10-Q
for a period not yet in the warehouse appears it re-ingests, re-extracts, rebuilds every mart, regenerates synthetic data,
forecasts, Excel, Power BI export, docs and deck, then runs the tests and records the result in data/interim/refresh_state.json.
Optionally removes the scheduled task that calls it (--remove-task NAME).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "data" / "interim" / "refresh_state.json"
STEPS = [
    ["-m", "assetlens.ingest.run", "2"],
    ["-m", "assetlens.extract.run_gs"],
    ["-m", "assetlens.warehouse.build"],
    ["-m", "assetlens.benchmark.metrics"],
    ["-m", "assetlens.market.sensitivity"],
    ["-m", "assetlens.synth.generator"],
    ["-m", "assetlens.allocation.methods"],
    ["-m", "assetlens.forecast.engine"],
    ["-m", "assetlens.forecast.budget"],
    ["-m", "assetlens.forecast.montecarlo"],
    ["-m", "assetlens.forecast.backtest"],
    ["-m", "assetlens.sales.analytics"],
    ["-m", "assetlens.excel.build_model"],
    ["-m", "assetlens.powerbi.export_star_schema"],
    ["-m", "assetlens.warehouse.docs_gen"],
    ["-m", "assetlens.deck.build_deck"],
    ["-m", "assetlens.deck.render_pdf"],
]


def latest_gs_10q() -> tuple[str, str] | None:
    load_dotenv(ROOT / ".env")
    r = httpx.get("https://data.sec.gov/submissions/CIK0000886982.json", headers={"User-Agent": os.environ["SEC_USER_AGENT"]}, timeout=30)
    r.raise_for_status()
    rec = r.json()["filings"]["recent"]
    rows = [(rd, acc) for f, rd, acc in zip(rec["form"], rec["reportDate"], rec["accessionNumber"]) if f == "10-Q"]
    return max(rows) if rows else None


def processed_period() -> str:
    return json.loads(STATE.read_text())["period"] if STATE.exists() else "2026-06-30"   # last 10-Q built into the project


def run(force: bool = False, remove_task: str | None = None) -> dict:
    found = latest_gs_10q()
    done = processed_period()
    if not found or (found[0] <= done and not force):
        return {"status": "nothing new", "latest_10q": found, "processed_through": done}
    py = sys.executable
    env = {**os.environ, "PYTHONUTF8": "1"}
    for step in STEPS:
        res = subprocess.run([py, *step], cwd=ROOT, env=env, capture_output=True, text=True, check=False)
        if res.returncode:
            out = {"status": "failed", "step": " ".join(step), "stderr": res.stderr[-800:]}
            STATE.parent.mkdir(parents=True, exist_ok=True)
            STATE.write_text(json.dumps({**out, "period": done, "at": datetime.now().isoformat()}))
            return out
    t = subprocess.run([py, "-m", "pytest", "-q", "-m", "not slow"], cwd=ROOT, env=env, capture_output=True, text=True, check=False)
    out = {"status": "refreshed", "period": found[0], "accession": found[1], "tests": t.stdout.strip().splitlines()[-1] if t.stdout else "", "at": datetime.now().isoformat()}
    STATE.write_text(json.dumps(out))
    if remove_task and t.returncode == 0:
        subprocess.run(["schtasks", "/delete", "/tn", remove_task, "/f"], capture_output=True, check=False)
    return out


if __name__ == "__main__":
    args = sys.argv[1:]
    task = args[args.index("--remove-task") + 1] if "--remove-task" in args else None
    print(json.dumps(run("--force" in args, task), indent=1))
