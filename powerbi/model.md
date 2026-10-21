# Power BI semantic model and build guide

> Claude Code cannot emit a `.pbix`. Everything below lets you assemble the report in Power BI Desktop in about an hour.
> Data: `outputs/powerbi/*.csv|parquet` (run `make powerbi`). Power Query scripts: `powerbi/powerquery/*.m`. Measures: `powerbi/measures.dax`.
> **Business-unit, advisor, expense and compensation tables are SYNTHETIC** – keep "Synthetic data" in those page subtitles.

## 1. Load (≈10 min)
1. *Home → Transform data → New source → Blank query*, paste `00_parameters.m`, name it `FolderPath` and set the path to `outputs\powerbi\`.
2. For each file in `powerbi/powerquery/` create a blank query (Advanced Editor), paste, and name it after the file (`fact_benchmark`, …).
   `fact_gl` (2.6M rows) loads from Parquet; everything else from CSV.
3. *Close & Apply*.

## 2. Star schema and relationships

| From (many) | To (one) | Active | Note |
|---|---|---|---|
| `fact_benchmark[period_end]` | `dim_date[date]` | yes | quarter-end date |
| `fact_benchmark[ticker]` | `dim_company[ticker]` | yes | |
| `fact_forecast[period_end]` | `dim_date[date]` | yes | |
| `fact_forecast[scenario]` | `dim_scenario[scenario]` | yes | |
| `fact_budget[period_end]` | `dim_date[date]` | yes | |
| `fact_profitability[period_end]` | `dim_date[date]` | yes | |
| `fact_profitability[business]` | `dim_business[business]` | yes | |
| `fact_business_pnl[business]` / `[period_end]` | `dim_business` / `dim_date` | yes | |
| `fact_advisor_monthly[advisor_id]` | `dim_advisor[advisor_id]` | yes | |
| `fact_advisor_monthly[period_end]` | `dim_date[date]` | yes | |
| `dim_advisor[region]` | `dim_region[region]` | yes | |
| `fact_gl[posting_date]` | `dim_date[date]` | **yes** | role: posting date |
| `fact_gl[period_end]` | `dim_date[date]` | no | role: period end (use `USERELATIONSHIP`) |
| `fact_gl[vendor_id]` | `dim_vendor[vendor_id]` | yes | |
| `fact_gl[owner]` | `dim_business[business]` | yes | pools (`TECH`…) have no row – filter with `owner` |
| `fact_financials[period_end]` | `dim_date[date]` | yes | role: period end |
| `fact_financials[filed_date]` | `dim_date[date]` | **no** | role: filing date – **role-playing date dimension** |
| `fact_financials[metric]` | `dim_metric[metric]` | yes | |
| `fact_savings[initiative_id]` | `dim_initiative[initiative_id]` | yes | |

Mark `dim_date` as a date table (column `date`). Create the disconnected parameter table
`dim_allocation_method = DATATABLE("method", STRING, {{"revenue"},{"headcount"},{"abc"},{"step_down"},{"reciprocal"}})` for the method slicer.
Hide key columns, set summarisation to *Don't summarize* for ratios, add the measures from `measures.dax` into display folders as commented.

Filter-direction rule: single direction dimension → fact everywhere; no bi-directional filters.

## 3. Row-level security
`security_user_map(user_principal_name, business, region)` – "ALL" means unrestricted on that dimension.

| Role | Table | DAX filter |
|---|---|---|
| `BusinessHead` | `dim_business` | `[business] IN SELECTCOLUMNS( FILTER( security_user_map, security_user_map[user_principal_name] = USERPRINCIPALNAME() ), "b", security_user_map[business] ) \|\| CALCULATE( COUNTROWS( security_user_map ), security_user_map[user_principal_name] = USERPRINCIPALNAME(), security_user_map[business] = "ALL" ) > 0` |
| `RegionalCFO` | `dim_region` | same pattern on `region` |

Test with *View as → Other user* for two users: `business.head.pe@example.com` should see only Public Equity on page 4, and
`regional.cfo.emea@example.com` only EMEA advisors/cost. Replace the placeholder addresses with real UPNs in your tenant before publishing.
Public peer-benchmark pages (1–3) have no RLS because they contain only public data.

## 4. Pages and wireframes

```
Page 1  Executive Overview        KPI cards: GS AUS, fee yield T4Q, organic growth T4Q, pre-tax margin | line: AUS | scenario bars (FY pre-tax)
Page 2  Peer Benchmarking         Table (league + z-score) | scatter margin vs organic growth | line fee yield by ticker | stacked AUM change decomposition | comparability note box
Page 3  P&L Forecast & Scenarios  Scenario slicer | fan of net revenue (4 scenarios) | pre-tax margin line | waterfall: PVM fee bridge | stress case table
Page 4  Profitability by Business Method slicer | matrix business × (CM%, FA margin, rank) | bar: margin by method | flag table "loss-making only because of method"  [SYNTHETIC]
Page 5  Mandate Pricing           Parameter what-if (AUM, fee scale) | KPI: break-even fee marginal / fully allocated | heatmap fee × AUM | tornado (from Python export)
Page 6  Expense & Savings         Spend by category/vendor (Pareto) | budget vs actual | T&E flag rate | savings tracker target vs realised  [SYNTHETIC]
Page 7  Sales Productivity & Comp Revenue/advisor by cohort | Lorenz | NNA trend | comp ratio by business  [SYNTHETIC]
Page 8  Growth Markets            GCC case: AUM ramp, EBITDA, cumulative FCF, NPV/IRR cards (static from Excel Growth_Case export)
```
Core pages for the first release: 1–5.

## 5. Formatting standards
Neutral grey/blue palette, no third-party branding, 12-pt body, titles state the insight ("GS fee yield fell X bps in 4 years"), units in every title ($m, bps, %),
footer text box on every page: *"AssetLens is an independent educational project built from publicly available SEC filings and FRED data. Not affiliated with
or based on non-public information from any company named. Business-unit, headcount, advisor, expense and compensation data are synthetic. Nothing here is
investment advice."*

## 6. Validation
After load, compare the 11 values in `outputs/powerbi/dax_spot_checks.csv` against the cards/tables (tolerance ±0.01%). Record the result in `docs/modules/M15.md`.
Status at build time: **DAX not executed in Power BI Desktop** (no Windows Desktop automation here) – the expected values come from the DuckDB warehouse.

## 7. Optional
* PBIP/TMDL project: not generated (would be unverifiable without Desktop).
* Tableau Public: publish `fact_benchmark` (one sheet: margin vs organic growth scatter) to claim Tableau legitimately.
