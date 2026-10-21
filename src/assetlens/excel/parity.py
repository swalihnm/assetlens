"""M14 parity test: recalculate the workbook with a pure-Python Excel engine and compare with the Python models.

LibreOffice is not installed on the build machine (see DECISIONS.md); `formulas` evaluates the same formulas.
Fails on any #REF!/#DIV/0!/#VALUE!/#NAME? and on parity breaks beyond 0.01%.
"""
from __future__ import annotations

import shutil
import tempfile
import warnings
from dataclasses import replace
from pathlib import Path

import formulas
import numpy as np
import openpyxl

from assetlens.excel.build_model import OUT
from assetlens.forecast.engine import load_base, run_scenario
from assetlens.growth import business_case as GC
from assetlens.pricing import inputs as pin
from assetlens.pricing import mandate as PM

warnings.filterwarnings("ignore")
ERRORS = ("#REF!", "#DIV/0!", "#VALUE!", "#NAME?", "#N/A", "#NUM!")
TOL = 1e-4  # 0.01%


class Recalc:
    def __init__(self, overrides: dict[tuple[str, str], object] | None = None):
        tmp = Path(tempfile.mkdtemp()) / "m.xlsx"
        wb = openpyxl.load_workbook(OUT)
        for (sh, addr), v in (overrides or {}).items():
            wb[sh][addr].value = v
        wb.save(tmp)
        self.sol = formulas.ExcelModel().loads(str(tmp)).finish().calculate()
        self.idx = {}
        for k, v in self.sol.items():
            sk = str(k).upper()
            if "]" in sk and "!" in sk:
                sheet, cell = sk.split("]")[1].split("!")
                self.idx[(sheet.strip("'"), cell.replace("$", ""))] = v
        shutil.rmtree(tmp.parent, ignore_errors=True)

    def get(self, sheet: str, cell: str):
        v = self.idx[(sheet.upper(), cell.upper())].value
        v = np.asarray(v).ravel()[0]
        return v.item() if hasattr(v, "item") else v

    def errors(self) -> list[str]:
        bad = []
        for (sh, cell), rng in self.idx.items():
            for x in np.asarray(rng.value).ravel():
                if isinstance(x, str) and x.startswith(ERRORS) or str(x) in ERRORS:
                    bad.append(f"{sh}!{cell}={x}")
        return bad


def rel(a, b) -> float:
    return abs(a - b) / max(abs(b), 1e-9)


def run() -> dict:
    out = {"scenarios": {}, "errors": [], "failures": []}
    base = load_base()
    cols = "CDEFGHIJ"
    for sc in ("base", "bull", "bear", "stress"):
        rc = Recalc({("Scenarios", "B2"): sc})
        py = run_scenario(sc, base)
        worst = 0.0
        for j, c in enumerate(cols):
            for sheet, cell, ref in [("PnL", f"{c}5", py.net_revenues[j]), ("PnL", f"{c}10", py.pretax[j]),
                                     ("PnL", f"{c}7", py.comp[j]), ("PnL", f"{c}14", py.aus_total[j]),
                                     ("Revenue", f"{c}17", py.mgmt_fees[j])]:
                worst = max(worst, rel(float(rc.get(sheet, cell)), float(ref)))
        chk = float(rc.get("Checks", "B19"))
        out["scenarios"][sc] = dict(max_rel_error=worst, checks_sum=chk, master=rc.get("Cover", "B4"))
        if worst > TOL:
            out["failures"].append(f"{sc}: P&L parity {worst:.2e}")
        if chk > 1e-3:
            out["failures"].append(f"{sc}: checks sheet sum {chk}")
        if sc == "base":
            out["errors"] = rc.errors()
            if out["errors"]:
                out["failures"].append(f"{len(out['errors'])} Excel error cells, e.g. {out['errors'][:3]}")
            d = pin.defaults("equity")
            m = replace(PM.Mandate(), cost_per_fte=d["cost_per_fte"], allocated_bps=d["allocated_bps"])
            pairs = [("Mandate_Pricing", "B51", PM.lifetime_value(m, "marginal")), ("Mandate_Pricing", "B52", PM.lifetime_value(m, "fully_allocated")),
                     ("Mandate_Pricing", "B56", PM.break_even_fee(m, "marginal")), ("Mandate_Pricing", "B57", PM.break_even_fee(m, "fully_allocated")),
                     ("Mandate_Pricing", "B62", PM.break_even_fee(m, "marginal", "lifetime")),
                     ("Mandate_Pricing", "B63", PM.break_even_fee(m, "fully_allocated", "lifetime"))]
            g = GC.run()
            pairs += [("Growth_Case", "B77", g["npv"]), ("Growth_Case", "B76", g["npv_explicit"]), ("Growth_Case", "B78", g["irr"]),
                      ("Growth_Case", "B80", g["payback_years"]), ("Growth_Case", "B83", g["peak_funding"])]
            out["other"] = {}
            for sh, cell, ref in pairs:
                v = float(rc.get(sh, cell))
                out["other"][f"{sh}!{cell}"] = (v, float(ref), rel(v, float(ref)))
                if rel(v, float(ref)) > TOL:
                    out["failures"].append(f"{sh}!{cell}: excel {v} vs python {ref}")
    for loc in ("KAFD", "ADGM"):
        rc = Recalc({("Growth_Case", "B2"): loc})
        g = GC.run(loc)
        v = float(rc.get("Growth_Case", "B77"))
        out["scenarios"][f"growth_{loc}"] = dict(max_rel_error=rel(v, g["npv"]))
        if rel(v, g["npv"]) > TOL:
            out["failures"].append(f"Growth {loc}: excel {v} vs python {g['npv']}")
    for m in ("revenue", "headcount", "step_down", "reciprocal"):
        rc = Recalc({("Profitability", "B2"): m})
        if abs(float(rc.get("Profitability", "B14"))) > 1e-3:
            out["failures"].append(f"Profitability reconciliation fails for {m}")
    return out


if __name__ == "__main__":
    r = run()
    for k, v in r["scenarios"].items():
        print(k, v)
    for k, v in r.get("other", {}).items():
        print(k, [round(x, 6) for x in v])
    print("errors:", r["errors"][:10])
    print("FAILURES:", r["failures"] or "none")
