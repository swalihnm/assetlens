# AssetLens

**FP&A and strategic-finance analytics for asset & wealth management** - peer benchmarking from SEC filings, driver-based P&L forecasting, fully allocated profitability, mandate pricing, a Gulf expansion case, a live-formula Excel model, Power BI assets, a board pack, an API and a SQL/RAG assistant.

[![CI](https://github.com/swalihnm/assetlens/actions/workflows/ci.yml/badge.svg)](https://github.com/swalihnm/assetlens/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.12-blue) ![License](https://img.shields.io/badge/license-MIT-green)

> **Disclaimer.** AssetLens is an independent educational project built from publicly available SEC filings and FRED data. It is not affiliated with, endorsed by, or based on any non-public information from Goldman Sachs or any other company named. Business-unit, headcount, advisor, expense and compensation data are **synthetic**, generated to be consistent with public segment totals, and do not represent any company's internal figures. Nothing here is investment advice. Company names are used descriptively; no logos or third-party branding are used.

## Findings (public data unless marked synthetic)

1. **Goldman's Asset & Wealth Management (AWM) is growing assets faster than peers, helped by liquidity products.** Assets under supervision reached $4.10tn at 30 Sep 2026; trailing-four-quarter organic growth is 14.9% vs JPMorgan AWM 9.3%, Morgan Stanley IM 10.1%, BlackRock 6.5%, Invesco 7.6%, Franklin 3.8% and T. Rowe -3.2%. Much of Goldman's inflow is low-fee liquidity products.
2. **Fee yields are falling at all seven companies.** Trailing-four-quarter yield: GS 34.8 bps, T. Rowe 38.6, JPM 35.1, MS 33.4, Franklin 43.8, Invesco 23.9, BlackRock 15.6. Fitted trends (HAC 95% CI, all significant): Invesco -2.89, JPM -1.77, MS -1.52, Franklin -1.38, T. Rowe -1.27, BlackRock -0.35, GS -0.33 bps a year. Definitions differ by company - see `comparability_flags`.
3. **Scenario range for the next eight quarters** (driver model; assumptions, not forecasts): final-quarter pre-tax margin 29.3% base, 31.2% bull, 25.5% bear, 15.7% under a -25% equity stress. Goldman's own medium-term AWM target is about 30% (10-Q, June 2026).
4. **Allocation method changes the answer (synthetic businesses).** Liquidity Solutions shows +36% fully allocated margin on a revenue basis and about -20% under activity-based costing (rank 2 to 6) while its contribution margin stays positive. Marginal pricing floor on a $1bn equity mandate: 15.9 bps marginal vs 25.5 bps fully allocated break-even.
5. **GCC private wealth office (illustrative):** NPV $170m at the DIFC base case (UAE 15% minimum top-up tax, KSA 20%), but 93% is terminal value (explicit seven-year NPV $11m). Monte Carlo: mean NPV about $255m, ~10% chance of loss; staging a pilot first lowers expected value, so it works as risk control, not value creation. Back-test: driver-model fee forecasts have 2.5-3.5% MAPE vs 4.5% for the best naive baseline (small sample).

![Fee yield](outputs/charts/fee_yield.png)
![Allocation methods](outputs/charts/margin_by_method.png)

## What is inside

| Area | Contents | Where |
|---|---|---|
| Data pipeline | EDGAR + FRED ingestion, table parsers, closure-checked AUM roll-forwards, provenance for every fact | `src/assetlens/ingest`, `extract`, `warehouse` |
| Warehouse | DuckDB star schema; dbt project (23 tests, lineage docs) | `data/warehouse` (built locally), `dbt/` |
| Benchmarking | 7 companies (GS, BLK, TROW, IVZ, MS, JPM, BEN), T4Q metrics, fee-compression regression, AUM decomposition, market betas | `benchmark`, `market` |
| Forecasting | Driver-based scenarios, price-volume-mix bridges, budget variance, Monte Carlo (10k paths), conditional backtest (MLflow) | `forecast` |
| Profitability and pricing | 5 allocation methods, monthly pack, mandate break-evens / LTV, Gulf business case with real option | `allocation`, `pricing`, `growth` |
| People and cost | Compensation accrual and pay-for-performance, sales analytics, expense policy engine, CP-SAT savings optimiser | `comp`, `sales`, `expense` |
| Deliverables | Live-formula Excel model (Python parity-tested), Power BI assets (DAX, RLS design), board pack PPTX + PDF | `outputs/`, `powerbi/` |
| Apps | Streamlit (8 pages), FastAPI (5 endpoints), Docker Compose | `app/`, `src/assetlens/api`, `docker-compose.yml` |
| AI layer | Text-to-SQL agent (sqlglot-validated, read-only), hybrid RAG with citations, numeric guardrail, LLM table extraction with human review | `src/assetlens/ai` |

```
SEC EDGAR ─┐                      ┌─> benchmark ──┐
FRED ──────┼─> ingest ─> extract ─┴─> DuckDB + dbt ┼─> forecast / Monte Carlo ─┐
           │        (closure-checked)               │                           ├─> Excel · Power BI · deck · API · Streamlit
synthetic internal data (calibrated to public totals) ─> allocation ─> pricing ─┘
```

## Quick start

Requires Python 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/swalihnm/assetlens.git && cd assetlens
cp .env.example .env                          # set SEC_USER_AGENT="Your Name your@email" (SEC fair-access rule)
uv sync --all-extras
uv run python -m assetlens.pipeline all       # ingest -> ... -> deck (first run downloads ~1.4 GB of filings, cached afterwards)
uv run pytest -q -m "not slow"                # drop the marker to include the Excel parity and Streamlit tests
uv run streamlit run app/streamlit_app.py     # dashboard
uv run uvicorn assetlens.api.app:app          # API docs at http://localhost:8000/docs
```

`make <step>` shortcuts exist for the same steps (`make all`, `make test`, ...); `make` is optional. Run individual steps with e.g. `uv run python -m assetlens.pipeline warehouse benchmark`.

**Docker:** build the warehouse on the host first (`data/` is mounted, not baked in), then `docker compose up --build` (API on :8000, Streamlit on :8501).

**Keeping it current:** `uv run python -m assetlens.refresh` checks EDGAR for a new Goldman 10-Q and rebuilds everything when one appears.

## Data and compliance

* Sources: SEC EDGAR (10-K, 10-Q, 8-K Exhibit 99.1) and FRED. Requests are throttled to 8/s with a descriptive User-Agent and cached under `data/raw/`; the cache is not in the repository.
* Every public fact in `fact_financials` has provenance (accession number, table locator, raw text, extraction method, retrieval time). Restated figures keep all versions (`restatement_log`); marts use the latest filed value.
* AUM roll-forwards are accepted only when `begin + flows + market + other = end` and they chain with the prior quarter. Goldman's segment checks pass 19/19; peers chain with zero breaks (`docs/RECONCILIATION_REPORT.md`).
* Synthetic tables carry `synthetic = true` and are calibrated to public segment totals within 0.5% (tests enforce it).

## Documentation

`docs/MODEL_DOCUMENTATION.md` (method, validation, limitations) · `docs/METRICS.md` · `docs/ASSUMPTIONS_REGISTER.csv` · `docs/DATA_DICTIONARY.md` · `docs/DECISIONS.md` (design decisions and verification findings, including the tax and target checks) · `docs/DATA_GAPS.md` · `docs/RECONCILIATION_REPORT.md` · per-module notes in `docs/modules/` · Power BI build guide `powerbi/model.md` · status log `progress.md`.

## Quality

About 60 tests: unit and property tests (Hypothesis) for every formula, allocation conservation, bridge identities, calibration against public totals, Excel-vs-Python parity (max relative error ~1e-15), deck-vs-warehouse number checks, a Streamlit smoke test over all pages, a SQL-validator adversarial set and the numeric-guardrail catch rate. Lint: ruff. CI runs lint and the tests that do not need the SEC cache.

## Known limitations

* Goldman's AWM segment was re-based in the FY2022 10-K, so its consistent quarterly series starts in 2022 Q1 (annual figures for 2020-21 exist).
* Peer metrics are not perfectly like-for-like (AUS vs AUM, gross vs net fees, GAAP vs adjusted margins); each difference is documented in `comparability_flags`.
* Scenario paths, class-level fee yields and the Gulf case inputs are assumptions. The top-down budget uses Goldman's published ~30% margin target and an assumed 8% revenue growth (Goldman publishes no total revenue growth target). Gulf tax rates come from secondary sources and should be confirmed by a tax adviser.
* The Power BI `.pbix` is not included (it must be assembled in Power BI Desktop); the DAX measures were validated only against warehouse queries, not executed in Power BI.
* The AI layer was evaluated on a free open model (Ollama `gemma4:31b-cloud`) and offline baselines; see `docs/modules/M17.md`.

## License

MIT - see [LICENSE](LICENSE).
