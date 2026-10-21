"""Price-volume-mix fee bridge (Section 6.3) and headcount x cost-per-head expense bridge.

Both decompositions are exact identities (unit/property tested): the effects sum to the total change.
"""
from __future__ import annotations

import numpy as np


def pvm(aum0: np.ndarray, fees0: np.ndarray, aum1: np.ndarray, fees1: np.ndarray) -> dict[str, float]:
    """aum/fees by asset class (same units/period). Yield y_k = fees_k / aum_k (period yield)."""
    aum0, fees0, aum1, fees1 = (np.asarray(x, dtype=float) for x in (aum0, fees0, aum1, fees1))
    A0, A1 = aum0.sum(), aum1.sum()
    w0, w1 = aum0 / A0, aum1 / A1
    y0, y1 = fees0 / aum0, fees1 / aum1
    volume = (A1 - A0) * float((w0 * y0).sum())
    mix = A1 * float(((w1 - w0) * y0).sum())
    rate = A1 * float((w1 * (y1 - y0)).sum())
    return dict(volume=volume, mix=mix, rate=rate, total=volume + mix + rate,
                actual_change=float(fees1.sum() - fees0.sum()))


def expense_bridge(h0: float, c0: float, h1: float, c1: float, nc0: float = 0.0, nc1: float = 0.0) -> dict[str, float]:
    """Comp = headcount x cost per head; plus non-comp. headcount, cost/head and non-comp effects."""
    headcount = (h1 - h0) * c0
    cost_per_head = h1 * (c1 - c0)
    noncomp = nc1 - nc0
    return dict(headcount=headcount, cost_per_head=cost_per_head, noncomp=noncomp,
                total=headcount + cost_per_head + noncomp, actual_change=(h1 * c1 + nc1) - (h0 * c0 + nc0))
