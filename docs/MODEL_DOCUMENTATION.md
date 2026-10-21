# Model documentation

## Purpose and scope
AssetLens benchmarks Goldman Sachs' Asset & Wealth Management (AWM) segment against BlackRock, T. Rowe Price and Invesco from public SEC filings; forecasts the AWM P&L with a driver-based model; reports fully allocated profitability; prices new mandates on a marginal basis; and evaluates a GCC private wealth office. Educational project; no non-public data is used.

## Data
* Public: SEC EDGAR 10-K/10-Q and 8-K Exhibit 99.1 (HTML tables, provenance per fact in `fact_provenance`), FRED market series.
* Synthetic (`synthetic = true`): business-unit P&L, cost pools, headcount, advisors, GL (2.6M rows), T&E (200k), savings initiatives. Calibrated so revenue lines, provision and operating expenses equal the public GS AWM quarterly totals (`tests/test_synth.py`).

## Methodology
1. **Extraction**: deterministic table parsers; AUM roll-forwards accepted only if begin + flows + market + other = end (tolerance max(0.35, 0.05% of end) in table units) and chained with the previous quarter.
2. **Benchmark**: metrics in METRICS.md; comparability flags per company.
3. **Forecast**: per asset class AUM_t = AUM_{t-1}(1+r) + g/4 x AUM_{t-1}; fees = average AUM x yield / 4 with yield compression; incentive fees = rate x average alternatives AUS x quarterly seasonality x scenario multiplier; PBL via a rate-sensitive margin; Investments scenario-scaled; Comp = max(floor, ratio x revenue); non-comp fixed + variable; provision scenario-scaled. Class yields are relative assumptions scaled so the base quarter's fees are reproduced.
4. **Allocation**: revenue, headcount, ABC (driver shares), step-down (fixed order), reciprocal (T = (I - A^T)^-1 D).
5. **Pricing**: annual model, tiered schedule, Weibull survival, break-evens verified in Excel by closed form.
6. **Growth case**: advisor cohorts with logistic ramp, seven years plus Gordon terminal value.

## Validation results
* GS segment reconciliation: 19/19 on each check (`RECONCILIATION_REPORT.md`).
* Forecast engine reproduces Q2-2026 management fees within -3.1% given realised balances (tolerance 5%).
* PVM and expense bridges sum exactly (property tests); allocations conserve cost (property tests); fully allocated pre-tax reconciles to public segment pre-tax.
* Excel vs Python parity: max relative error about 1e-15 across 4 scenarios, mandate pricing and growth case; no Excel error cells (`excel/parity.py`).
* 31 automated tests (`make test-all`).

## Limitations
* GS AWM quarterly series starts 2022 Q1 (perimeter re-base); Q3-2026 opex and pre-tax pending the 10-Q.
* BLK market impact is a residual; IVZ fees are gross; TROW has two missing roll-forward quarters.
* GS class-level fee yields are assumed (not disclosed). Scenario paths and growth-case inputs are assumptions, not forecasts.
* Synthetic businesses are illustrative; conclusions about them are not statements about Goldman Sachs.
* Power BI DAX not executed; no PDF of the deck (no LibreOffice on the build machine).

## Monitoring / change log
* 2026-10-21 v1.0 Phase 1 build. After each new filing re-run `make extract warehouse benchmark synth allocate forecast excel powerbi deck` and review `RECONCILIATION_REPORT.md`.
