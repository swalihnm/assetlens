"""M18 - FastAPI: benchmarks, forecast, mandate pricing, allocation, growth case. Read-only over the warehouse."""
from __future__ import annotations

from dataclasses import replace

import duckdb
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from assetlens.growth import business_case as GC
from assetlens.pricing import inputs as pin
from assetlens.pricing import mandate as PM
from assetlens.warehouse.build import DB

app = FastAPI(title="AssetLens API", version="1.0",
              description="Educational project on public SEC/FRED data; business-unit data synthetic; not investment advice.")


def clean(x):
    """JSON-safe: NaN/inf -> None, numpy -> python."""
    import math

    import numpy as np
    if isinstance(x, dict):
        return {k: clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [clean(v) for v in x]
    if isinstance(x, np.ndarray):
        return clean(x.tolist())
    if isinstance(x, np.generic):
        x = x.item()
    if isinstance(x, float) and not math.isfinite(x):
        return None
    return x


def q(sql: str, params: list | None = None):
    con = duckdb.connect(str(DB), read_only=True)
    try:
        return con.execute(sql, params or []).df()
    finally:
        con.close()


@app.get("/benchmarks")
def benchmarks(ticker: str | None = None, latest_only: bool = True):
    sql = "select * from mart_peer_benchmark"
    p: list = []
    if ticker:
        sql += " where ticker = ?"
        p.append(ticker.upper())
    df = q(sql + " order by ticker, period_end", p)
    if latest_only:
        df = df.sort_values("period_end").groupby("ticker").tail(1)
    return clean(df.astype({"period_end": str}).to_dict("records"))


@app.get("/forecast")
def forecast(scenario: str = "base"):
    df = q("select * from fact_forecast where scenario = ? order by t", [scenario])
    if df.empty:
        raise HTTPException(404, "scenario must be one of base, bull, bear, stress")
    return clean(df.astype({"period_end": str}).to_dict("records"))


class MandateIn(BaseModel):
    asset_class: str = "equity"
    initial_aum: float = Field(1000.0, gt=0, description="$m")
    tiers: list[tuple[float, float]] = Field([(250, 40), (500, 32), (1e12, 24)], description="(upper bound $m, bps)")
    growth_annual: float = 0.06
    hazard_annual: float = Field(0.08, gt=0, lt=1)
    weibull_shape: float = 1.0
    pm_fte: float = 0.6
    service_fte: float = 0.3
    seed_capital: float = 0.0
    hurdle_margin: float = 0.15


@app.post("/mandate/price")
def mandate_price(m: MandateIn):
    d = pin.defaults(m.asset_class)
    mm = replace(PM.Mandate(), asset_class=m.asset_class, initial_aum=m.initial_aum, tiers=list(m.tiers),
                 growth_annual=m.growth_annual, hazard_annual=m.hazard_annual, weibull_shape=m.weibull_shape,
                 pm_fte=m.pm_fte, service_fte=m.service_fte, seed_capital=m.seed_capital,
                 cost_per_fte=d["cost_per_fte"], allocated_bps=d["allocated_bps"])
    rec = PM.recommend(mm, m.hurdle_margin, d["competitor_band_bps"])
    mc = PM.monte_carlo_ltv(mm, n=1000)
    return clean(dict(recommendation=rec,
                lifetime_value=dict(marginal=PM.lifetime_value(mm, "marginal"), fully_allocated=PM.lifetime_value(mm, "fully_allocated")),
                min_viable_aum=dict(marginal=PM.min_viable_aum(mm, "marginal"), fully_allocated=PM.min_viable_aum(mm, "fully_allocated")),
                monte_carlo={k: v for k, v in mc.items() if k != "draws"}, tornado=PM.tornado(mm),
                inputs_from_warehouse=d, synthetic_cost_inputs=True))


@app.get("/allocation")
def allocation(method: str = "abc"):
    df = q("select period_end, business, net_revenues, contribution_margin, allocated_musd, fully_allocated_pretax, "
           "fully_allocated_margin from mart_profitability_by_business where method = ? order by period_end, business", [method])
    if df.empty:
        raise HTTPException(404, "method must be revenue, headcount, abc, step_down or reciprocal")
    return clean(df.astype({"period_end": str}).to_dict("records"))


@app.get("/growth-case")
def growth_case(location: str = "DIFC"):
    if location not in GC.CFG["locations"]:
        raise HTTPException(404, f"location must be one of {list(GC.CFG['locations'])}")
    r = GC.run(location)
    return clean(r)
