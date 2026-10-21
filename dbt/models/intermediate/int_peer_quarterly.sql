-- one row per ticker x quarter with the metrics used by the benchmark
select ticker, period_end,
  max(case when metric in ('aum_end') then value end) as aum_end,
  max(case when metric = 'aum_begin' then value end) as aum_begin,
  max(case when metric = 'aum_avg' then value end) as aum_avg_reported,
  max(case when metric = 'net_flows' then value end) as net_flows,
  max(case when metric in ('rev_mgmt_other_fees','fees_base_sec_lending','fees_investment_advisory','fees_investment_management') then value end) as fees,
  max(case when metric = 'net_revenues' then value end) as net_revenues,
  max(case when metric in ('pretax_earnings','operating_income') then value end) as op_income,
  max(case when metric = 'opex' then value end) as opex,
  max(case when metric = 'comp_total' then value end) as comp
from {{ ref('stg_financials') }}
group by ticker, period_end
