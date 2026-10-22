# AssetLens - project record (for résumé, LinkedIn and interviews)

_Owner: Abdulla Swalih NM · Repo: https://github.com/swalihnm/assetlens (public, MIT) · Last updated: 2026-10-22_
_Target role: Goldman Sachs - AWM Management, F&S, Analyst, Bengaluru (https://higher.gs.com/roles/184192)_

---

## Links

* **GitHub repository:** https://github.com/swalihnm/assetlens
* **Clone:** `git clone https://github.com/swalihnm/assetlens.git`
* **CI status:** https://github.com/swalihnm/assetlens/actions
* **Board pack (PDF):** https://github.com/swalihnm/assetlens/blob/main/outputs/deck/AssetLens_Board_Pack.pdf
* **Excel model:** https://github.com/swalihnm/assetlens/blob/main/outputs/excel/AssetLens_PnL_Model.xlsx
* **Model documentation:** https://github.com/swalihnm/assetlens/blob/main/docs/MODEL_DOCUMENTATION.md
* **Target role posting:** https://higher.gs.com/roles/184192

## 1. One-paragraph summary (use as the project blurb)

AssetLens is an end-to-end FP&A and strategic-finance analytics platform for asset and wealth management. It ingests public SEC filings for Goldman Sachs' Asset & Wealth Management segment and six peers (BlackRock, T. Rowe Price, Invesco, Morgan Stanley Investment Management, JPMorgan Asset & Wealth Management, Franklin Resources), benchmarks their operating results, forecasts the P&L with a driver-based model under bull/base/bear/stress scenarios and Monte Carlo, reports fully allocated profitability by business using five cost-allocation methods, prices new mandates on a marginal basis, evaluates a Gulf wealth-office expansion case, and delivers everything through a live-formula Excel model, Power BI assets, a board pack, a Streamlit app, a FastAPI service and a text-to-SQL / RAG assistant. Internal-style data (business costs, advisors, expenses, compensation) is synthetic and calibrated to public segment totals; everything public is traceable to an SEC accession number.

**Short version (one line):** "Built an SEC-filings-driven FP&A platform benchmarking 7 asset managers, with a driver-based P&L forecast, cost-allocation and mandate-pricing engines, a live-formula Excel model, Power BI/Streamlit/API delivery and an AI SQL assistant."

## 2. Scale at a glance (all verified in the repo)

| Item | Number |
|---|---|
| Companies benchmarked | 7 (GS AWM, BLK, TROW, IVZ, MS IM, JPM AWM, BEN), 30-31 quarters each (2019-2026) |
| SEC filings indexed | 1,071 (10-K, 10-Q, 8-K) across 8 CIKs (BlackRock's two CIKs stitched) |
| Provenance-tagged public facts | 2,505 in `fact_financials` (accession no., table locator, raw text, method, retrieval time) |
| Goldman restatement rows logged | 262 |
| Warehouse | DuckDB, about 40 tables; dbt project with 8 models and 23 tests |
| Synthetic general ledger | 2,599,992 postings; 201,179 T&E claims; 800 advisors; 40 savings initiatives |
| Excel model | 14 sheets, 1,151 live formulas, 13 integrity checks |
| Python | 72 source files, about 6,300 lines; 60 automated tests |
| Power BI assets | 27 exported tables, about 55 DAX measures, RLS design, 8 page wireframes |
| Git | 28+ commits, CI on GitHub Actions (green), Docker image 1.38 GB |
| Governance docs | Model documentation, 60-row assumptions register, data dictionary (generated), metric dictionary, decisions log, data-gaps log, reconciliation report, 16 module notes |

## 3. Mapping to the job description (talking points)

| Posting responsibility | What I built | Headline evidence |
|---|---|---|
| Board presentation (financials, strategy, risk, product) | 6-slide board pack (PPTX + PDF), numbers pulled from the warehouse | Test re-derives slide numbers; PDF overflow-checked |
| Benchmarking vs competitors | 7-company benchmark, comparability layer, fee-compression regression | Fee yields falling at all 7 (-0.3 to -2.9 bps/yr, significant) |
| Marginal profitability to price new mandates | Mandate engine: break-evens, minimum AUM, survival-weighted LTV, API + Excel | $1bn equity mandate: 15.9 bps marginal vs 25.5 bps fully allocated break-even |
| Fully allocated profitability by business | 5 allocation methods, monthly pack | 4 of 6 businesses change rank by method; Liquidity +36% to -20% |
| P&L forecasting and budget process | Driver model, scenarios, Monte Carlo, backtest, PVM and expense bridges, budget variance | Q8 margin 29.3 / 31.2 / 25.5 / 15.7% (base / bull / bear / stress) |
| Growth Markets expansion analysis | GCC private wealth office: NPV/IRR/payback, Monte Carlo, staged-entry option | NPV $170m, 93% terminal value, ~10% loss probability |
| Compensation strategy | Comp ratio benchmark, accrual with Q4 true-up, scenario sensitivity, pay-for-performance | Accrual reconciles to annual pool (property test) |
| Sales and productivity | Advisor KPIs, cohort ramps, Gini, NNA forecast | Top 10% of advisors = 37% of revenue (synthetic) |
| Expense policy and savings | Rules + Isolation Forest, vendor HHI, CP-SAT savings optimiser | 84% recall on injected violations; $123.5m savings goal met at $86.3m cost |
| BI tools, large data, programming | Power BI assets (DAX, RLS), Streamlit, SQL/dbt, Python, 2.6M-row ledger | See sections 4 and 5 |

## 4. What was built, module by module

Detailed notes (method, outputs, validation, limitations) are in `docs/modules/`.

1. **Ingestion and extraction (M1-M2).** Rate-limited, cached EDGAR/FRED clients; deterministic HTML-table parsers; a generic AUM roll-forward detector that accepts a table only if it closes (begin + flows + market + other = end) and chains with the prior quarter; Goldman multi-vintage handling with restatement log and Q4 derivation.
2. **Warehouse (M3).** DuckDB star schema + dbt (staging, intermediate, marts, 23 tests incl. custom conservation tests) + generated data dictionary.
3. **Benchmarking (M4).** Fee yield, organic growth, market impact, margin, comp ratio, operating leverage, T4Q and z-scores for 7 companies; comparability flags; AUM growth decomposition.
4. **Market sensitivity (M5).** Robust regressions of AUM market impact on equity and bond returns, rolling betas, asset-mix sanity check.
5. **Forecast (M6).** Driver model, 4 scenarios, 10,000-path block-bootstrap Monte Carlo, rolling-origin conditional backtest with MLflow, price-volume-mix and expense bridges, budget vs actual, run-rate/exit-rate.
6. **Synthetic internal data (M7).** Calibrated to public Goldman AWM totals (exact on revenue, provision and opex); businesses, pools, regions, headcount, advisors, ledger, T&E with labelled violations, savings initiatives.
7. **Allocation (M8).** Revenue, headcount, activity-based, step-down and reciprocal methods; rank-sensitivity; monthly HTML pack.
8. **Mandate pricing (M9).** Tiered fees, marginal vs fully allocated break-evens (Brent's method), minimum viable AUM, Weibull survival LTV, Monte Carlo, tornado, recommendation rule, REST endpoint.
9. **Growth case (M10).** Cohort ramp business case for 3 Gulf locations, Monte Carlo, real option by simulation.
10. **Compensation and sales (M11-M12), expense (M13).** As in section 3.
11. **Excel model (M14).** Live-formula workbook with scenario/method/location selectors and Python parity testing.
12. **Power BI assets and Streamlit (M15).** Star schema export, Power Query, DAX, RLS design, page wireframes, 8-page Streamlit mirror.
13. **Board pack (M16).** PPTX + PDF generated from the warehouse.
14. **AI layer (M17).** Text-to-SQL agent (LangGraph, sqlglot validation, read-only execution), hybrid RAG with citations, numeric guardrail for generated commentary, LLM table extraction with Pydantic schema and human review queue, provider-agnostic gateway (Claude/OpenAI/Ollama/mock) with cost and latency logging.
15. **Delivery (M18).** FastAPI, Docker Compose (API + Streamlit), GitHub Actions CI, cross-platform pipeline runner, automatic refresh when Goldman files its next 10-Q.

## 5. Testing and validation (the "exams")

**Automated tests: 60 passing** (`uv run pytest`), including property-based tests with Hypothesis.

| Test file | Tests | What it proves |
|---|---|---|
| test_core | 7 | Parser handles parentheses and 'NM' cells; roll-forward gate rejects non-closing tables; every fact has provenance; GS roll-forward closes and chains; metric definitions; peers chain |
| test_synth | 5 | Calibration to public totals within 0.5%; GL totals = public opex; advisor revenue = PWM fees; T&E violation rate; every synthetic table flagged |
| test_allocation | 3 | Cost conservation for all methods (property test); reciprocal = direct when no inter-pool usage; fully allocated pre-tax reconciles to public segment |
| test_forecast | 4 | PVM and expense bridges sum exactly (property tests); model reproduces last reported quarter within 5% (actual -3.1%); scenarios ordered and stored |
| test_montecarlo | 5 | Vectorised simulator equals the deterministic engine in all 4 scenarios; bootstrap shapes; quantiles ordered |
| test_backtest | 1 | Error guard (conditional MAPE < 3.5%, beats best naive) and no look-ahead leakage |
| test_pricing | 11 | Profit = 0 at every break-even; min-AUM; tiered fee maths; LTV monotone in hazard; Weibull matches hazard; MC collapses to deterministic with zero volatility; rejection rule |
| test_growth_sim | 2 | Market-index default leaves case unchanged; simulation reproducible; abandon branch bounded |
| test_comp_sales | 3 | Accrual + true-up reconcile to annual pool (property test); regression recovers planted payout; sales metric bounds |
| test_expense | 3 | Detection metrics; optimiser feasible, dependency-respecting and no worse than greedy; vendor metrics |
| test_market | 1 | Betas sensible; bond proxy correlates > 0.9 with ICE |
| test_excel (slow) | 1 | **Excel recalculated vs Python: ~1e-15 error across 4 scenarios, mandate and growth; no error cells** |
| test_deck | 2 | Slide numbers re-derived from warehouse; PDF renders 6 pages, no overflow |
| test_api | 1 | All endpoints, 404s, input validation (422) |
| test_app (slow) | 1 | All 8 Streamlit pages render without exception |
| test_ai | 7 | Validator rejects all 17 adversarial queries; baseline SQL accuracy floor; guardrail rounding rule and wrong-number blocking; 250 seeded wrong-number drafts all blocked; extraction schema/grounding/queue; gateway |
| test_refresh | 3 | New 10-Q triggers all steps and records state; failure keeps old state; no-op when nothing new |

**Other validation**
* **Reconciliation:** Goldman segment checks 19/19 (revenue lines sum, roll-forward closure, begin = prior end, flows by class); peers chain with zero breaks.
* **dbt:** 23/23 tests pass (`dbt build`).
* **Clean-clone rebuild:** cloned the repo into an empty folder with only the SEC cache and rebuilt everything (ingest made 0 network calls); 60/60 tests passed there. This caught two real bugs (un-wired peer extraction; MLflow failing on long Windows paths), both fixed.
* **CI:** GitHub Actions (lint, tests, Docker build) is green.
* **Backtest (26 forecast/actual pairs, 8 origins, horizons 1-4):** MAPE on management fees: model with realised markets 2.5%, model with assumed markets 3.5%, best naive baseline 4.5%, naive 8.1%, seasonal naive 12.6%.
* **Market sensitivity:** equity beta (R2): T. Rowe 0.85 (0.97), BlackRock 0.66 (0.95), JPMorgan 0.41 (0.96).
* **AI evaluation (free open model, Ollama `gemma4:31b-cloud`; Claude not evaluated):**
  * Text-to-SQL, 69 questions with executed gold SQL: **81.2% strict, 94.2% lenient** execution accuracy; hard multi-step questions 9/12 (template baseline 0/12). An untuned prompt scored 62.3% before a metric glossary was added.
  * SQL validator: 17/17 adversarial queries rejected.
  * Retrieval over filings (20 questions): top-5 hit rate BM25 0.90, LSA 0.80, hybrid 0.90; live answers 85% cited, 95% number-grounded.
  * Numeric guardrail: 250/250 seeded wrong-number drafts blocked, 10/10 clean drafts passed.
  * LLM table extraction: 3/3 correct on real release tables (tiny sample).

## 6. Key findings (what the analysis says)

1. Goldman AWM's trailing-four-quarter organic growth is 14.9% vs 3.8% to 10.1% for other peers and -3.2% for T. Rowe; much of Goldman's inflow is low-fee liquidity products. AUS reached $4.10tn at 30 Sep 2026.
2. Fee yields fell at all seven firms (bps/year: Invesco -2.89, JPMorgan -1.77, Franklin -1.38, T. Rowe -1.27, Morgan Stanley -1.22, BlackRock -0.35, Goldman -0.33). Latest yields: 15.6 (BlackRock) to 43.8 (Franklin) bps.
3. Eight-quarter pre-tax margin: 29.3% base, 31.2% bull, 25.5% bear, 15.7% stress; Monte Carlo gives a 3.2% probability that the final-quarter margin is below 25%, and 13.1% that any quarter is. Goldman's own medium-term target is about 30% (10-Q).
4. Allocation method decides rankings: Liquidity Solutions earns +36.4% on a revenue basis but -20.1% under activity-based costing while contribution margin stays positive; 4 of 6 businesses change rank. Mandate rule: never price below marginal break-even.
5. GCC case: NPV $170m (IRR 50%, payback 5.7 years), but 93% of value is terminal value; staging a pilot lowers expected value ($51m to $154m) because it delays a project that pays off in about 90% of paths.
6. Goldman's AWM comp ratio was 44.3%, 43.1%, 40.2% and 44.6% for FY2022-25.

## 7. Engineering and judgement calls (strong interview stories)

* **Perimeter change:** Goldman re-based its segment in the FY2022 10-K (Dec-2021 AUS moved from a 1.7tn legacy basis to a 2.5tn basis). I tagged every fact with a perimeter and used recast comparatives to build a consistent 2022+ series instead of splicing incompatible numbers.
* **Closure-gated parsing:** parsers cannot guess. A roll-forward is accepted only if it closes arithmetically and chains with the prior quarter; this exposed table layouts that look right but add up wrong (acquisition rows, "reinvested distributions", footnote digits in labels).
* **Restatements:** all filing vintages kept, latest filed value used, 262 changes logged; Q4 derived as FY - 9M with the mixed-vintage risk documented.
* **Data availability:** FRED's ICE bond series shrank to about 3 years, so I built and validated a duration-based proxy (0.955 correlation on the overlap) instead of dropping the analysis.
* **Honest negative results:** Goldman's equity beta is statistically insignificant and the staged-entry option is worth less than going all-in; both are reported as found, and the deck text was changed when the simulation contradicted my first draft.
* **Source checks changed the model:** verified Goldman's 30% margin target in its 10-Q, found that no total revenue growth target is published (so 8% is labelled an assumption), and corrected Gulf tax from 9% to 15% for DIFC/ADGM after finding the UAE minimum top-up tax for large groups.
* **Reproducibility:** the clean-clone test, cross-platform pipeline runner, Docker, CI and an automatic refresh job make the project rebuild without manual steps.
* **Guardrails on AI:** read-only, allow-listed, AST-validated SQL; numeric guardrail on generated text (a fact can justify only one number, which closed a hole where a wrong figure matched another fact); human-review gate for LLM-extracted facts.

## 8. Résumé bullets (every number is from this repo; pick the version for the role)

### Primary - Goldman Sachs AWM F&S Analyst
* Built a driver-based P&L forecasting model (Excel with 1,151 live formulas + Python) for an asset and wealth management business, projecting net revenues, compensation and pre-tax margin over 8 quarters under bull/base/bear/stress scenarios (final-quarter margin 31.2% / 29.3% / 25.5% / 15.7%), with scenario switching, 13 automated integrity checks and Excel-to-Python parity of about 1e-15.
* Benchmarked 7 asset managers over 30 quarters from 1,071 SEC filings on fee yield, organic growth, margin and compensation ratio; decomposed AUM growth into net flows vs market moves and showed fee yields declining at all seven (-0.3 to -2.9 bps a year, statistically significant) while Goldman AWM's organic growth was 14.9% vs a peer range of -3.2% to 10.1%.
* Developed a mandate pricing tool comparing marginal and fully allocated profitability: break-even fees of 15.9 bps (marginal) and 25.5 bps (fully allocated) for a $1bn equity mandate, minimum viable AUM of $378m / $623m, and survival-weighted lifetime value with Monte Carlo.
* Produced fully allocated profitability reporting for 6 businesses using revenue, headcount, activity-based, step-down and reciprocal allocation; showed 4 of 6 businesses change rank by method and one business swings from +36% to -20% margin.
* Delivered a board pack (PPTX + PDF, every figure traced to the warehouse), Power BI assets (star schema, about 55 DAX measures, row-level-security design) and a Gulf expansion case (NPV $170m, IRR 50%, payback 5.7 years; 93% of value from terminal value; Monte Carlo loss probability about 10%).

### Data Analyst
* Built a DuckDB + dbt warehouse (8 models, 23 passing tests) over 1,071 SEC filings and a 2.6M-row synthetic general ledger, with row-level provenance (accession number, table locator, raw text) on 2,505 facts and automated reconciliation (19/19 checks on Goldman's segment, zero roll-forward breaks across peers).
* Designed a Power BI semantic model (27 tables, about 55 DAX measures, role-playing date dimension, row-level security for business-head and regional-CFO views) and an equivalent 8-page Streamlit app.

### Data Scientist
* Simulated 10,000 block-bootstrapped market paths to produce P10/P50/P90 fan charts of revenue and margin (probability the final-quarter margin falls below 25%: 3.2%); conditional backtest cut fee-forecast error to 2.5% MAPE vs 4.5% for the best naive baseline (26 forecast/actual pairs).
* Priced mandates with Weibull survival lifetime value; detected injected expense-policy violations with rules plus Isolation Forest (84% recall, 75% precision@k); optimised a savings programme with integer programming (CP-SAT): met a $123.5m goal at $86.3m cost within headcount and dependency constraints; estimated AUM market betas with robust regression (R2 up to 0.97).

### AI Engineer
* Built a text-to-SQL agent (LangGraph, sqlglot AST validation, read-only execution) that rejects 17/17 adversarial queries and reached 81.2% strict / 94.2% lenient execution accuracy on a 69-question finance eval set with an open-source model (9/12 on hard multi-step questions vs 0/12 for a template baseline).
* Added hybrid BM25 + embedding retrieval over SEC filings with accession-number citations (top-5 hit rate 0.90), a numeric guardrail that blocked 250/250 seeded wrong-number drafts, and LLM table extraction into Pydantic schemas with grounding checks and a human-review queue.

### Technical Business Analyst
* Translated a nine-item finance requirement set into 16 module specifications with business rules and acceptance criteria; documented model governance (model documentation, 60-row assumptions register, data dictionary, reconciliation report, decisions and data-gap logs) and verified key inputs against primary sources (Goldman's 10-Q margin target, UAE minimum-tax rules).

### Project line for the Projects section
**AssetLens - asset-management FP&A platform** (Python, DuckDB, dbt, Excel, Power BI, Streamlit, FastAPI, Docker) · https://github.com/swalihnm/assetlens

## 9. Claims to avoid (accuracy and integrity)

* Do not say the Power BI **dashboard was published**; say "Power BI assets / semantic model specification". The `.pbix` has not been built and the DAX has not been executed in Power BI.
* Internal business data is **synthetic**; never present business-unit, advisor, expense or comp results as Goldman's actual numbers. Say "calibrated to public segment totals".
* The AI evaluation used an **open free model (gemma4:31b)**, not Claude or GPT; accuracy numbers are for that model on my eval set.
* Sample sizes are small (18 Goldman AWM quarters, 26 backtest pairs, 20 retrieval questions, 3 extraction cases): present results as indicative.
* The Gulf case uses **illustrative** operating assumptions and secondary-source tax rates; terminal value dominates.
* Scenario outputs are assumptions, not forecasts or investment advice. The project is independent and not affiliated with Goldman Sachs.

## 10. Interview cheat sheet (concepts mapped to this project)

| Topic | One-line answer | Where it lives in the project |
|---|---|---|
| AUM vs AUS vs client assets | AUS adds advisory/third-party-distributed assets Goldman does not manage; Goldman reports AUS | GS facts, comparability flags |
| Management vs incentive fees | Management fees recur with average AUM; incentive fees are lumpy and depend on realisations | Forecast: incentive tied to alternatives AUS with Q4 seasonality |
| Fee yield and compression | Fees x4 / average AUM; falls with passive shift and pricing pressure | M4 regression: -0.3 to -2.9 bps/yr |
| Organic growth vs market | Flows are earned growth; market appreciation is not | AUM decomposition, market betas |
| Operating leverage; comp ratio | Revenue growing faster than cost; comp flexes with revenue, accrued YTD and trued-up in Q4 | Comp accrual model, floor in forecast |
| Contribution vs fully allocated | Allocation method changes rankings and decisions | M8: 4 of 6 businesses change rank |
| ABC, step-down, reciprocal | ABC uses activity drivers; step-down is sequential; reciprocal solves inter-department usage simultaneously | `allocation/methods.py` |
| Marginal pricing | A mandate can be worth winning below fully allocated cost, never below marginal cost | M9 rule and break-evens |
| Price-volume-mix | Splits a fee change into AUM, mix and rate effects that sum exactly | `forecast/bridges.py`, Excel bridge |
| Budget vs forecast; run vs exit rate | Budget is the plan; run-rate annualises the latest quarter, exit-rate uses period-end balances | `forecast/budget.py` |
| NPV, IRR, payback; scenario vs sensitivity vs stress | Value, return, speed; scenario = coherent paths, sensitivity = one driver, stress = tail | GCC case, scenarios, tornado |
| Why GCC wealth | Rapid wealth creation, new regional hubs, but ramp, regulation, tax and key-person risk | M10 and its option analysis |

**2-minute walkthrough:** problem (FP&A for asset managers) -> data (SEC filings with provenance and closure checks) -> benchmark findings -> forecast and Monte Carlo -> allocation and pricing -> deliverables (Excel parity, deck, API) -> validation (60 tests, clean-clone rebuild) -> what I would do next (Power BI build, live-LLM comparison).

## 11. Repository map

* `src/assetlens/` - ingest, extract, warehouse, benchmark, market, forecast, allocation, pricing, growth, comp, sales, expense, excel, powerbi, deck, api, ai, pipeline, refresh
* `dbt/` - SQL models and tests · `app/` - Streamlit · `config/` - scenarios, assumptions, synthetic parameters, peers
* `outputs/` - Excel model, board pack (PPTX + PDF), charts, reports · `powerbi/` - DAX, Power Query, build guide
* `docs/` - model documentation, decisions, data gaps, metrics, assumptions register, data dictionary, reconciliation report, `modules/`
* Run: `uv sync --all-extras` then `uv run python -m assetlens.pipeline all` · Demo: `uv run streamlit run app/streamlit_app.py`

## 12. Status

Complete and published. Two items sit outside the codebase:
* **Power BI file:** assemble the `.pbix` in Power BI Desktop from `powerbi/model.md` (about an hour), then compare to `outputs/powerbi/dax_spot_checks.csv`.
* **Goldman Q3-2026 10-Q** (due about 30 Oct): `AssetLensRefresh`, a daily Windows scheduled task starting 30 Oct 07:30, rebuilds everything when the filing appears (needs the PC on) and removes itself afterwards; or run `uv run python -m assetlens.refresh`.
