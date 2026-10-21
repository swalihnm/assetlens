# AssetLens – build progress

_Last updated: 2026-10-21. Spec: AssetLens_Project_Spec.md. Phase 1 target = F&S-ready._

## Status by module

| Module | Status | Evidence / notes |
|---|---|---|
| M0 Setup | Done (partial) | uv env, Makefile, pyproject, .env(.example). **Missing:** pre-commit, Dockerfile, GitHub Actions |
| M1 EDGAR + FRED ingestion | Done | 593-filing manifest, cached, rate-limited; 8 FRED series |
| M2 Extraction + reconciliation | Done for GS, BLK, TROW, IVZ | Closure-gated AUM roll-forwards; GS reconciliation 19/19 on each check. Gaps in `docs/DATA_GAPS.md`. **Missing:** auto-generated `RECONCILIATION_REPORT.md`, review queue |
| M3 Warehouse | Partial | DuckDB `fact_financials` + `fact_provenance` + marts built in Python. **Missing:** dbt project and tests, dbt docs |
| M4 Benchmarking | Done | `mart_peer_benchmark`, fee-compression regression, AUM decomposition, comparability flags, charts |
| M5 Market sensitivity | Not started | Phase 2 |
| M6 Forecast / budget | Done (deterministic) | 4 scenarios, PVM + expense bridges (exact), budget variance, run/exit rate. Monte Carlo + backtest = Phase 2 |
| M7 Synthetic data | Done | 2.6M-row GL, 200k T&E, 800 advisors, 40 initiatives; calibration tests pass |
| M8 Allocation | Done | 5 methods, conservation property tests, reconciles to public pre-tax |
| M9 Mandate pricing | Done | brentq break-evens, min AUM, Weibull LTV, Monte Carlo, tornado. **Missing:** FastAPI endpoint |
| M10 GCC case | Deterministic core done | 3 locations; Monte Carlo + staged real option = Phase 2 |
| M11 Comp / M12 Sales / M13 Expense | Not started | Phase 2 |
| M14 Excel | Done | Live formulas, 14 sheets, checks all 0, Python parity ~1e-15 (all scenarios, mandate, growth). Recalc by `formulas` lib, not LibreOffice |
| M15 Power BI assets | Done (assets) | 27 tables, Power Query, 60+ DAX measures, model.md with RLS. **.pbix not built; DAX never executed** |
| M16 Board deck | Done (PPTX) | 5 slides + appendix, numbers pulled from warehouse, test passes. **No PDF** (no LibreOffice) |
| M17 AI layer | Not started | Phase 3 |
| M18 API / Docker / docs | Not started | |

## Tests
`make test` – 30 pass (fast). `make test-all` adds the ~80 s Excel parity test.

## Still to do for Phase 1
1. README with sourced findings and screenshots
2. docs: MODEL_DOCUMENTATION, ASSUMPTIONS_REGISTER.csv, DATA_DICTIONARY, METRICS, per-module notes, RECONCILIATION_REPORT
3. dbt project over the warehouse with tests and lineage
4. Dockerfile, pre-commit, GitHub Actions
5. Monthly profitability pack (sample month)

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
