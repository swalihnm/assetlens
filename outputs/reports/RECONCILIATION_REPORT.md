# Reconciliation report (auto-generated)

_Generated 2026-10-21 14:38. GS AWM perimeter, 21 quarters._

## GS segment checks

| Check | Passed | Total |
|---|---|---|
| begin_equals_prior_end | 19 | 19 |
| flows_by_class_sum | 19 | 19 |
| revenue_lines_sum | 19 | 19 |
| rollforward_closes | 19 | 19 |

Failures: **0**

## Peer AUM roll-forwards (closure and chaining)

| Ticker | Quarters with roll-forward | Closing | Chaining breaks |
|---|---|---|---|
| BLK | 30 | n/a (residual) | 0 |
| GS | 20 | 19 | 0 |
| IVZ | 30 | 30 | 0 |
| TROW | 28 | 28 | 2 |

BLK has no begin/market table in its releases; its roll-forward is begin = prior end and market = residual, so closure is true by construction. TROW 2020-Q3 and 2021-Q4 roll-forwards are missing (see DATA_GAPS.md). Chaining breaks around missing quarters are expected.

## Restatements

GS restatement log rows: 262 (see `restatement_log` table).
