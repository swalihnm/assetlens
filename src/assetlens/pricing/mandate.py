"""M9 - mandate pricing: marginal (contribution) vs fully allocated profitability, break-evens, LTV.

Annual model over `years`. Revenue uses a TIERED schedule applied to average AUM. All $ in USD millions,
fees/costs in bps of AUM. Fixed-per-mandate costs (PM/service FTE, data, onboarding) are what make a
minimum viable AUM exist.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace

import numpy as np
from scipy.optimize import brentq


@dataclass
class Mandate:
    name: str = "Institutional equity SMA"
    mandate_type: str = "SMA"
    asset_class: str = "equity"
    initial_aum: float = 1000.0                                  # $m
    tiers: list[tuple[float, float]] = field(default_factory=lambda: [
        (250.0, 40.0), (500.0, 32.0), (float("inf"), 24.0)])      # (upper AUM bound $m, bps)
    growth_annual: float = 0.06                                   # net AUM growth (market + flows)
    hazard_annual: float = 0.08                                   # annual termination hazard
    weibull_shape: float = 1.0                                    # 1.0 = exponential
    years: int = 7
    # direct costs
    pm_fte: float = 0.6
    service_fte: float = 0.3
    cost_per_fte: float = 0.45                                    # $m loaded (synthetic, from M7/M8)
    trading_bps: float = 1.0
    custody_admin_bps: float = 1.5
    data_licence: float = 0.05                                    # $m / year
    onboarding: float = 0.25                                      # $m one-off at t=0
    commission_pct_first_year: float = 0.15
    seed_capital: float = 0.0
    cost_of_capital: float = 0.10
    allocated_bps: float = 6.0                                    # shared cost, ABC rate from M8 (bps of AUM)
    discount_rate: float = 0.09


def tiered_fee(aum: float, tiers: list[tuple[float, float]], scale: float = 1.0) -> float:
    """Annual fee ($m) on `aum` under a marginal-tier schedule, optionally scaled."""
    fee, lo = 0.0, 0.0
    for hi, bps in tiers:
        if aum > lo:
            fee += (min(aum, hi) - lo) * bps / 1e4
        lo = hi
    return fee * scale


def effective_bps(aum: float, tiers, scale: float = 1.0) -> float:
    return tiered_fee(aum, tiers, scale) / aum * 1e4


def survival(m: Mandate, t: np.ndarray) -> np.ndarray:
    """Weibull survival S(t)=exp(-(t/lam)^k); lam chosen so that 1-S(1) equals the annual hazard."""
    lam = 1.0 / (-np.log(1 - m.hazard_annual)) ** (1 / m.weibull_shape)
    return np.exp(-((t / lam) ** m.weibull_shape))


def cash_flows(m: Mandate, fee_scale: float = 1.0, aum_path: np.ndarray | None = None) -> dict[str, np.ndarray]:
    """Per-year (1..years) revenue and cost lines for a surviving mandate (before survival weighting)."""
    yrs = np.arange(1, m.years + 1)
    if aum_path is None:
        end = m.initial_aum * (1 + m.growth_annual) ** yrs
        start = np.concatenate([[m.initial_aum], end[:-1]])
        avg = (start + end) / 2
    else:
        avg = aum_path
    revenue = np.array([tiered_fee(a, m.tiers, fee_scale) for a in avg])
    direct_people = (m.pm_fte + m.service_fte) * m.cost_per_fte * (1.03 ** (yrs - 1))
    variable = avg * (m.trading_bps + m.custody_admin_bps) / 1e4
    commission = np.where(yrs == 1, m.commission_pct_first_year * revenue, 0.0)
    capital = np.full(m.years, m.seed_capital * m.cost_of_capital)
    direct = direct_people + variable + m.data_licence + commission + capital
    allocated = avg * m.allocated_bps / 1e4
    return dict(avg_aum=avg, revenue=revenue, direct=direct, allocated=allocated,
                marginal=revenue - direct, fully_allocated=revenue - direct - allocated)


def lifetime_value(m: Mandate, basis: str = "marginal", fee_scale: float = 1.0,
                   aum_path: np.ndarray | None = None) -> float:
    cf = cash_flows(m, fee_scale, aum_path)
    yrs = np.arange(1, m.years + 1)
    s = survival(m, yrs - 0.5)                                     # mid-year survival
    disc = (1 + m.discount_rate) ** -(yrs - 0.5)
    return float((s * cf[basis] * disc).sum() - m.onboarding)


def break_even_fee(m: Mandate, basis: str = "marginal", horizon: str = "year1") -> float:
    """Effective fee (bps on year-1 average AUM) at which profit = 0. The tiered schedule is scaled by a
    factor lambda (keeps its shape) and solved with Brent's method."""
    if horizon == "year1":
        f = lambda lam: cash_flows(m, lam)[basis][0]               # noqa: E731
    else:
        f = lambda lam: lifetime_value(m, basis, lam)              # noqa: E731
    lam = brentq(f, 1e-6, 50.0, xtol=1e-12)
    avg0 = cash_flows(m)["avg_aum"][0]
    return effective_bps(avg0, m.tiers, lam)


def min_viable_aum(m: Mandate, basis: str = "marginal") -> float:
    """Smallest initial AUM ($m) with year-1 profit >= 0 at the PROPOSED fee schedule."""
    f = lambda a: cash_flows(replace(m, initial_aum=a))[basis][0]    # noqa: E731
    if f(1e5) < 0:
        return float("inf")
    if f(1.0) >= 0:
        return 1.0
    return float(brentq(f, 1.0, 1e5, xtol=1e-6))


def monte_carlo_ltv(m: Mandate, n: int = 5000, mkt_mu: float = 0.06, mkt_sigma: float = 0.13,
                    flow_sigma: float = 0.05, seed: int = 11, basis: str = "fully_allocated") -> dict:
    """E[NPV] over random AUM paths: annual market return ~ N(mu, sigma) + organic flow noise."""
    rng = np.random.default_rng(seed)
    out = np.empty(n)
    for i in range(n):
        r = rng.normal(mkt_mu, mkt_sigma, m.years) + rng.normal(0.0, flow_sigma, m.years)
        end = m.initial_aum * np.cumprod(1 + np.clip(r, -0.6, 1.0))
        start = np.concatenate([[m.initial_aum], end[:-1]])
        out[i] = lifetime_value(m, basis, 1.0, (start + end) / 2)
    return dict(mean=float(out.mean()), p10=float(np.percentile(out, 10)), p50=float(np.percentile(out, 50)),
                p90=float(np.percentile(out, 90)), prob_loss=float((out < 0).mean()), draws=out)


def pricing_grid(m: Mandate, aums: list[float], fee_scales: list[float]) -> list[dict]:
    rows = []
    for a in aums:
        for s in fee_scales:
            mm = replace(m, initial_aum=a)
            cf = cash_flows(mm, s)
            rows.append(dict(aum=a, fee_scale=s, eff_bps=effective_bps(cf["avg_aum"][0], m.tiers, s),
                             marginal_y1=cf["marginal"][0], fully_allocated_y1=cf["fully_allocated"][0],
                             ltv_marginal=lifetime_value(mm, "marginal", s),
                             ltv_fully_allocated=lifetime_value(mm, "fully_allocated", s)))
    return rows


def recommend(m: Mandate, hurdle_margin: float = 0.15, competitor_band_bps: tuple[float, float] | None = None) -> dict:
    be_m = break_even_fee(m, "marginal")
    be_f = break_even_fee(m, "fully_allocated")
    floor, target = be_m, be_f * (1 + hurdle_margin)
    proposed = effective_bps(cash_flows(m)["avg_aum"][0], m.tiers)
    if proposed < floor:
        verdict = "REJECT - below marginal break-even (destroys value on any view)"
    elif proposed < be_f:
        verdict = "EXCEPTION ONLY - covers marginal cost but not fully allocated cost (strategic / capacity-filling case)"
    elif proposed < target:
        verdict = "APPROVE WITH CAUTION - above fully allocated break-even but below hurdle margin"
    else:
        verdict = "APPROVE - meets fully allocated break-even plus hurdle margin"
    return dict(proposed_bps=proposed, marginal_be_bps=be_m, fully_allocated_be_bps=be_f, floor_bps=floor,
                target_bps=target, verdict=verdict, competitor_band_bps=competitor_band_bps)


def tornado(m: Mandate, basis: str = "fully_allocated", shock: float = 0.2) -> list[dict]:
    base = lifetime_value(m, basis)
    rows = []
    specs = [("Fee schedule", lambda mm, k: (mm, 1 + k)), ("Initial AUM", lambda mm, k: (replace(mm, initial_aum=mm.initial_aum * (1 + k)), 1.0)),
             ("Termination hazard", lambda mm, k: (replace(mm, hazard_annual=min(0.9, mm.hazard_annual * (1 + k))), 1.0)),
             ("AUM growth", lambda mm, k: (replace(mm, growth_annual=mm.growth_annual + k * 0.1), 1.0)),
             ("Cost per FTE", lambda mm, k: (replace(mm, cost_per_fte=mm.cost_per_fte * (1 + k)), 1.0)),
             ("Allocated cost rate", lambda mm, k: (replace(mm, allocated_bps=mm.allocated_bps * (1 + k)), 1.0)),
             ("Discount rate", lambda mm, k: (replace(mm, discount_rate=mm.discount_rate + k * 0.05), 1.0))]
    for name, f in specs:
        lo_m, lo_s = f(m, -shock)
        hi_m, hi_s = f(m, +shock)
        rows.append(dict(driver=name, low=lifetime_value(lo_m, basis, lo_s) - base,
                         high=lifetime_value(hi_m, basis, hi_s) - base))
    rows.sort(key=lambda r: -max(abs(r["low"]), abs(r["high"])))
    return rows
