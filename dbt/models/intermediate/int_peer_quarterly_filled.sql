select *,
  coalesce(aum_begin, lag(aum_end) over (partition by ticker order by period_end)) as aum_begin_f
from {{ ref('int_peer_quarterly') }}
