.PHONY: setup test lint ingest
setup:
	uv sync --extra dev
test:
	uv run pytest -q
lint:
	uv run ruff check src tests
ingest:
	uv run python -m assetlens.ingest.run
