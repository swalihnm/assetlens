# M13 Expense management and savings

**Method.** Spend cube, budget vs actual with 10% flag, run-rate and exit-rate, vendor concentration (HHI, tail spend). Policy engine with five rules (over limit, duplicate, split transaction, weekend/holiday, missing receipt) plus Isolation Forest and robust z-score, evaluated against injected ground truth. Savings programme optimiser (OR-Tools CP-SAT) chooses initiatives to meet a goal at minimum implementation cost plus risk charge subject to a headcount cap and dependencies; savings roll up into the M6 forecast.

**Outputs.** `expense/rules.py`, `anomaly.py`, `analytics.py`, `savings_optimizer.py`.

**Results and validation.** Rules alone: precision 72.6%, recall 83.8%; precision@k (k = number of true violations): rules 73.7%, Isolation Forest 54.2%, combined 75.1%. Recall by type: over limit, duplicate and split 100%, missing receipt 84%, weekend/holiday 4% (indistinguishable from legitimate weekend travel by construction). Optimiser: goal 60% of expected savings ($123.5m) met at $86.3m objective with 21 initiatives, 124 of 150 headcount cap; test checks feasibility, dependencies and that it is no worse than a greedy heuristic.

**Limitations.** All expense data synthetic; detection metrics depend on how violations were injected.
