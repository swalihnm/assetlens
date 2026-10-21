"""M10 (deterministic core) - GCC private wealth office business case. Annual, year 0 = set-up.

Advisor cohorts ramp on a logistic curve of tenure; client AUM = sum over cohorts of mature AUM * ramp(tenure)
* client retention; revenue = net revenue bps * average AUM.  Monte Carlo and the staged-entry real option are
Phase 2 extensions (see docs/modules/M10.md).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import numpy_financial as npf
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[3]
CFG = yaml.safe_load((ROOT / "config" / "assumptions.yaml").read_text())["growth_case"]


def ramp(tenure: float, mid: float, k: float) -> float:
    return 1.0 / (1.0 + np.exp(-k * (tenure - mid)))


def run(location: str | None = None, **over) -> dict:
    c = {**CFG, **over}
    loc = c["locations"][location or c["base_location"]]
    n = c["years"]
    yrs = np.arange(1, n + 1)
    hires = np.array(c["advisors_hired"], dtype=float)
    # advisors by cohort alive in year t (hired at start of year h, attrition applied annually)
    adv = np.zeros(n)
    aum_end = np.zeros(n)
    for h in range(n):
        for t in range(h, n):
            alive = hires[h] * (1 - c["advisor_attrition"]) ** (t - h)
            adv[t] += alive
            tenure = (t - h) + 0.5
            aum_end[t] += (alive * c["mature_aum_per_advisor_musd"] * ramp(tenure, c["ramp_midpoint_years"], c["ramp_steepness"])
                           * (1 - c["client_attrition"]) ** (t - h))
    aum_start = np.concatenate([[0.0], aum_end[:-1]])
    avg_aum = (aum_start + aum_end) / 2
    revenue = avg_aum * c["net_revenue_bps"] / 1e4
    support = adv * c["support_per_advisor"] + c["core_staff"]
    infl = (1 + c["cost_inflation"]) ** (yrs - 1)
    comp = (adv * c["advisor_cost_musd"] + support * c["support_cost_musd"]) * loc["cost_index"] * infl
    variable = revenue * c["variable_comp_pct_of_revenue"]
    premises = (adv + support) * c["premises_tech_per_head_musd"] * loc["cost_index"] * infl + loc["licence_musd_yr"]
    ebitda = revenue - comp - variable - premises
    tax = np.maximum(ebitda, 0) * loc["tax_rate"]
    capex0 = loc["setup_capex_musd"]
    reg_cap = c["regulatory_capital_musd"]
    fcf = np.concatenate([[-(capex0 + reg_cap)], ebitda - tax])
    fcf[-1] += reg_cap                                                    # capital released at end of horizon
    r, g = c["discount_rate"], c["terminal_growth"]
    tv = (ebitda[-1] - tax[-1]) * (1 + g) / (r - g)
    disc = (1 + r) ** -np.arange(0, n + 1)
    npv_explicit = float((fcf * disc).sum())
    npv_total = npv_explicit + float(tv * disc[-1])
    cum = np.cumsum(fcf)
    dcum = np.cumsum(fcf * disc)

    def first_cross(series):
        idx = np.flatnonzero(series >= 0)
        if len(idx) == 0:
            return None
        i = int(idx[0])
        return float(i - 1 + (-series[i - 1] / (series[i] - series[i - 1]))) if i > 0 else 0.0

    irr = float(npf.irr(np.concatenate([fcf[:-1], [fcf[-1] + tv]])))
    be_year = next((int(t) for t, e in zip(yrs, ebitda) if e > 0), None)
    return dict(location=location or c["base_location"], years=yrs, advisors=adv, headcount=adv + support,
                aum_end=aum_end, avg_aum=avg_aum, revenue=revenue, comp=comp + variable, premises=premises,
                ebitda=ebitda, tax=tax, fcf=fcf, terminal_value=float(tv), npv_explicit=npv_explicit,
                npv=npv_total, irr=irr, irr_explicit=float(npf.irr(fcf)) if (fcf > 0).any() else float("nan"),
                payback_years=first_cross(cum), discounted_payback_years=first_cross(dcum),
                break_even_year=be_year, peak_funding=float(-cum.min()))


def compare_locations() -> pd.DataFrame:
    rows = []
    for loc in CFG["locations"]:
        r = run(loc)
        rows.append(dict(location=loc, npv_musd=r["npv"], npv_explicit_musd=r["npv_explicit"], irr=r["irr"],
                         payback_years=r["payback_years"], break_even_year=r["break_even_year"],
                         peak_funding_musd=r["peak_funding"], note=CFG["locations"][loc]["note"]))
    return pd.DataFrame(rows)


if __name__ == "__main__":
    pd.set_option("display.width", 250)
    print(compare_locations().round(2).to_string())
    r = run()
    print({k: (np.round(v, 1).tolist() if isinstance(v, np.ndarray) else v) for k, v in r.items() if k in ("aum_end", "revenue", "ebitda", "fcf")})
