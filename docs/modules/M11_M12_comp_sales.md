# M11-M12 Compensation and sales analytics

**Method.** Compensation: peer comp ratios plus Goldman AWM annual segment comp ratio (FY2022-25, from the ASU 2023-07 disclosure); accrual model (variable pool accrued at the YTD target ratio, Q4 true-up to the final pool, fixed/variable split); scenario sensitivity of pool and margin; pay-for-performance regression on synthetic advisor comp; pool allocation by revenue vs contribution. Sales: advisor KPIs by region, quota attainment, cohort ramp curves, time to productivity, Lorenz/Gini, synthetic pipeline funnel, four-quarter NNA forecast (damped exponential smoothing with bootstrap intervals).

**Outputs.** `comp/analysis.py`, `sales/analytics.py`, tables `fact_comp`, `mart_sales_productivity`, `mart_cohort_ramp`, `fact_pipeline`, `mart_nna_forecast`.

**Results and validation.** GS AWM comp ratio 44.3% / 43.1% / 40.2% / 44.6% (FY2022-25). Accrual and Q4 true-up reconcile to the annual pool (property test). Regression recovers the planted 28% advisor payout (coefficient 0.279, R2 0.98). Advisor revenue Gini 0.51, top 10% of advisors = 37% of revenue, time to productivity about 1 year.

**Limitations.** Advisor, pipeline and comp data are synthetic; the pipeline leads NNA by construction, so its R2 is not a finding.
