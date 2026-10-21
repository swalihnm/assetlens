-- begin + flows + market + other = end, for tickers that disclose all lines (GS, TROW, IVZ)
with p as (
  select ticker, period_end,
    max(case when metric = 'aum_begin' then value end) as b,
    max(case when metric = 'net_flows' then value end) as f,
    max(case when metric = 'market' then value end) as m,
    coalesce(max(case when metric = 'aum_other_change' then value end), 0) + coalesce(max(case when metric = 'acquisitions' then value end), 0) as o,
    max(case when metric = 'aum_end' then value end) as e
  from {{ ref('stg_financials') }} group by 1, 2)
select * from p where b is not null and f is not null and m is not null and e is not null and ticker <> 'BLK'
  and abs(b + f + m + o - e) > greatest(0.0006 * e, 400)
