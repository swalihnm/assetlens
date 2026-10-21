"""M8 - allocation of shared cost pools to businesses: revenue, headcount, ABC, step-down, reciprocal.

Pure-numpy kernels (`*_alloc`) return a (pools x businesses) matrix whose columns sum to the pool cost
(conservation - property-tested). `run()` applies them to the synthetic warehouse tables.
"""
from __future__ import annotations

import duckdb
import numpy as np
import pandas as pd

from assetlens.warehouse.build import DB

METHODS = ["revenue", "headcount", "abc", "step_down", "reciprocal"]
STEP_ORDER = ["PREM", "FHL", "TECH", "OPS", "RISK"]  # most-shared-first (assumption, documented)


def direct_alloc(cost: np.ndarray, shares: np.ndarray) -> np.ndarray:
    """cost: (P,), shares: (B,) or (P,B) rows summing to 1 -> (P,B)."""
    s = np.atleast_2d(shares)
    s = np.broadcast_to(s, (len(cost), s.shape[1]))
    return cost[:, None] * s


def reciprocal_alloc(cost: np.ndarray, usage: np.ndarray, bus_shares: np.ndarray) -> np.ndarray:
    """usage[i, j] = share of provider i's output consumed by pool j (i != j); remainder goes to businesses
    in proportion to bus_shares[i, :]. Solves T = (I - A^T)^-1 D (simultaneous equations)."""
    P = len(cost)
    T = np.linalg.solve(np.eye(P) - usage.T, cost)
    to_bus = 1.0 - usage.sum(axis=1)
    return (T * to_bus)[:, None] * bus_shares


def step_down_alloc(cost: np.ndarray, usage: np.ndarray, bus_shares: np.ndarray,
                    order: list[int]) -> np.ndarray:
    """Sequential: each pool, in `order`, allocates its accumulated cost to LATER pools and businesses;
    usage by earlier pools is ignored (renormalised) - the defining limitation of step-down."""
    P, B = bus_shares.shape
    acc = cost.astype(float).copy()
    out = np.zeros((P, B))
    done: set[int] = set()
    for i in order:
        later = [j for j in order if j not in done and j != i]
        w_pool = {j: usage[i, j] for j in later}
        w_bus = (1.0 - usage[i].sum()) * bus_shares[i]
        tot = sum(w_pool.values()) + w_bus.sum()
        for j, w in w_pool.items():
            acc[j] += acc[i] * w / tot
        out[i] = acc[i] * w_bus / tot
        done.add(i)
    return out


def load() -> dict[str, pd.DataFrame]:
    con = duckdb.connect(str(DB), read_only=True)
    t = {n: con.execute(f"select * from {n}").df() for n in
         ["fact_business_pnl", "fact_cost_pools", "fact_drivers", "dim_support_usage", "fact_headcount"]}
    con.close()
    return t


def run() -> pd.DataFrame:
    t = load()
    pnl, pools, drv, use, hc = (t["fact_business_pnl"], t["fact_cost_pools"], t["fact_drivers"],
                                t["dim_support_usage"], t["fact_headcount"])
    pool_ids = list(pools.pool.unique())
    biz = list(pnl.business.unique())
    U = use.pivot(index="provider", columns="user", values="share").reindex(index=pool_ids, columns=pool_ids).fillna(0).values
    order = [pool_ids.index(p) for p in STEP_ORDER]
    rows = []
    for pe in sorted(pnl.period_end.unique()):
        cost = pools[pools.period_end == pe].set_index("pool").reindex(pool_ids).cost.values
        rev = pnl[pnl.period_end == pe].set_index("business").reindex(biz).net_revenues.values
        h = hc[(hc.period_end == pe) & (hc.business != "SHARED")].groupby("business").headcount.sum().reindex(biz).values
        d = drv[drv.period_end == pe].pivot(index="pool", columns="business", values="quantity").reindex(index=pool_ids, columns=biz)
        abc = (d.values / d.values.sum(axis=1, keepdims=True))
        mats = {
            "revenue": direct_alloc(cost, rev / rev.sum()),
            "headcount": direct_alloc(cost, h / h.sum()),
            "abc": direct_alloc(cost, abc),
            "step_down": step_down_alloc(cost, U, abc, order),
            "reciprocal": reciprocal_alloc(cost, U, abc),
        }
        for m, mat in mats.items():
            for i, p in enumerate(pool_ids):
                for j, b in enumerate(biz):
                    rows.append((pe, m, p, b, mat[i, j]))
    fa = pd.DataFrame(rows, columns=["period_end", "method", "pool", "business", "allocated_musd"])
    fa["synthetic"] = True
    return fa


def profitability(fa: pd.DataFrame, pnl: pd.DataFrame) -> pd.DataFrame:
    alloc = fa.groupby(["period_end", "method", "business"]).allocated_musd.sum().reset_index()
    base = pnl[["period_end", "business", "net_revenues", "direct_comp", "direct_noncomp", "provision",
                "contribution_margin"]]
    m = alloc.merge(base, on=["period_end", "business"])
    m["fully_allocated_pretax"] = m.contribution_margin - m.allocated_musd
    m["contribution_margin_pct"] = m.contribution_margin / m.net_revenues
    m["fully_allocated_margin"] = m.fully_allocated_pretax / m.net_revenues
    m["synthetic"] = True
    return m


def rank_sensitivity(prof: pd.DataFrame, last_n: int = 4) -> pd.DataFrame:
    qs = sorted(prof.period_end.unique())[-last_n:]
    g = prof[prof.period_end.isin(qs)].groupby(["method", "business"]).agg(
        revenue=("net_revenues", "sum"), pretax=("fully_allocated_pretax", "sum")).reset_index()
    g["margin"] = g.pretax / g.revenue
    g["rank"] = g.groupby("method").margin.rank(ascending=False).astype(int)
    return g


def save(fa: pd.DataFrame, prof: pd.DataFrame, rk: pd.DataFrame) -> None:
    con = duckdb.connect(str(DB))
    for name, df in [("fact_allocation", fa), ("mart_profitability_by_business", prof),
                     ("mart_allocation_rank_sensitivity", rk)]:
        con.register("x", df)
        con.execute(f"create or replace table {name} as select * from x")
        con.unregister("x")
    con.close()


if __name__ == "__main__":
    fa = run()
    pnl = load()["fact_business_pnl"]
    prof = profitability(fa, pnl)
    rk = rank_sensitivity(prof)
    save(fa, prof, rk)
    piv = rk.pivot(index="business", columns="method", values="rank")
    print(piv)
    print(rk.pivot(index="business", columns="method", values="margin").round(3))
