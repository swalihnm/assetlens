select cast(period_end as date) as period_end, method, pool, business, allocated_musd, synthetic
from {{ source('raw', 'fact_allocation') }}
