"""Cross-platform pipeline runner (no `make` needed):  uv run python -m assetlens.pipeline [all | step ...]

Steps run in dependency order. `all` rebuilds everything from the SEC/FRED cache (network only for uncached files).
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STEPS: dict[str, list[list[str]]] = {
    "ingest": [["-m", "assetlens.ingest.run", "2"]],
    "extract": [["-m", "assetlens.extract.run_all"]],
    "warehouse": [["-m", "assetlens.warehouse.build"]],
    "benchmark": [["-m", "assetlens.benchmark.metrics"]],
    "market": [["-m", "assetlens.market.sensitivity"]],
    "synth": [["-m", "assetlens.synth.generator"]],
    "allocate": [["-m", "assetlens.allocation.methods"]],
    "forecast": [["-m", "assetlens.forecast.engine"], ["-m", "assetlens.forecast.budget"]],
    "montecarlo": [["-m", "assetlens.forecast.montecarlo"], ["-m", "assetlens.forecast.backtest"]],
    "analytics": [["-m", "assetlens.sales.analytics"], ["-m", "assetlens.comp.analysis"]],
    "excel": [["-m", "assetlens.excel.build_model"]],
    "powerbi": [["-m", "assetlens.powerbi.export_star_schema"]],
    "docs": [["-m", "assetlens.warehouse.docs_gen"]],
    "deck": [["-m", "assetlens.deck.build_deck"], ["-m", "assetlens.deck.render_pdf"]],
}
ORDER = list(STEPS)


def run(steps: list[str]) -> int:
    names = ORDER if steps in ([], ["all"]) else steps
    unknown = [s for s in names if s not in STEPS]
    if unknown:
        print(f"unknown step(s): {unknown}; choose from {ORDER}")
        return 2
    env = {"PYTHONUTF8": "1"}
    import os
    env = {**os.environ, **env}
    for name in names:
        t0 = time.time()
        for cmd in STEPS[name]:
            r = subprocess.run([sys.executable, *cmd], cwd=ROOT, env=env, check=False)
            if r.returncode:
                print(f"[pipeline] step '{name}' FAILED ({' '.join(cmd)})")
                return r.returncode
        print(f"[pipeline] {name} ok ({time.time() - t0:.0f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(run(sys.argv[1:]))
