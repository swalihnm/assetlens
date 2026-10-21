"""M5 - how market-driven AUM change responds to equity and bond returns (OLS, HC3 robust), rolling betas,
asset-mix sanity check and lending-revenue sensitivity to the policy rate."""
from __future__ import annotations

from pathlib import Path

import duckdb
import matplotlib
import numpy as np
import pandas as pd
import statsmodels.api as sm

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from assetlens.warehouse.build import DB

ROOT = Path(__file__).resolve().parents[3]
EQ, BOND = "SP500_ret", "BOND_PROXY"
DURATION = 6.5   # approx. modified duration of the IG corporate index (assumption)


def load() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    con = duckdb.connect(str(DB), read_only=True)
    b = con.execute("select ticker, period_end, market_impact_pct, aum_begin, aum_end from mart_peer_benchmark").df()
    m = con.execute("select * from fact_market").df()
    f = con.execute("select ticker, metric, period_end, value from fact_financials where ticker='GS'").df()
    con.close()
    b["period_end"] = pd.to_datetime(b.period_end)
    m["period_end"] = pd.to_datetime(m.period_end)
    f["period_end"] = pd.to_datetime(f.period_end)
    # FRED serves only ~3 years of ICE BofA total-return history, so build a duration proxy from the 10y yield:
    # r = y_start/4 - D * dy  (quarter-end yields)
    from assetlens.ingest import fred
    y = fred.fetch("DGS10")["DGS10"].resample("QE").last() / 100
    proxy = (y.shift(1) / 4 - DURATION * y.diff()).rename("BOND_PROXY")
    m = m.merge(proxy.rename_axis("period_end").reset_index(), on="period_end", how="left")
    return b, m, f


def fit(y: pd.Series, X: pd.DataFrame):
    return sm.OLS(y, sm.add_constant(X)).fit(cov_type="HC3")


def run() -> dict:
    b, m, f = load()
    m = m.set_index("period_end")
    rows, models = [], {}
    for t, g in b.groupby("ticker"):
        d = g.set_index("period_end").join(m[[EQ, BOND]]).dropna(subset=["market_impact_pct", EQ, BOND])
        d = d[d.index >= "2019-03-31"]
        if len(d) < 12:
            continue
        res = fit(d.market_impact_pct, d[[EQ, BOND]])
        ci = res.conf_int()
        models[t] = (res, d)
        rows.append(dict(ticker=t, n=len(d), beta_equity=res.params[EQ], eq_ci_low=ci.loc[EQ, 0], eq_ci_high=ci.loc[EQ, 1],
                         beta_bond=res.params[BOND], bd_ci_low=ci.loc[BOND, 0], bd_ci_high=ci.loc[BOND, 1],
                         alpha_q=res.params["const"], r2=res.rsquared,
                         dw=float(sm.stats.durbin_watson(res.resid)),
                         note="BLK impact = residual incl. FX/acquisitions (GIP/HPS 2024-25)" if t == "BLK" else ""))
    out = pd.DataFrame(rows)
    both = m.dropna(subset=["BAMLCC0A0CMTRIV_ret", BOND])
    proxy_corr = float(both["BAMLCC0A0CMTRIV_ret"].corr(both[BOND])) if len(both) > 4 else float("nan")
    # rolling 12-quarter equity beta (extension)
    roll = []
    for t, (res, d) in models.items():
        for i in range(12, len(d) + 1):
            w = d.iloc[i - 12:i]
            r = sm.OLS(w.market_impact_pct, sm.add_constant(w[[EQ, BOND]])).fit()
            roll.append(dict(ticker=t, period_end=w.index[-1], beta_equity=r.params[EQ], beta_bond=r.params[BOND]))
    roll = pd.DataFrame(roll)
    # asset-mix sanity for GS: disclosed AUS mix vs implied exposure
    p = f.pivot_table(index="period_end", columns="metric", values="value", aggfunc="first")
    mix = (p[["aus_equity", "aus_alternatives", "aus_fixed_income", "aus_liquidity"]].div(p.aum_end, axis=0)
           .dropna().iloc[-1])
    gs_beta = out[out.ticker == "GS"].iloc[0]
    sanity = dict(bond_proxy_corr_with_ice=proxy_corr, bond_proxy_overlap_quarters=len(both), disclosed_equity_share=float(mix.aus_equity), disclosed_alt_share=float(mix.aus_alternatives),
                  disclosed_fi_share=float(mix.aus_fixed_income), disclosed_liquidity_share=float(mix.aus_liquidity),
                  implied_equity_beta=float(gs_beta.beta_equity), implied_bond_beta=float(gs_beta.beta_bond),
                  expected_equity_beta_range=(float(mix.aus_equity), float(mix.aus_equity + mix.aus_alternatives)))
    # lending revenue vs policy rate (GS PBL, QoQ growth on change in avg fed funds)
    con = duckdb.connect(str(DB), read_only=True)
    dff = con.execute("select period_end, DFF_avg from fact_market").df()
    con.close()
    dff["period_end"] = pd.to_datetime(dff.period_end)
    pbl = p["rev_private_banking_lending"].dropna()
    z = pd.DataFrame({"pbl_qoq": pbl.pct_change()}).join(dff.set_index("period_end").DFF_avg.diff().rename("d_dff")).dropna()
    lend = fit(z.pbl_qoq, z[["d_dff"]])
    sanity["pbl_beta_per_1pp_policy_rate"] = float(lend.params["d_dff"])
    sanity["pbl_beta_p"] = float(lend.pvalues["d_dff"])
    sanity["pbl_n"] = len(z)
    # diagnostics plot
    fig, axes = plt.subplots(1, len(models), figsize=(3.4 * len(models), 3.1), dpi=160, sharey=True)
    fig.patch.set_facecolor("#fcfcfb")
    for ax, (t, (res, d)) in zip(np.atleast_1d(axes), models.items()):
        ax.scatter(res.fittedvalues * 100, res.resid * 100, s=14, color="#2a78d6")
        ax.axhline(0, color="#52514e", lw=0.8)
        ax.set_title(f"{t}: residuals vs fitted (%)", fontsize=8, loc="left")
        ax.tick_params(labelsize=7)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
    fig.tight_layout()
    (ROOT / "outputs" / "charts").mkdir(parents=True, exist_ok=True)
    fig.savefig(ROOT / "outputs" / "charts" / "market_residuals.png", facecolor="#fcfcfb")
    plt.close(fig)
    con = duckdb.connect(str(DB))
    for name, df in [("mart_market_sensitivity", out), ("mart_market_beta_rolling", roll)]:
        con.register("x", df)
        con.execute(f"create or replace table {name} as select * from x")
        con.unregister("x")
    con.close()
    return dict(betas=out, sanity=sanity)


if __name__ == "__main__":
    pd.set_option("display.width", 250)
    r = run()
    print(r["betas"].round(3).to_string())
    print(r["sanity"])
