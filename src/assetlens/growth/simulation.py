"""M10 Phase 2 - Monte Carlo of the GCC case and a staged-entry real option (decision tree via simulation).

Random drivers per path: mature AUM per advisor (lognormal), net revenue bps (normal), ramp midpoint (uniform),
advisor attrition (beta), hiring achievement (beta) and a market path for client AUM (lognormal annual returns).
Staged entry: representative-office pilot first; expand only if pilot AUM at the end of year 2 clears a threshold.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from assetlens.growth import business_case as GC

PILOT = dict(advisors_hired=[3, 0, 0, 0, 0, 0, 0], core_staff=3, regulatory_capital_musd=5.0)
PILOT_SETUP_FRAC, PILOT_LICENCE_FRAC = 0.35, 0.4
THRESHOLD_MUSD = 500.0
EXIT_COST_MUSD = 1.0
DELAY_YEARS = 2


def draw(n: int, seed: int = 99) -> list[dict]:
    rng = np.random.default_rng(seed)
    base = GC.CFG
    out = []
    for _ in range(n):
        mkt = np.cumprod(1 + np.clip(rng.normal(0.06, 0.14, 7), -0.5, 0.8))
        hit = rng.beta(8.5, 1.5)                                       # mean 0.85 of planned hires achieved
        out.append(dict(
            mature_aum_per_advisor_musd=base["mature_aum_per_advisor_musd"] * float(np.exp(rng.normal(-0.03, 0.30))),
            net_revenue_bps=float(rng.normal(base["net_revenue_bps"], 8.0)),
            ramp_midpoint_years=float(rng.uniform(1.0, 2.5)),
            advisor_attrition=float(rng.beta(2, 23)) + 0.02,
            advisors_hired=[h * hit for h in base["advisors_hired"]],
            market_index=mkt))
    return out


def pilot_params(d: dict) -> dict:
    pilot_hires = [h * (d["advisors_hired"][0] / GC.CFG["advisors_hired"][0]) for h in PILOT["advisors_hired"]]
    return {**d, "advisors_hired": pilot_hires, "core_staff": PILOT["core_staff"],
            "regulatory_capital_musd": PILOT["regulatory_capital_musd"]}


def simulate(n: int = 2000, location: str | None = None, seed: int = 99, threshold: float = THRESHOLD_MUSD,
             delay: int = DELAY_YEARS) -> dict:
    loc = GC.CFG["locations"][location or GC.CFG["base_location"]]
    rdisc = GC.CFG["discount_rate"]
    full, staged, passed = np.empty(n), np.empty(n), np.zeros(n, dtype=bool)
    for i, d in enumerate(draw(n, seed)):
        f = GC.run(location, **d)
        full[i] = f["npv"]
        # pilot cash flows (years 0-2): smaller set-up and licence, no terminal value
        locs = {**GC.CFG["locations"], "PILOT": {**loc, "setup_capex_musd": loc["setup_capex_musd"] * PILOT_SETUP_FRAC,
                                                   "licence_musd_yr": loc["licence_musd_yr"] * PILOT_LICENCE_FRAC}}
        p = GC.run("PILOT", **pilot_params(d), locations=locs)
        pilot_cf = p["fcf"][:3].copy()                                  # year 0, 1, 2
        pilot_cf[-1] -= PILOT["regulatory_capital_musd"] * 0              # capital stays tied up if expanding
        disc = (1 + rdisc) ** -np.arange(3)
        pilot_pv = float((pilot_cf * disc).sum())
        ok = p["aum_end"][1] >= threshold
        passed[i] = ok
        if ok:                                                          # expand: full programme starts DELAY years later
            staged[i] = pilot_pv + f["npv"] * (1 + rdisc) ** -delay
        else:                                                           # abandon: release capital, pay exit cost
            staged[i] = pilot_pv + (PILOT["regulatory_capital_musd"] - EXIT_COST_MUSD) * (1 + rdisc) ** -2
    def stats(x):
        return dict(mean=float(x.mean()), p10=float(np.percentile(x, 10)), p50=float(np.percentile(x, 50)),
                    p90=float(np.percentile(x, 90)), prob_loss=float((x < 0).mean()))
    return dict(full=stats(full), staged=stats(staged), pass_rate=float(passed.mean()),
                option_value=float(staged.mean() - full.mean()), n=n, location=location or GC.CFG["base_location"],
                draws=pd.DataFrame(dict(full=full, staged=staged, passed=passed)))


def option_grid(n: int = 1000) -> pd.DataFrame:
    rows = []
    for th in (250, 350, 500):
        for dl in (1, 2):
            r = simulate(n, threshold=th, delay=dl)
            rows.append(dict(threshold_musd=th, delay_years=dl, pass_rate=r["pass_rate"], full_mean=r["full"]["mean"],
                             staged_mean=r["staged"]["mean"], option_value=r["option_value"],
                             full_prob_loss=r["full"]["prob_loss"], staged_prob_loss=r["staged"]["prob_loss"]))
    return pd.DataFrame(rows)


if __name__ == "__main__":
    pd.set_option("display.width", 200)
    print(option_grid().round(3).to_string())
