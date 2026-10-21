"""M6 Phase 2 - Monte Carlo: block bootstrap of joint (equity, bond) quarterly returns -> fan charts of net revenue,
pre-tax earnings and margin, and the probability that margin falls below a threshold.

Vectorised re-implementation of `engine.run_scenario` (equivalence unit-tested for deterministic inputs).
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import matplotlib
import numpy as np
import pandas as pd

from assetlens.forecast.engine import CFG, CLASSES, Base, calibrate_yields, load_base
from assetlens.warehouse.build import DB

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[3]
H = CFG["horizon_quarters"]


def historical_returns() -> pd.DataFrame:
    """Joint quarterly (equity, bond-proxy) returns. Equity history is the FRED S&P 500 window (~2016 on)."""
    from assetlens.market.sensitivity import BOND, EQ, load
    _, m, _ = load()
    return m.set_index("period_end")[[EQ, BOND]].dropna().rename(columns={EQ: "eq", BOND: "bond"})


def block_bootstrap(hist: pd.DataFrame, n: int, block: int = 2, seed: int = 42) -> tuple[np.ndarray, np.ndarray]:
    """Moving-block bootstrap (preserves cross-correlation and short-range dependence). Returns (n, H) arrays."""
    rng = np.random.default_rng(seed)
    arr = hist.values
    T = len(arr)
    nblocks = int(np.ceil(H / block))
    starts = rng.integers(0, T - block + 1, size=(n, nblocks))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]).reshape(n, -1)[:, :H]
    draws = arr[idx]
    return draws[:, :, 0], draws[:, :, 1]


def simulate(eq: np.ndarray, bond: np.ndarray, b: Base, scenario: str = "base", shocks: dict | None = None) -> dict[str, np.ndarray]:
    """eq, bond: (N, H) quarterly returns. Deterministic (shocks=None) path equals engine.run_scenario."""
    N = eq.shape[0]
    sc = CFG["scenarios"][scenario]
    y0 = calibrate_yields(b)
    aus = {k: np.full(N, b.aus[k]) for k in CLASSES}
    comp_base = CFG["comp_ratio_target"] * b.netrev_avg
    floor = CFG["comp_fixed_floor_share"] * comp_base
    fixed_nc = (b.opex_avg - comp_base) - CFG["noncomp_variable_rate"] * b.netrev_avg
    inc_rate = b.incentive_t4q / b.alt_avg_t4q
    nim0, beta = CFG["pbl"]["nim0"], CFG["pbl"]["nim_beta_to_short_rate"]
    r0 = CFG["scenarios"]["base"]["short_rate"][0]
    out = {k: np.zeros((N, H)) for k in ("net_revenues", "pretax", "margin", "comp", "aus_total", "mgmt_fees")}
    cum_eq = np.zeros(N)
    for t in range(1, H + 1):
        pe = pd.Timestamp(b.quarter) + pd.offsets.QuarterEnd(t)
        qn = pe.quarter
        prev = {k: v.copy() for k, v in aus.items()}
        fees = np.zeros(N)
        avg_alt = None
        for k in CLASSES:
            ac = CFG["asset_classes"][k]
            r = ac["equity_beta"] * eq[:, t - 1] + ac["carry_q"] + (bond[:, t - 1] if k == "fixed_income" else 0.0)
            g = sc["organic_annual"][k] + (shocks["organic"][:, t - 1] if shocks else 0.0)
            aus[k] = prev[k] * (1 + r) + g / 4 * prev[k]
            y = y0[k] * (1 - CFG["fee_compression_annual"][k]) ** (0.25 * t)
            avg = (prev[k] + aus[k]) / 2
            fees += avg * y / 4
            if k == "alternatives":
                avg_alt = avg
        cum_eq = (1 + cum_eq) * (1 + eq[:, t - 1]) - 1
        inc_mult = sc["incentive_mult"] * (shocks["incentive"][:, t - 1] if shocks else 1.0)
        incentive = inc_rate * avg_alt * CFG["incentive_seasonality"][qn - 1] * inc_mult
        pbl = b.pbl * (1 + CFG["pbl"]["loan_growth_annual"]) ** (t / 4) * (1 + beta * (sc["short_rate"][t - 1] - r0) / nim0)
        inv = b.investments_avg * sc["investments_mult"] * (shocks["investments"][:, t - 1] if shocks else 1.0)
        rev = fees + incentive + pbl + inv
        comp = np.maximum(floor, CFG["comp_ratio_target"] * rev)
        nc = fixed_nc * (1 + CFG["inflation_annual"]) ** (t / 4) + CFG["noncomp_variable_rate"] * rev
        prov = b.provision_avg * sc["provision_mult"]
        pt = rev - comp - nc - prov
        for k, v in dict(net_revenues=rev, pretax=pt, margin=pt / rev, comp=comp, mgmt_fees=fees,
                         aus_total=sum(aus.values())).items():
            out[k][:, t - 1] = v
    return out


def stochastic_shocks(eq: np.ndarray, n: int, seed: int = 7) -> dict[str, np.ndarray]:
    """Link lumpy revenue lines and flows to the market path (assumptions documented in DECISIONS.md)."""
    rng = np.random.default_rng(seed)
    cum = np.cumprod(1 + eq, axis=1) - 1
    return dict(
        organic=0.5 * eq * 4 + rng.normal(0, 0.02, (n, H)),                      # flows chase markets + noise
        incentive=np.clip((1 + 2.0 * cum) * np.exp(rng.normal(0, 0.45, (n, H))), 0.05, None),
        investments=np.clip(1 + 4.0 * eq + rng.normal(0, 0.6, (n, H)), -1.0, None))


def run(n: int = 10_000, threshold: float = 0.25, seed: int = 42) -> dict:
    hist = historical_returns()
    eq, bond = block_bootstrap(hist, n, seed=seed)
    b = load_base()
    res = simulate(eq, bond, b, "base", stochastic_shocks(eq, n))
    qs = [10, 50, 90]
    rows = []
    for t in range(H):
        for name in ("net_revenues", "pretax", "margin"):
            p = np.percentile(res[name][:, t], qs)
            rows.append(dict(t=t + 1, metric=name, p10=p[0], p50=p[1], p90=p[2]))
    fan = pd.DataFrame(rows)
    prob = dict(margin_below_threshold_q8=float((res["margin"][:, -1] < threshold).mean()),
                margin_below_threshold_any=float((res["margin"] < threshold).any(axis=1).mean()),
                threshold=threshold, n=n, hist_quarters=len(hist),
                pretax_8q_p10=float(np.percentile(res["pretax"].sum(axis=1), 10)),
                pretax_8q_p50=float(np.percentile(res["pretax"].sum(axis=1), 50)),
                pretax_8q_p90=float(np.percentile(res["pretax"].sum(axis=1), 90)))
    con = duckdb.connect(str(DB))
    con.register("x", fan)
    con.execute("create or replace table mart_montecarlo_fan as select * from x")
    con.register("y", pd.DataFrame([prob]))
    con.execute("create or replace table mart_montecarlo_prob as select * from y")
    con.close()
    # fan chart (net revenue and margin)
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.6), dpi=170)
    fig.patch.set_facecolor("#fcfcfb")
    for ax, name, scale, lab in [(axes[0], "net_revenues", 1e-3, "Net revenues ($bn)"), (axes[1], "margin", 100, "Pre-tax margin (%)")]:
        d = fan[fan.metric == name]
        ax.fill_between(d.t, d.p10 * scale, d.p90 * scale, color="#2a78d6", alpha=0.18, lw=0)
        ax.plot(d.t, d.p50 * scale, color="#2a78d6", lw=2)
        ax.set_title(lab + ": P10-P50-P90", fontsize=9, loc="left")
        ax.tick_params(labelsize=8)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
    axes[1].axhline(threshold * 100, color="#eb6834", lw=1, ls="--")
    axes[1].text(1, threshold * 100 + 0.3, f"{threshold:.0%} threshold", fontsize=7, color="#52514e")
    fig.text(0.01, 0.01, "Block-bootstrapped returns; scenario/assumption-driven; not a forecast. AssetLens educational project.", fontsize=6)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(ROOT / "outputs" / "charts" / "montecarlo_fan.png", facecolor="#fcfcfb")
    plt.close(fig)
    return dict(fan=fan, prob=prob)


if __name__ == "__main__":
    r = run()
    pd.set_option("display.width", 200)
    print(r["fan"][r["fan"].t.isin([1, 4, 8])].round(3).to_string())
    print(r["prob"])
