"""M13 - expense policy engine: rule checks on T&E claims (synthetic) evaluated against injected ground truth."""
from __future__ import annotations

import pandas as pd
from pandas.tseries.holiday import USFederalHolidayCalendar

RECEIPT_THRESHOLD_USD = 75.0
RULES = ["over_limit", "duplicate", "split_transaction", "weekend_holiday", "missing_receipt"]


def apply_rules(te: pd.DataFrame) -> pd.DataFrame:
    d = te.copy()
    d["claim_date"] = pd.to_datetime(d.claim_date)
    d["r_over_limit"] = d.amount_usd > d.limit_usd
    key = ["employee_id", "claim_date", "category", "amount_usd"]
    d["r_duplicate"] = d.duplicated(key, keep=False) & ~d.duplicated(key, keep="first") | d.duplicated(key, keep="first")
    # split: same employee, day and category, >= 2 claims each within limit but together above the limit
    g = d.groupby(["employee_id", "claim_date", "category"])
    tot, cnt, mx = g.amount_usd.transform("sum"), g.amount_usd.transform("size"), g.amount_usd.transform("max")
    mn = g.amount_usd.transform("min")
    d["r_split_transaction"] = (cnt >= 2) & (tot > d.limit_usd) & (mx <= 0.8 * d.limit_usd) & (mn >= 0.5 * d.limit_usd) & ~d.r_duplicate   # both parts just under the limit
    hol = USFederalHolidayCalendar().holidays(d.claim_date.min(), d.claim_date.max())
    d["r_weekend_holiday"] = (d.claim_date.dt.weekday >= 5) | d.claim_date.isin(hol)
    d["r_missing_receipt"] = (~d.has_receipt.astype(bool)) & (d.amount_usd > RECEIPT_THRESHOLD_USD)
    d["rule_hits"] = d[[f"r_{r}" for r in RULES]].sum(axis=1)
    # weekend/holiday alone is weak evidence (some legitimate travel): require a second signal for a hard flag
    strong = ["r_over_limit", "r_duplicate", "r_split_transaction", "r_missing_receipt"]
    d["rule_flag"] = d[strong].any(axis=1) | (d.r_weekend_holiday & (d.amount_usd > 0.8 * d.limit_usd))
    return d
