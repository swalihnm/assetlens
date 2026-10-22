# M7 Synthetic internal data

**Method.** Public GS AWM quarterly totals (revenue lines, provision, operating expenses) are allocated across 6 businesses, 5 cost pools and 4 regions by normalisation, so totals reproduce exactly. Advisors have logistic productivity ramps and books consistent with an assumed 85 bps fee yield; the general ledger posts monthly comp and vendor spend; T&E claims carry injected violations with ground-truth labels; savings initiatives have dependencies. Everything is seeded and parameterised in `config/synthetic.yaml`.

**Outputs.** `fact_business_pnl`, `fact_cost_pools`, `fact_drivers`, `fact_headcount`, 800 advisors / `fact_advisor_monthly`, `fact_gl` (2,599,992 rows), `fact_te` (201,179 claims, five violation types), 40 savings initiatives. Every table has `synthetic = true`.

**Results and validation.** Calibration tests: business revenue equals public net revenue within 0.5% each quarter, GL totals equal public operating expenses, advisor revenue equals PWM management fees, T&E violation rate 1-2.5%.

**Limitations.** Synthetic - illustrates method, not any company's internals. The business split, driver weights and pool shares are assumptions.
