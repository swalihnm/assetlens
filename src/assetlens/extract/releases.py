"""Earnings-release (Exhibit 99.1) table parsers for peers. One spec per company.

A spec is a list of table rules: anchors (strings that must all appear in the table text),
and row rules: (label regex, metric, column pick, scale). Column pick: int index or 'last'.
First matching row per metric per table wins; first matching table per rule wins.
"""
from __future__ import annotations

import re

import pandas as pd

from assetlens.extract.tables import find_tables, norm, rows, soup

Rule = tuple[str, str, int | str, float]  # regex, metric, col, scale

TROW_RULES = [
    (["Unaudited Consolidated Statements of Income"], [
        (r"^Investment advisory fees$", "fees_investment_advisory", 0, 1),
        (r"^Net revenues$", "net_revenues", 0, 1),
        (r"^(Total )?[Cc]ompensation( and related costs)?$|^Total compensation and related costs$|^Compensation and related costs$", "comp_total", 0, 1),
        (r"^Compensation, benefits, and related costs$", "comp_base", 0, 1),
        (r"^Total operating expenses$", "opex", 0, 1),
        (r"^Net operating income$", "operating_income", 0, 1),
        (r"^Income before income taxes$", "pretax_income", 0, 1)]),
    (["Average AUM", "Investment advisory fees", "Total investment advisory fees"], [
        (r"^Average AUM$", "aum_avg", 0, 1000),
        (r"^Investment advisory annualized effective fee rate \(bps\)$", "fee_rate_reported_bps", 0, 1)]),
]


def _pick(nums: list[float | None], col: int | str):
    if not nums:
        return None, -1
    i = len(nums) - 1 if col == "last" else col
    return (nums[i], i) if i < len(nums) else (None, -1)


def parse_release(html: bytes, rules, meta: dict) -> list[dict]:
    sp = soup(html)
    out, done = [], set()
    for anchors, rrules in rules:
        for ti, t in find_tables(sp, *anchors):
            got = 0
            for label, nums, raw in rows(t):
                for rx, metric, col, scale in rrules:
                    if metric in done or not re.search(rx, label):
                        continue
                    if col == "row":  # BLK: [net flows, ending AUM, base fees+sec lending, ...] in $m
                        if len(nums) < 3:
                            continue
                        done.add(metric)
                        for k, x in zip(("net_flows", "aum_end", "fees_base_sec_lending"), nums[:3]):
                            out.append({**meta, "metric": k, "value": x * (1 if k != "x" else 1),
                                        "currency": "USD", "scale": "millions", "period_type": "Q",
                                        "locator": f"table#{ti} row='{norm(label)}' col={'012'[['net_flows','aum_end','fees_base_sec_lending'].index(k)]}",
                                        "raw_text": raw, "method": "html_table", "confidence": 1.0,
                                        "reviewed": True})
                        got += 1
                        continue
                    v, ci = _pick(nums, col)
                    if v is None:
                        continue
                    done.add(metric)
                    got += 1
                    out.append({**meta, "metric": metric, "value": v * scale, "currency": "USD",
                                "scale": "millions", "period_type": "Q",
                                "locator": f"table#{ti} row='{norm(label)}' col={ci}",
                                "raw_text": raw, "method": "html_table", "confidence": 1.0,
                                "reviewed": True})
            if got:
                break
    return out


TROW_10Q_RULES = [
    (["Investment advisory fees", "Net revenues", "Total operating expenses", "Compensation and related costs"], [
        (r"^Investment advisory fees$", "fees_investment_advisory", 0, 1),
        (r"^Net revenues$", "net_revenues", 0, 1),
        (r"^Compensation and related costs$", "comp_total", 0, 1),
        (r"^Total operating expenses$", "opex", 0, 1),
        (r"^Net operating income$", "operating_income", 0, 1),
        (r"^Income before income taxes$", "pretax_income", 0, 1)]),
]


IVZ_RULES = [
    (["Total operating revenues", "Employee compensation", "Total operating expenses"], [
        (r"^Investment management fees$", "fees_investment_management", 0, 1),
        (r"^Total operating revenues$", "net_revenues", 0, 1),
        (r"^Employee compensation$", "comp_total", 0, 1),
        (r"^Total operating expenses$", "opex", 0, 1),
        (r"^Operating income$", "operating_income", 0, 1),
        (r"^Income before income taxes$", "pretax_income", 0, 1)]),
    (["Operating revenues, U.S. GAAP basis", "Net revenues"], [
        (r"^Net revenues$", "net_revenues_adj", 0, 1)]),
    (["Operating income, U.S. GAAP basis", "Adjusted operating income"], [
        (r"^Adjusted operating income$", "operating_income_adj", 0, 1)]),
    (["Average AUM", "Ending Assets"], [
        (r"^Average AUM$", "aum_avg", 0, 1000)]),
]


BLK_RULES = [
    (["Total revenue", "Employee compensation and benefits", "Total expense", "Operating income"], [
        (r"^Investment advisory and administration fees$", "fees_advisory_admin", 0, 1),
        (r"^Total revenue$", "net_revenues", 0, 1),
        (r"^Employee compensation and benefits$", "comp_total", 0, 1),
        (r"^Total expense$", "opex", 0, 1),
        (r"^Operating income$", "operating_income", 0, 1),
        (r"^Income before income taxes$", "pretax_income", 0, 1)]),
    (["RESULTS BY PRODUCT TYPE"], [
        (r"^Total$", "_by_product_total", "row", 1)]),
    (["Operating income, as adjusted"], [
        (r"^Operating income, as adjusted", "operating_income_adj", 0, 1)]),
]
