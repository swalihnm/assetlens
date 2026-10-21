"""M13 - anomaly ranking (Isolation Forest + robust z-score) and evaluation of rules / ML / combined vs ground truth."""
from __future__ import annotations

import duckdb
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from assetlens.expense.rules import RULES, apply_rules
from assetlens.warehouse.build import DB


def features(d: pd.DataFrame) -> pd.DataFrame:
    x = pd.DataFrame(index=d.index)
    x["ratio"] = d.amount_usd / d.limit_usd
    x["weekend"] = d.r_weekend_holiday.astype(int)
    x["no_receipt"] = (~d.has_receipt.astype(bool)).astype(int)
    g = d.groupby(["employee_id", "claim_date"])
    x["same_day_claims"] = g.amount_usd.transform("size")
    x["same_day_total_ratio"] = g.amount_usd.transform("sum") / d.limit_usd
    x["dup_key_count"] = d.groupby(["employee_id", "claim_date", "category", "amount_usd"]).amount_usd.transform("size")
    emp = d.groupby("employee_id").amount_usd.transform("mean")
    x["emp_rel_amount"] = d.amount_usd / emp
    return x


def robust_z(s: pd.Series) -> pd.Series:
    med = s.median()
    mad = (s - med).abs().median() or 1e-9
    return (s - med) / (1.4826 * mad)


def evaluate(n_estimators: int = 150, seed: int = 3) -> dict:
    con = duckdb.connect(str(DB), read_only=True)
    te = con.execute("select * from fact_te").df()
    con.close()
    d = apply_rules(te)
    X = features(d)
    iso = IsolationForest(n_estimators=n_estimators, contamination="auto", random_state=seed, n_jobs=-1).fit(X)
    d["if_score"] = -iso.score_samples(X)
    d["rz"] = robust_z(X.ratio).abs()
    # combined score: rule hits dominate, IF score breaks ties / adds novel patterns
    d["combined"] = d.rule_flag.astype(float) * 10 + d.if_score
    truth = d.is_violation.values
    k = int(truth.sum())
    out = {}
    for name, score in [("rules", d.rule_flag.astype(float) + d.rule_hits * 0.01), ("isolation_forest", d.if_score),
                        ("robust_z", d.rz), ("combined", d.combined)]:
        top = np.argsort(-score.values)[:k]
        p_at_k = float(truth[top].mean())
        recall_k = float(truth[top].sum() / k)
        out[name] = dict(precision_at_k=p_at_k, recall_at_k=recall_k, k=k)
    flag = d.rule_flag.values
    out["rules_binary"] = dict(precision=float(truth[flag].mean()) if flag.any() else 0.0, recall=float(flag[truth].mean()), flagged=int(flag.sum()))
    per = {}
    top = np.argsort(-d.combined.values)[:k]
    sel = np.zeros(len(d), bool)
    sel[top] = True
    for t in RULES:
        m = (d.violation_type == t).values
        per[t] = dict(n=int(m.sum()), recall_rules=float(flag[m].mean()), recall_combined_top_k=float(sel[m].mean()))
    out["per_type"] = per
    out["claims"] = len(d)
    return out


if __name__ == "__main__":
    import json
    print(json.dumps(evaluate(), indent=1))
