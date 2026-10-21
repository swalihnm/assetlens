# AssetLens – build progress

_Last updated: 2026-10-21. Spec: AssetLens_Project_Spec.md. Phase 1 target = F&S-ready._

## Status by module

| Module | Status | Evidence / notes |
|---|---|---|
| M0 Setup | Done (basic) | uv env, Makefile, pre-commit config, Dockerfile, CI workflow (untested on GitHub; CI has no warehouse so data tests skip) |
| M1 EDGAR + FRED ingestion | Done | 593-filing manifest, cached, rate-limited; 8 FRED series |
| M2 Extraction + reconciliation | Done for GS, BLK, TROW, IVZ | Closure-gated AUM roll-forwards; GS reconciliation 19/19 on each check. Gaps in `docs/DATA_GAPS.md`. Auto-generated `RECONCILIATION_REPORT.md` done. **Missing:** LLM review queue (Phase 3) |
| M3 Warehouse | Done | DuckDB star schema + dbt project (staging/intermediate/marts, 23 tests pass, docs generated) |
| M4 Benchmarking | Done, 7 peers | GS, BLK, TROW, IVZ plus MS (IM), JPM (AWM), BEN; comparability flags; charts |
| M5 Market sensitivity | Done | HC3 betas with CIs, rolling betas, residual plot; bond proxy because FRED ICE history is ~3 yrs |
| M6 Forecast / budget | Done | 4 scenarios, PVM + expense bridges, budget variance, Monte Carlo (10k paths), conditional backtest (MLflow) |
| M7 Synthetic data | Done | 2.6M-row GL, 200k T&E (5 violation types incl. split), 800 advisors, 40 initiatives; calibration tests pass |
| M8 Allocation | Done | 5 methods, property tests, monthly HTML profitability pack |
| M9 Mandate pricing | Done | engine + FastAPI `POST /mandate/price` + Excel sheet |
| M10 GCC case | Done | deterministic + Monte Carlo + staged-entry option (option value negative in all settings) |
| M11 Compensation | Done | ratio benchmark, accrual with Q4 true-up, scenario sensitivity, pay-for-performance, pool allocation |
| M12 Sales | Done | KPIs, cohort ramps, time to productivity, Gini, funnel (synthetic), NNA forecast |
| M13 Expense | Done | spend cube, budget/run/exit rate, rules+IsolationForest (P@k 74%), HHI/tail, CP-SAT savings optimiser, forecast roll-up |
| M14 Excel | Done | live formulas, checks all 0, Python parity ~1e-15 |
| M15 Power BI assets | Done (assets) | **.pbix not built; DAX never executed** |
| M16 Board deck | Done (PPTX) | numbers from warehouse, test passes. **No PDF** (no LibreOffice) |
| M17 AI layer | Done offline | text-to-SQL baseline 82.6% (hard 0/12), adversarial 17/17 rejected, RAG hit@5 0.90, guardrail 250/250, extraction + review queue. **No live LLM run (no API key)** |
| M18 API / Streamlit / Docker / docs | Done | FastAPI (5 endpoints), Streamlit 8 pages (smoke-tested), Dockerfile + CI (unrun) |

## Tests
`make test` - 54 pass (fast). `make test-all` adds the Excel parity test (~80 s) and the Streamlit all-pages smoke test.

## Still to do
1. Live-LLM evaluation of text-to-SQL / RAG answers / extraction (needs an API key)
2. Parse older MS IM AUM layouts and JPM AWM P&L before 2024 (see DATA_GAPS G12-G15); TROW 2020-Q3 / 2021-Q4
3. Build the .pbix; render deck PDF (install LibreOffice) and cross-check the workbook with it
4. Q3-2026 GS 10-Q (about 30 Oct): rerun extract + warehouse

## Open items for you
- Power BI: build the .pbix from `powerbi/model.md`, then check `outputs/powerbi/dax_spot_checks.csv`.
- Confirm management targets (30% margin, ~8% growth) from a primary source; they are marked UNVERIFIED in the budget model.
- Verify GCC corporate tax rates in `config/assumptions.yaml`.
- Q3-2026 GS 10-Q (≈30 Oct): re-run `make extract warehouse` to fill opex/pre-tax and fix the Q4-2025 mixed-vintage quarter.
- FRED key saved in `.env` (gitignored); current code uses the public CSV endpoint and doesn't need it.

## Decisions made on your behalf (details in docs/DECISIONS.md)
- Parsed iXBRL/HTML tables directly instead of Arelle.
- GS series on the AWM perimeter starts 2022 Q1 (FY2022 re-base); 2019–21 quarterlies unavailable.
- BLK market impact is a residual (no roll-forward table in releases).
- Excel recalculation/parity via Python `formulas` engine.
- GCC base case location DIFC; assumptions illustrative; terminal value is 93% of NPV.
