select f.fact_id, f.ticker, f.unit, f.metric, cast(f.period_end as date) as period_end, f.value,
       p.accession_no, p.form_type, cast(p.filed_date as date) as filed_date, p.method, p.locator
from {{ source('raw', 'fact_financials') }} f
join {{ source('raw', 'fact_provenance') }} p using (fact_id)
