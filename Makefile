.PHONY: docs refresh dbt api pack market montecarlo analytics app setup test test-all lint ingest extract warehouse benchmark synth allocate forecast excel parity powerbi deck all
setup:
	uv sync --all-extras
test:
	uv run pytest -q -m "not slow"
test-all:
	uv run pytest -q
lint:
	uv run ruff check src tests
ingest:
	uv run python -m assetlens.ingest.run 2
extract:
	uv run python -m assetlens.extract.run_all
warehouse:
	uv run python -m assetlens.warehouse.build
benchmark:
	uv run python -m assetlens.benchmark.metrics
synth:
	uv run python -m assetlens.synth.generator
allocate:
	uv run python -m assetlens.allocation.methods
forecast:
	uv run python -m assetlens.forecast.engine && uv run python -m assetlens.forecast.budget
excel:
	uv run python -m assetlens.excel.build_model
parity:
	uv run python -m assetlens.excel.parity
powerbi:
	uv run python -m assetlens.powerbi.export_star_schema
deck:
	uv run python -m assetlens.deck.build_deck && uv run python -m assetlens.deck.render_pdf
all:
	uv run python -m assetlens.pipeline all
dbt:
	uv run dbt build --project-dir dbt --profiles-dir dbt && uv run dbt docs generate --project-dir dbt --profiles-dir dbt
api:
	uv run uvicorn assetlens.api.app:app --reload
pack:
	uv run python -m assetlens.allocation.monthly_pack
market:
	uv run python -m assetlens.market.sensitivity
montecarlo:
	uv run python -m assetlens.forecast.montecarlo && uv run python -m assetlens.forecast.backtest
analytics:
	uv run python -m assetlens.sales.analytics && uv run python -m assetlens.comp.analysis
app:
	uv run streamlit run app/streamlit_app.py
refresh:
	uv run python -m assetlens.refresh
docs:
	uv run python -m assetlens.warehouse.docs_gen
