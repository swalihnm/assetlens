"""Static charts (matplotlib) following the dataviz skill: fixed categorical slots per entity, thin marks,
direct labels + legend, recessive grid, neutral surface. Colours validated with validate_palette.js."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import duckdb
import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from assetlens.growth import business_case as GC  # noqa: E402
from assetlens.pricing import inputs as pin  # noqa: E402
from assetlens.pricing import mandate as PM  # noqa: E402
from assetlens.warehouse.build import DB  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "outputs" / "charts"
SURF, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e5e1"
COL = {"GS": "#2a78d6", "BLK": "#eb6834", "TROW": "#1baf7a", "IVZ": "#eda100", "MS": "#e87ba4", "JPM": "#6250d6", "BEN": "#008300"}   # fixed slot per entity
SCN = {"bull": "#1baf7a", "base": "#2a78d6", "bear": "#eb6834", "stress": "#52514e"}
DISC = "AssetLens: independent educational project, public SEC/FRED data; business-unit data synthetic; not investment advice."


def _ax(w=7.6, h=3.9, title=""):
    fig, ax = plt.subplots(figsize=(w, h), dpi=200)
    fig.patch.set_facecolor(SURF)
    ax.set_facecolor(SURF)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.grid(axis="y", color=GRID, lw=0.7)
    ax.tick_params(colors=INK2, labelsize=8)
    if title:
        ax.set_title(title, loc="left", fontsize=10.5, color=INK, fontweight="bold")
    return fig, ax


def _save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.text(0.01, 0.005, DISC, fontsize=5.5, color=INK2)
    fig.tight_layout(rect=(0, 0.02, 1, 1))
    p = OUT / f"{name}.png"
    fig.savefig(p, facecolor=SURF)
    plt.close(fig)
    return p


def _q(sql):
    con = duckdb.connect(str(DB), read_only=True)
    try:
        return con.execute(sql).df()
    finally:
        con.close()


def make_all() -> dict[str, Path]:
    b = _q("select * from mart_peer_benchmark")
    b["period_end"] = pd.to_datetime(b.period_end)
    out = {}
    # 1 indexed AUM
    fig, ax = _ax(title="AUM / AUS indexed to Mar-2022 = 100")
    for t, g in b[b.period_end >= "2022-03-31"].groupby("ticker"):
        g = g.dropna(subset=["aum_end"]).sort_values("period_end")
        y = g.aum_end / g.aum_end.iloc[0] * 100
        ax.plot(g.period_end, y, color=COL[t], lw=2, marker="o", ms=3)
        ax.annotate(f"{t} {y.iloc[-1]:.0f}", (g.period_end.iloc[-1], y.iloc[-1]), xytext=(4, 0),
                    textcoords="offset points", fontsize=8, color=INK, va="center")
    ax.set_xlim(right=b.period_end.max() + pd.Timedelta(days=170))
    out["aum_indexed"] = _save(fig, "aum_indexed")
    # 2 fee yield
    fig, ax = _ax(title="Fee yield, trailing four quarters (bps)")
    for t, g in b.dropna(subset=["fee_yield_t4q_bps"]).groupby("ticker"):
        g = g.sort_values("period_end")
        ax.plot(g.period_end, g.fee_yield_t4q_bps, color=COL[t], lw=2, marker="o", ms=3)
        ax.annotate(f"{t} {g.fee_yield_t4q_bps.iloc[-1]:.1f}", (g.period_end.iloc[-1], g.fee_yield_t4q_bps.iloc[-1]),
                    xytext=(4, 0), textcoords="offset points", fontsize=8, color=INK, va="center")
    ax.set_xlim(right=b.period_end.max() + pd.Timedelta(days=170))
    out["fee_yield"] = _save(fig, "fee_yield")
    # 3 scatter margin vs organic growth (latest T4Q with both)
    last = b.dropna(subset=["op_margin_t4q", "organic_growth_t4q"]).sort_values("period_end").groupby("ticker").tail(1)
    fig, ax = _ax(5.6, 3.9, "Operating margin vs organic growth (T4Q, latest)")
    for r in last.itertuples():
        ax.scatter(r.organic_growth_t4q * 100, r.op_margin_t4q * 100, s=90, color=COL[r.ticker], edgecolor=SURF, lw=1.5, zorder=3)
        ax.annotate(f"{r.ticker} ({str(r.period_end)[:7]})", (r.organic_growth_t4q * 100, r.op_margin_t4q * 100), xytext=(7, 4),
                    textcoords="offset points", fontsize=8)
    ax.set_xlabel("Organic growth, T4Q (%)", fontsize=8, color=INK2)
    ax.set_ylabel("Operating margin, T4Q (%)", fontsize=8, color=INK2)
    out["scatter"] = _save(fig, "margin_vs_growth")
    # 4 GS waterfall since Mar-2022
    d = _q("select * from mart_aum_decomposition where ticker='GS'").iloc[0]
    fig, ax = _ax(5.6, 3.9, "GS AUS change since Dec-2021 ($bn)")
    vals = [d.aum_begin / 1e3, d.net_flows / 1e3, d.market_fx_other / 1e3, d.aum_end / 1e3]
    labs = ["Dec-21 AUS", "Net flows", "Market & other", "Sep-26 AUS"]
    bottoms = [0, vals[0], vals[0] + vals[1], 0]
    heights = [vals[0], vals[1], vals[2], vals[3]]
    cols = [INK2, COL["GS"], COL["TROW"], INK2]
    for i in range(4):
        ax.bar(i, heights[i], bottom=bottoms[i], color=cols[i], width=0.55)
        ax.text(i, bottoms[i] + heights[i] + 40, f"{heights[i]:,.0f}", ha="center", fontsize=8)
    ax.set_xticks(range(4), labs)
    out["waterfall"] = _save(fig, "gs_aus_waterfall")
    # 5 scenario margin
    f = _q("select * from fact_forecast")
    fig, ax = _ax(title="Forecast pre-tax margin by scenario (GS AWM)")
    for s, g in f.groupby("scenario"):
        g = g.sort_values("t")
        ax.plot(g.t, g.pretax_margin * 100, color=SCN[s], lw=2, marker="o", ms=3)
        ax.annotate(f"{s} {g.pretax_margin.iloc[-1] * 100:.1f}%", (8, g.pretax_margin.iloc[-1] * 100), xytext=(5, 0),
                    textcoords="offset points", fontsize=8, va="center")
    ax.set_xlabel("Quarters after Q3-2026", fontsize=8, color=INK2)
    ax.set_xlim(1, 9.6)
    out["scenarios"] = _save(fig, "scenario_margin")
    # 6 profitability by method
    p = _q("select * from mart_allocation_rank_sensitivity")
    piv = p.pivot(index="business", columns="method", values="margin") * 100
    piv = piv[["revenue", "headcount", "abc", "reciprocal"]]
    fig, ax = _ax(7.6, 3.9, "Fully allocated margin by allocation method, T4Q (%) - synthetic split")
    x = np.arange(len(piv))
    cols = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
    for i, m in enumerate(piv.columns):
        ax.bar(x + (i - 1.5) * 0.2, piv[m], width=0.18 - 0.02, color=cols[i], label=m)
    ax.axhline(0, color=INK2, lw=0.8)
    ax.set_xticks(x, piv.index)
    ax.legend(fontsize=7, frameon=False, ncol=4, loc="lower right")
    out["methods"] = _save(fig, "margin_by_method")
    # 7 mandate pricing
    dflt = pin.defaults("equity")
    m = replace(PM.Mandate(), cost_per_fte=dflt["cost_per_fte"], allocated_bps=dflt["allocated_bps"])
    r = PM.recommend(m, competitor_band_bps=dflt["competitor_band_bps"])
    fig, ax = _ax(6.4, 3.4, "Mandate fee vs break-evens (bps) - $1bn equity SMA")
    labs = ["Marginal\nbreak-even", "Fully allocated\nbreak-even", "Target (+15%)", "Proposed"]
    v = [r["marginal_be_bps"], r["fully_allocated_be_bps"], r["target_bps"], r["proposed_bps"]]
    ax.bar(range(4), v, color=[INK2, INK2, COL["TROW"], COL["GS"]], width=0.5)
    for i, x_ in enumerate(v):
        ax.text(i, x_ + 0.5, f"{x_:.1f}", ha="center", fontsize=8)
    ax.axhspan(*dflt["competitor_band_bps"], color=COL["IVZ"], alpha=0.15)
    ax.text(3.45, dflt["competitor_band_bps"][1], "peer fee-yield band", fontsize=7, ha="right", va="bottom", color=INK2)
    ax.set_xticks(range(4), labs)
    out["mandate"] = _save(fig, "mandate_breakeven")
    # 8 GCC FCF
    g = GC.run()
    fig, ax = _ax(6.4, 3.4, "GCC private wealth office - cumulative free cash flow ($m)")
    cum = np.cumsum(g["fcf"])
    ax.plot(range(len(cum)), cum, color=COL["GS"], lw=2, marker="o", ms=4)
    ax.axhline(0, color=INK2, lw=0.8)
    ax.set_xlabel("Year", fontsize=8, color=INK2)
    out["gcc"] = _save(fig, "gcc_cumulative_fcf")
    return out


if __name__ == "__main__":
    print(make_all())
