with b as (
  select *, coalesce(aum_avg_reported, (aum_begin_f + aum_end) / 2) as aum_avg
  from {{ ref('int_peer_quarterly_filled') }}
)
select ticker, period_end, aum_end, aum_avg, fees, net_flows, net_revenues, op_income,
  fees * 4 / aum_avg * 10000 as fee_yield_bps,
  net_flows * 4 / aum_begin_f as organic_growth_ann,
  op_income / net_revenues as op_margin,
  comp / net_revenues as comp_ratio
from b
