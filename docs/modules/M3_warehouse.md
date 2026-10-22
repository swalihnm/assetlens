# M3 Warehouse (DuckDB + dbt)

**Method.** Python builds typed fact and mart tables in DuckDB; a dbt-duckdb project (`dbt/`) re-expresses staging -> intermediate -> marts in SQL with tests. Star schema (dimensions and facts) is exported for Power BI.

**Outputs.** `data/warehouse/assetlens.duckdb` (about 40 tables), dbt: 8 models, 23 tests (not_null, unique, relationships, accepted_values plus custom tests: roll-forward closes, allocations conserve pool cost, synthetic revenue equals public totals, fee yield within range), dbt docs lineage.

**Results and validation.** `dbt build`: PASS 23 / 23. `docs/DATA_DICTIONARY.md` is generated from the database.

**Limitations.** dbt re-implements a subset of the marts; the Python-built marts remain the source for the forecast and deliverables. dbt needs the warehouse built first (not part of CI).
