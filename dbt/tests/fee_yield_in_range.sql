select * from {{ ref('mart_peer_benchmark_sql') }} where fee_yield_bps is not null and fee_yield_bps not between 1 and 100
