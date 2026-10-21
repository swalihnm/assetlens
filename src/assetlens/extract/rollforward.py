"""Generic AUM roll-forward detector. A candidate column is accepted only if it CLOSES:
begin + net_flows + market + other = end (tolerance 0.3% of end). Closure is the quality gate."""
from __future__ import annotations

import re
from dataclasses import dataclass

from assetlens.extract.tables import find_tables, norm, rows

BEGIN = re.compile(r"(beginning (of (the )?)?(period|quarter|balance)|^beginning|^balance.*beginning)", re.IGNORECASE)
END = re.compile(r"(^ending (assets|aum|balance)|^assets under (management|supervision)[^,]*\bat\b.*\d{4}$|ending balance|end of (the )?(period|quarter)|^balance.*end)", re.IGNORECASE)
FLOWS = re.compile(r"^(total )?net (cash )?(inflows|flows|new business|long-term (net )?(inflows|flows))", re.IGNORECASE)
MARKET = re.compile(r"(market (appreciation|depreciation|gains|losses|change|movement|impact)|^market|appreciation|depreciation)", re.IGNORECASE)
OTHER = re.compile(r"(distributions|foreign|fx|acquisition|disposition|other|transfer|model delivery)", re.IGNORECASE)
SKIP = re.compile(r"(before|prior to|change during|total change|percent|%|manager-driven|adjusted assets)", re.IGNORECASE)


@dataclass
class Roll:
    begin: float
    flows: float
    market: float
    other: float
    end: float
    table: int
    col: int
    raw: str


def _roles(r):
    """Row index per role (first occurrence), plus 'other' row indices between begin and end."""
    role, others = {}, []
    for i, (label, nums, raw) in enumerate(r):
        lab = norm(label)
        if not nums or (SKIP.search(lab) and not END.search(lab)):
            continue
        if BEGIN.search(lab) and "b" not in role:
            role["b"] = i
        elif END.search(lab) and "e" not in role and "b" in role:
            role["e"] = i
        elif FLOWS.search(lab) and not role.get("_tot"):
            if lab.lower().startswith("total net"):  # explicit total row beats component rows
                role["f"], role["_fl"], role["_tot"] = i, [i], True
            else:
                role.setdefault("f", i)
                role.setdefault("_fl", []).append(i)
        elif MARKET.search(lab) and "m" not in role:
            role["m"] = i
        elif OTHER.search(lab) and "b" in role and "e" not in role:
            others.append(i)
    return role, others


def candidates(tbl, ti: int) -> list[Roll]:
    from itertools import product
    r = rows(tbl)
    role, others = _roles(r)
    if not all(k in role for k in "bfme"):
        return []
    ncol = max(len(n) for _, n, _ in r)
    out = []

    def idxs(i, c):  # allowed positions in row i for logical column c (blank cells drop values)
        L = len(r[i][1])
        return [c - k for k in range(ncol - L + 1) if 0 <= c - k < L]

    flow_rows = role.get("_fl", [role["f"]])

    def vals(i, c):  # candidate values for row i at logical column c (all alignments)
        v = [r[i][1][j] for j in idxs(i, c)]
        return [x for x in v if x is not None] or [0.0]

    for c in range(ncol):
        for ib, im, ie in product(*(idxs(role[k], c) for k in "bme")):
            b, m, e = (r[role[k]][1][j] for k, j in zip("bme", (ib, im, ie)))
            if None in (b, m, e):
                continue
            f_opts = []
            for sel in ([flow_rows[0]], flow_rows):
                for combo in product(*(vals(x, c) for x in sel)):
                    f_opts.append(sum(combo))
            hit = None
            for f in f_opts:
                for combo in product(*(vals(o, c) for o in others)):
                    oth = sum(combo)
                    if abs(b + f + m + oth - e) <= max(0.35, 0.0005 * abs(e)):
                        hit = (f, oth)
                        break
                if hit:
                    break
            if hit:
                raws = " || ".join(r[x][2] for x in [role["b"]] + flow_rows + [role["m"], role["e"]])
                out.append(Roll(b, hit[0], m, hit[1], e, ti, c, raws))
                break
    return out


def best(sp, anchors: list[str], min_end: float = 0.0, cols: set[int] | None = None) -> Roll | None:
    """Among closing candidates in all matching tables: largest `end` (total column), earliest table."""
    cands = []
    for ti, t in find_tables(sp, *anchors):
        cands += [c for c in candidates(t, ti) if c.end >= min_end and (cols is None or c.col in cols)]
    if not cands:
        return None
    return max(cands, key=lambda c: (c.end, -c.table))
