"""M17 - finance question eval set (gold SQL executed against the warehouse). Categories: lookup, rank, scenario,
allocation, stats (covered by the template baseline's patterns) and hard (multi-step / paraphrased)."""
from __future__ import annotations

from assetlens.ai.text2sql import EvalItem

NAMES = {"GS": "Goldman Sachs", "BLK": "BlackRock", "TROW": "T. Rowe", "IVZ": "Invesco"}
MET = [("fee yield", "fee_yield_t4q_bps"), ("organic growth", "organic_growth_t4q"), ("AUM", "aum_end")]
BIZ = {"public equity": "PE", "fixed income": "FIMA", "liquidity": "LIQ", "alternatives": "ALT", "private wealth": "PWM", "private banking": "PBL"}


def items() -> list[EvalItem]:
    out: list[EvalItem] = []
    for t, n in NAMES.items():
        for lab, col in MET:
            out.append(EvalItem(f"What is the latest {lab} for {n}?",
                                f"select {col} from mart_peer_benchmark where ticker='{t}' and {col} is not null order by period_end desc limit 1", "lookup"))
    for t in ("BLK", "TROW", "IVZ"):
        out.append(EvalItem(f"What is the latest comp ratio for {NAMES[t]}?",
                            f"select comp_ratio_t4q from mart_peer_benchmark where ticker='{t}' and comp_ratio_t4q is not null order by period_end desc limit 1", "lookup"))
    for t, n in NAMES.items():
        out.append(EvalItem(f"What was the AUM of {n} in Q2 2026?", f"select aum_end from mart_peer_benchmark where ticker='{t}' and period_end='2026-06-30'", "lookup"))
        out.append(EvalItem(f"What were the net flows of {n} in Q1 2026?", f"select net_flows from mart_peer_benchmark where ticker='{t}' and period_end='2026-03-31'", "lookup"))
    for lab, col in [("fee yield", "fee_yield_t4q_bps"), ("organic growth", "organic_growth_t4q"), ("margin", "op_margin_t4q")]:
        for word, order in [("highest", "desc"), ("lowest", "asc")]:
            out.append(EvalItem(f"Which company has the {word} {lab}?",
                                f"select ticker from mart_peer_benchmark where {col} is not null and period_end=(select max(period_end) from mart_peer_benchmark b2 "
                                f"where b2.ticker=mart_peer_benchmark.ticker and b2.{col} is not null) order by {col} {order} limit 1", "rank"))
    for s in ("base", "bull", "bear", "stress"):
        out.append(EvalItem(f"What is the pre-tax margin in the {s} scenario at quarter 8?", f"select pretax_margin from fact_forecast where scenario='{s}' and t=8", "scenario"))
        out.append(EvalItem(f"What are net revenues in the {s} scenario forecast at quarter 8?", f"select net_revenues from fact_forecast where scenario='{s}' and t=8", "scenario"))
    out.append(EvalItem("What are pre-tax earnings in the base scenario at quarter 4?", "select pretax from fact_forecast where scenario='base' and t=4", "scenario"))
    out.append(EvalItem("What are pre-tax earnings in the bear scenario at quarter 4?", "select pretax from fact_forecast where scenario='bear' and t=4", "scenario"))
    for n, b in BIZ.items():
        out.append(EvalItem(f"What is the rank of {n} under the abc method?", f"select rank from mart_allocation_rank_sensitivity where method='abc' and business='{b}'", "allocation"))
    out.append(EvalItem("What is the margin of liquidity under the revenue method?", "select margin from mart_allocation_rank_sensitivity where method='revenue' and business='LIQ'", "allocation"))
    out.append(EvalItem("What is the margin of liquidity under the abc method?", "select margin from mart_allocation_rank_sensitivity where method='abc' and business='LIQ'", "allocation"))
    out.append(EvalItem("Show the margin by business under the reciprocal method", "select business, margin from mart_allocation_rank_sensitivity where method='reciprocal' order by margin desc", "allocation"))
    for t, n in NAMES.items():
        out.append(EvalItem(f"What is the fee compression slope for {n}?", f"select ticker, slope_bps_per_year from mart_fee_compression where ticker='{t}' order by slope_bps_per_year", "stats"))
    out.append(EvalItem("What is the Monte Carlo probability of the margin falling below the threshold?", "select margin_below_threshold_q8 from mart_montecarlo_prob", "stats"))
    out.append(EvalItem("Show the backtest MAPE by model", "select model, avg(mape) as mape from mart_backtest_summary group by model order by mape", "stats"))
    for t in ("BLK", "TROW"):
        out.append(EvalItem(f"What is the equity and bond beta for {NAMES[t]}?", f"select beta_equity, beta_bond from mart_market_sensitivity where ticker='{t}'", "stats"))
    out.append(EvalItem("What is the total savings target?", "select sum(target_savings_musd) as target from fact_savings", "stats"))
    # hard: multi-step / paraphrase - the baseline is not expected to solve most of these
    hard = [
        ("How many quarters did GS have net outflows?", "select count(*) from mart_peer_benchmark where ticker='GS' and net_flows < 0"),
        ("Which peer saw the biggest fall in T4Q fee yield over the last year?",
         "with l as (select ticker, fee_yield_t4q_bps y, period_end, row_number() over (partition by ticker order by period_end desc) r from mart_peer_benchmark where fee_yield_t4q_bps is not null) "
         "select a.ticker from l a join l b on a.ticker=b.ticker and a.r=1 and b.r=5 order by a.y-b.y asc limit 1"),
        ("What was BlackRock's average quarterly organic growth in 2024?", "select avg(organic_growth_ann) from mart_peer_benchmark where ticker='BLK' and period_end between '2024-01-01' and '2024-12-31'"),
        ("Total net flows of Invesco since 2023?", "select sum(net_flows) from mart_peer_benchmark where ticker='IVZ' and period_end >= '2023-01-01'"),
        ("What share of savings initiatives have confidence above 0.8?", "select avg(case when confidence > 0.8 then 1.0 else 0 end) from fact_savings"),
        ("Which owner has the largest savings target?", "select owner from fact_savings group by owner order by sum(target_savings_musd) desc limit 1"),
        ("What is revenue per advisor in EMEA in the latest quarter?", "select revenue_per_advisor from mart_sales_productivity where region='EMEA' order by period_end desc limit 1"),
        ("Which scenario has the lowest cumulative pre-tax earnings over eight quarters?", "select scenario from fact_forecast group by scenario order by sum(pretax) asc limit 1"),
        ("What is the combined latest AUM of GS and BlackRock?", "select sum(aum_end) from (select aum_end, row_number() over (partition by ticker order by period_end desc) r from mart_peer_benchmark where ticker in ('GS','BLK')) where r=1"),
        ("List tickers with a statistically significant fee compression trend", "select ticker from mart_fee_compression where significant order by ticker"),
        ("What is the average fully allocated margin of alternatives across all methods?", "select avg(margin) from mart_allocation_rank_sensitivity where business='ALT'"),
        ("How much did the stress case lose in pre-tax earnings versus base at quarter 8?", "select (select pretax from fact_forecast where scenario='base' and t=8) - (select pretax from fact_forecast where scenario='stress' and t=8)"),
    ]
    out += [EvalItem(q, s, "hard") for q, s in hard]
    return out


ADVERSARIAL = [  # every one must be rejected by the validator
    "drop table fact_forecast", "delete from fact_savings", "select * from fact_gl", "select * from read_csv('/etc/passwd')",
    "select 1; drop table mart_peer_benchmark", "update fact_savings set confidence = 1", "copy fact_forecast to 'x.csv'",
    "select * from mart_peer_benchmark cross join fact_forecast", "attach 'other.db'", "select * from information_schema.tables",
    "insert into fact_savings values (1)", "pragma database_list", "select * from fact_te", "create table t as select 1",
    "select * from main.mart_peer_benchmark", "select * from read_parquet('x.parquet')", "install httpfs",
]
