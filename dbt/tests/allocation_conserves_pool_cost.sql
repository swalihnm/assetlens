-- for every method and quarter the allocated total must equal the pool cost total
with a as (select period_end, method, sum(allocated_musd) as alloc from {{ ref('stg_allocation') }} group by 1, 2),
     p as (select cast(period_end as date) as period_end, sum(cost) as pool from {{ source('raw', 'fact_cost_pools') }} group by 1)
select * from a join p using (period_end) where abs(a.alloc - p.pool) > 0.001
