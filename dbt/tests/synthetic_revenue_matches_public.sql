with s as (select period_end, sum(net_revenues) as syn from {{ ref('stg_business_pnl') }} group by 1),
     f as (select period_end, max(value) as pub from {{ ref('stg_financials') }} where ticker = 'GS' and metric = 'net_revenues' group by 1)
select * from s join f using (period_end) where abs(s.syn / f.pub - 1) > 0.005
