select scenario, t, cast(period_end as date) as period_end, net_revenues, comp, noncomp, provision, pretax, pretax_margin
from {{ source('raw', 'fact_forecast') }}
