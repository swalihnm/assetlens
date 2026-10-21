"""M6 - driver-based quarterly P&L forecast (deterministic scenarios).

AUM[t,k] = AUM[t-1,k] (1 + r[t,k]) + Flows[t,k];  Flows = g_k/4 * AUM[t-1,k]
MgmtFees[t] = sum_k avgAUM[t,k] * y[t,k] / 4;     y[t,k] = y[t-1,k] (1-c_k)^(1/4)
Comp = max(fixed floor, target ratio * NetRevenue);  NonComp = fixed*(1+infl) + variable_rate * NetRevenue
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import duckdb
import pandas as pd
import yaml

from assetlens.warehouse.build import DB

ROOT = Path(__file__).resolve().parents[3]
CFG = yaml.safe_load((ROOT / "config" / "scenarios.yaml").read_text())
CLASSES = list(CFG["asset_classes"])


@dataclass
class Base:
    quarter: pd.Timestamp
    aus_prev: dict[str, float]      # AUS by class at base-1 quarter end
    aus: dict[str, float]           # AUS by class at base quarter end
    mgmt_fees: float
    pbl: float
    investments_avg: float
    incentive_t4q: float
    provision_avg: float
    opex_avg: float
    netrev_avg: float
    alt_avg_t4q: float


def load_base() -> Base:
    con = duckdb.connect(str(DB), read_only=True)
    f = con.execute("select period_end, metric, value from fact_financials where ticker='GS'").df()
    con.close()
    w = f.pivot_table(index="period_end", columns="metric", values="value", aggfunc="first").sort_index()
    w.index = pd.to_datetime(w.index)
    t0 = pd.Timestamp(CFG["start_after"])
    prev = w.index[w.index.get_loc(t0) - 1]
    cls = {"alternatives": "aus_alternatives", "equity": "aus_equity", "fixed_income": "aus_fixed_income",
           "liquidity": "aus_liquidity"}
    have_opex = w.dropna(subset=["opex"]).index
    bp = have_opex[-4:]                                  # last four quarters with a full P&L
    last4 = w.index[-4:]
    alt_end = w["aus_alternatives"]
    return Base(
        quarter=t0, aus_prev={k: float(w.loc[prev, v]) for k, v in cls.items()},
        aus={k: float(w.loc[t0, v]) for k, v in cls.items()},
        mgmt_fees=float(w.loc[t0, "rev_mgmt_other_fees"]), pbl=float(w.loc[t0, "rev_private_banking_lending"]),
        investments_avg=float(w["rev_investments"].dropna().iloc[-8:].mean()),
        incentive_t4q=float(w.loc[last4, "rev_incentive_fees"].sum()),
        provision_avg=float(w.loc[bp, "provision"].mean()),
        opex_avg=float(w.loc[bp, "opex"].mean()), netrev_avg=float(w.loc[bp, "net_revenues"].mean()),
        alt_avg_t4q=float(((alt_end + alt_end.shift(1)) / 2).loc[last4].mean()))


def calibrate_yields(b: Base) -> dict[str, float]:
    """Annual fee yield by class (fraction): scale * relative yield so base-quarter fees are reproduced."""
    avg = {k: (b.aus[k] + b.aus_prev[k]) / 2 for k in CLASSES}
    denom = sum(CFG["asset_classes"][k]["rel_yield"] * avg[k] for k in CLASSES)
    s = b.mgmt_fees * 4 / denom
    return {k: s * CFG["asset_classes"][k]["rel_yield"] for k in CLASSES}


def run_scenario(name: str, b: Base | None = None, overrides: dict | None = None) -> pd.DataFrame:
    b = b or load_base()
    sc = {**CFG["scenarios"][name], **(overrides or {})}
    H = CFG["horizon_quarters"]
    y = calibrate_yields(b)
    aus = dict(b.aus)
    comp_base = CFG["comp_ratio_target"] * b.netrev_avg
    floor = CFG["comp_fixed_floor_share"] * comp_base
    fixed_nc = (b.opex_avg - comp_base) - CFG["noncomp_variable_rate"] * b.netrev_avg
    inc_rate = b.incentive_t4q / b.alt_avg_t4q                      # annual incentive / avg alternatives AUS
    pbl_nim0, beta = CFG["pbl"]["nim0"], CFG["pbl"]["nim_beta_to_short_rate"]
    r0 = CFG["scenarios"]["base"]["short_rate"][0]
    rows = []
    for t in range(1, H + 1):
        pe = (b.quarter + pd.offsets.QuarterEnd(t))
        qn = pe.quarter
        prev = dict(aus)
        eq, bond = sc["equity_ret_q"][t - 1], sc["bond_ret_q"][t - 1]
        for k in CLASSES:
            ac = CFG["asset_classes"][k]
            r = ac["equity_beta"] * eq + ac["carry_q"] + (bond if k == "fixed_income" else 0.0)
            flows = sc["organic_annual"][k] / 4 * prev[k]
            aus[k] = prev[k] * (1 + r) + flows
            y[k] *= (1 - CFG["fee_compression_annual"][k]) ** 0.25
        avg = {k: (prev[k] + aus[k]) / 2 for k in CLASSES}
        fees = sum(avg[k] * y[k] / 4 for k in CLASSES)
        incentive = inc_rate * avg["alternatives"] * CFG["incentive_seasonality"][qn - 1] * sc["incentive_mult"]
        sr = sc["short_rate"][t - 1]
        loan_g = (1 + CFG["pbl"]["loan_growth_annual"]) ** (t / 4)
        pbl = b.pbl * loan_g * (1 + beta * (sr - r0) / pbl_nim0)
        inv = b.investments_avg * sc["investments_mult"]
        net_rev = fees + incentive + pbl + inv
        comp = max(floor, CFG["comp_ratio_target"] * net_rev)
        noncomp = fixed_nc * (1 + CFG["inflation_annual"]) ** (t / 4) + CFG["noncomp_variable_rate"] * net_rev
        prov = b.provision_avg * sc["provision_mult"]
        pretax = net_rev - comp - noncomp - prov
        core_rev = net_rev - inv
        rows.append(dict(
            scenario=name, period_end=pe, t=t, **{f"aus_{k}": aus[k] for k in CLASSES},
            aus_total=sum(aus.values()), net_flows=sum(sc["organic_annual"][k] / 4 * prev[k] for k in CLASSES),
            mgmt_fees=fees, incentive_fees=incentive, private_banking_lending=pbl, investments=inv,
            net_revenues=net_rev, comp=comp, noncomp=noncomp, provision=prov, pretax=pretax,
            pretax_margin=pretax / net_rev, core_pretax_margin=(pretax - inv) / core_rev,
            fee_yield_bps=fees * 4 / sum(avg.values()) * 1e4, comp_ratio=comp / net_rev,
            **{f"yield_{k}_bps": y[k] * 1e4 for k in CLASSES}))
    return pd.DataFrame(rows)


def reproduce_quarter(period: str = "2026-06-30") -> dict:
    """Acceptance test: feed REALISED flows/market for a reported quarter, compare fees with the actual."""
    con = duckdb.connect(str(DB), read_only=True)
    f = con.execute("select period_end, metric, value from fact_financials where ticker='GS'").df()
    con.close()
    w = f.pivot_table(index="period_end", columns="metric", values="value", aggfunc="first").sort_index()
    pe = pd.Timestamp(period)
    idx = list(pd.to_datetime(w.index))
    cur, prev, prev2 = (w.iloc[idx.index(pe)], w.iloc[idx.index(pe) - 1], w.iloc[idx.index(pe) - 2])
    cls = {"alternatives": "aus_alternatives", "equity": "aus_equity", "fixed_income": "aus_fixed_income",
           "liquidity": "aus_liquidity"}
    # yields calibrated on the PREVIOUS quarter, applied to this quarter's realised average balances
    b_prev = Base(pe, {k: prev2[v] for k, v in cls.items()}, {k: prev[v] for k, v in cls.items()},
                  prev.rev_mgmt_other_fees, 0, 0, 0, 0, 0, 0, 0)
    y = calibrate_yields(b_prev)
    avg = {k: (prev[v] + cur[v]) / 2 for k, v in cls.items()}
    fees = sum(avg[k] * y[k] / 4 for k in CLASSES)
    return dict(period=period, model_fees=fees, actual_fees=cur.rev_mgmt_other_fees,
                error_pct=fees / cur.rev_mgmt_other_fees - 1)


def run_all() -> pd.DataFrame:
    b = load_base()
    df = pd.concat([run_scenario(s, b) for s in CFG["scenarios"]], ignore_index=True)
    df["synthetic"] = False
    con = duckdb.connect(str(DB))
    con.register("x", df)
    con.execute("create or replace table fact_forecast as select * from x")
    con.close()
    return df


if __name__ == "__main__":
    pd.set_option("display.width", 250)
    d = run_all()
    print(reproduce_quarter())
    s = d.groupby("scenario").apply(lambda g: pd.Series(dict(
        rev_Q8=g.net_revenues.iloc[-1], pretax_8q=g.pretax.sum(), margin_Q8=g.pretax_margin.iloc[-1],
        aus_Q8=g.aus_total.iloc[-1])), include_groups=False)
    print(s.round(3))
