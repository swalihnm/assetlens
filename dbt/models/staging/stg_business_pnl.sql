select business, cast(period_end as date) as period_end, mgmt_fees, incentive_fees, pbl, investments,
       net_revenues, direct_comp, direct_noncomp, provision, contribution_margin, synthetic
from {{ source('raw', 'fact_business_pnl') }}
