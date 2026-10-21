"""M6 Phase 2 - rolling-origin backtest of GS AWM management & other fees, horizons 1-4, last 8 origins.

Models: driver model with assumed market returns (unconditional), driver model fed REALISED market returns
(conditional: isolates model error from market error), naive, seasonal naive, drift. No look-ahead: at each origin
only data up to that quarter (balances, flows, fees) is used. Runs are logged to a local MLflow store.
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import yaml

from assetlens.forecast.engine import CFG, CLASSES
from assetlens.warehouse.build import DB

ROOT = Path(__file__).resolve().parents[3]
CLS = {"alternatives": "aus_alternatives", "equity": "aus_equity", "fixed_income": "aus_fixed_income", "liquidity": "aus_liquidity"}
FLOW = {"alternatives": "flow_alternatives", "equity": "flow_equity", "fixed_income": "flow_fixed_income", "liquidity": "flow_liquidity"}
UNCOND = dict(eq=0.02, bond=0.01)          # assumed long-run quarterly returns for the unconditional model
HORIZONS = (1, 2, 3, 4)


def data() -> tuple[pd.DataFrame, pd.DataFrame]:
    from assetlens.market.sensitivity import BOND, EQ, load
    _, m, _ = load()
    mk = m.set_index("period_end")[[EQ, BOND]].rename(columns={EQ: "eq", BOND: "bond"})
    con = duckdb.connect(str(DB), read_only=True)
    f = con.execute("select period_end, metric, value from fact_financials where ticker='GS'").df()
    con.close()
    w = f.pivot_table(index="period_end", columns="metric", values="value", aggfunc="first").sort_index()
    w.index = pd.to_datetime(w.index)
    w = w[w.index >= "2022-03-31"]
    return w, mk


def model_fees(w: pd.DataFrame, mk: pd.DataFrame, origin: pd.Timestamp, h: int, conditional: bool) -> float:
    """Management fees at origin+h using only information available at `origin`."""
    hist = w[w.index <= origin]
    prev, cur = hist.iloc[-2], hist.iloc[-1]
    rel = {k: CFG["asset_classes"][k]["rel_yield"] for k in CLASSES}
    avg0 = {k: (prev[CLS[k]] + cur[CLS[k]]) / 2 for k in CLASSES}
    s = cur.rev_mgmt_other_fees * 4 / sum(rel[k] * avg0[k] for k in CLASSES)
    # trailing-4Q organic growth by class (annualised), from information up to origin
    g = {}
    for k in CLASSES:
        flows = hist[FLOW[k]].tail(4)
        beg = hist[CLS[k]].shift(1).tail(4)
        g[k] = float((flows * 4 / beg).mean())
    aus = {k: cur[CLS[k]] for k in CLASSES}
    dates = [origin + pd.offsets.QuarterEnd(i) for i in range(1, h + 1)]
    fees = 0.0
    for i, d in enumerate(dates, 1):
        prevb = dict(aus)
        if conditional:
            eq, bd = mk.loc[d, "eq"], mk.loc[d, "bond"]
        else:
            eq, bd = UNCOND["eq"], UNCOND["bond"]
        fees = 0.0
        for k in CLASSES:
            ac = CFG["asset_classes"][k]
            r = ac["equity_beta"] * eq + ac["carry_q"] + (bd if k == "fixed_income" else 0.0)
            aus[k] = prevb[k] * (1 + r) + g[k] / 4 * prevb[k]
            y = s * rel[k] * (1 - CFG["fee_compression_annual"][k]) ** (0.25 * i)
            fees += (prevb[k] + aus[k]) / 2 * y / 4
    return fees


def baselines(w: pd.DataFrame, origin: pd.Timestamp, h: int) -> dict[str, float]:
    y = w.rev_mgmt_other_fees[w.index <= origin]
    naive = y.iloc[-1]
    seasonal = y.iloc[-4 + (h - 1) % 4 - 0] if len(y) >= 4 else naive
    seasonal = y.iloc[len(y) - 4 + ((h - 1) % 4)] if len(y) >= 4 else naive    # same quarter last year
    drift = y.iloc[-1] + h * (y.iloc[-1] - y.iloc[0]) / (len(y) - 1)
    return dict(naive=naive, seasonal_naive=seasonal, drift=drift)


def run(n_origins: int = 8, log_mlflow: bool = True) -> dict:
    w, mk = data()
    actual = w.rev_mgmt_other_fees
    last_obs = actual.index[-1]
    origins = [d for d in actual.index if d + pd.offsets.QuarterEnd(1) <= last_obs][-n_origins:]
    rows = []
    for o in origins:
        for h in HORIZONS:
            tgt = o + pd.offsets.QuarterEnd(h)
            if tgt not in actual.index:
                continue
            a = actual[tgt]
            preds = dict(model_assumed_mkt=model_fees(w, mk, o, h, False), model_realised_mkt=model_fees(w, mk, o, h, True),
                         **baselines(w, o, h))
            for name, p in preds.items():
                rows.append(dict(origin=o, horizon=h, model=name, actual=a, forecast=p, error=p - a, ape=abs(p - a) / a))
    d = pd.DataFrame(rows)
    summ = d.groupby(["model", "horizon"]).agg(mape=("ape", "mean"), bias=("error", lambda e: e.mean()), n=("ape", "size")).reset_index()
    tot = d.groupby("model").agg(mape=("ape", "mean"), n=("ape", "size")).reset_index()
    best_naive = tot[tot.model.isin(["naive", "seasonal_naive", "drift"])].mape.min()
    for_mlflow = dict(tot.set_index("model").mape)
    if log_mlflow:
        import mlflow
        mlflow.set_tracking_uri("sqlite:///" + (ROOT / "data" / "mlflow.db").as_posix())
        mlflow.set_experiment("assetlens_backtest")
        with mlflow.start_run(run_name="gs_awm_mgmt_fees"):
            mlflow.log_params(dict(origins=len(origins), horizons=str(HORIZONS), uncond_eq=UNCOND["eq"], uncond_bond=UNCOND["bond"]))
            mlflow.log_metrics({f"mape_{k}": float(v) for k, v in for_mlflow.items()})
            mlflow.log_metric("improvement_vs_best_naive_conditional",
                              float(1 - for_mlflow["model_realised_mkt"] / best_naive))
    con = duckdb.connect(str(DB))
    for name, df in [("mart_backtest_errors", d), ("mart_backtest_summary", summ)]:
        con.register("x", df)
        con.execute(f"create or replace table {name} as select * from x")
        con.unregister("x")
    con.close()
    return dict(detail=d, summary=summ, total=tot, best_naive_mape=float(best_naive),
                conditional_improvement=float(1 - for_mlflow["model_realised_mkt"] / best_naive),
                unconditional_improvement=float(1 - for_mlflow["model_assumed_mkt"] / best_naive))


if __name__ == "__main__":
    pd.set_option("display.width", 200)
    r = run()
    print(r["summary"].pivot(index="model", columns="horizon", values="mape").round(4))
    print(r["total"].round(4))
    print({k: round(v, 3) for k, v in r.items() if k.endswith(("improvement", "mape"))})
