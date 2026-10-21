with a as (
  select period_end, method, business, sum(allocated_musd) as allocated_musd
  from {{ ref('stg_allocation') }} group by 1, 2, 3)
select a.period_end, a.method, a.business, p.net_revenues, p.contribution_margin, a.allocated_musd,
       p.contribution_margin - a.allocated_musd as fully_allocated_pretax,
       (p.contribution_margin - a.allocated_musd) / p.net_revenues as fully_allocated_margin
from a join {{ ref('stg_business_pnl') }} p using (period_end, business)
