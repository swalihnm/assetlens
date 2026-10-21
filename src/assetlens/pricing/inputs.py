"""Pull mandate-pricing cost inputs from the synthetic M7/M8 tables and the competitor band from M4."""
from __future__ import annotations

import duckdb

from assetlens.warehouse.build import DB

CLASS_TO_BUSINESS = {"equity": ("PE", "aus_equity"), "fixed_income": ("FIMA", "aus_fixed_income"),
                     "liquidity": ("LIQ", "aus_liquidity"), "alternatives": ("ALT", "aus_alternatives")}


def defaults(asset_class: str = "equity") -> dict:
    biz, aus_metric = CLASS_TO_BUSINESS[asset_class]
    con = duckdb.connect(str(DB), read_only=True)
    last4 = con.execute("select distinct period_end from fact_business_pnl order by 1 desc limit 4").df().period_end.tolist()
    q = ",".join(f"'{x}'" for x in last4)
    alloc = con.execute(f"""select sum(allocated_musd) a from fact_allocation
                            where method='abc' and business='{biz}' and period_end in ({q})""").fetchone()[0]
    fo = con.execute(f"""select sum(direct_comp+direct_noncomp) c from fact_business_pnl
                         where business='{biz}' and period_end in ({q})""").fetchone()[0]
    hc = con.execute(f"""select avg(h) from (select period_end, sum(headcount) h from fact_headcount
                         where business='{biz}' and period_end in ({q}) group by 1)""").fetchone()[0]
    avg_aus = con.execute(f"""select avg(value) from fact_financials where ticker='GS' and metric='{aus_metric}'
                              and period_end in ({q})""").fetchone()[0]
    band = con.execute("""select min(fee_yield_t4q_bps), max(fee_yield_t4q_bps) from mart_peer_benchmark
                          where period_end=(select max(period_end) from mart_peer_benchmark where ticker='GS'
                          and fee_yield_t4q_bps is not null) and fee_yield_t4q_bps is not null""").fetchone()
    con.close()
    return dict(cost_per_fte=fo / hc if hc else 0.45,                         # $m per FO head per year
                allocated_bps=alloc / avg_aus * 1e4, competitor_band_bps=tuple(round(x, 1) for x in band))
