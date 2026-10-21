"""GS AWM extraction from 10-Q / 10-K MD&A tables (deterministic, with provenance).

Every column of every matched table is stored (current period AND recast comparatives), so the
warehouse keeps all vintages and marts can take the latest filed value (restatement handling).
"""
from __future__ import annotations

import pandas as pd

from assetlens.extract.tables import find_tables, rows, soup
from assetlens.ingest.edgar_client import EdgarClient

# (label prefix -> canonical metric). Order matters: first match wins.
SEG_LABELS = [
    ("Management and other fees", "rev_mgmt_other_fees"),
    ("Incentive fees", "rev_incentive_fees"),
    ("Private banking and lending", "rev_private_banking_lending"),
    ("Equity investments", "rev_equity_investments"),
    ("Debt investments", "rev_debt_investments"),
    ("Lending and debt investments", "rev_lending_debt_legacy"),
    ("Investments", "rev_investments"),
    ("Net revenues", "net_revenues"),
    ("Total net revenues", "net_revenues"),
    ("Provision for credit losses", "provision"),
    ("Compensation and benefits", "comp_benefits"),   # ASU 2023-07 segment expense (10-K FY2024+)
    ("Other operating expenses", "other_opex"),
    ("Total operating expenses", "opex"),
    ("Operating expenses", "opex"),
    ("Pre-tax earnings", "pretax_earnings"),
]
FLOW_LABELS = {
    "Beginning balance": "aus_begin",
    "Alternative investments": "flow_alternatives",
    "Equity": "flow_equity",
    "Fixed income": "flow_fixed_income",
    "Total long-term AUS net inflows/(outflows)": "flow_long_term",
    "Liquidity products": "flow_liquidity",
    "Total AUS net inflows/(outflows)": "net_flows",
    "Acquisitions": "acquisitions",
    "Net market appreciation/(depreciation)": "market",
    "Ending balance": "aus_end",
}
END_LABELS = {"Alternative investments": "aus_alternatives", "Equity": "aus_equity",
              "Fixed income": "aus_fixed_income", "Total long-term AUS": "aus_long_term",
              "Liquidity products": "aus_liquidity", "Total AUS": "aus_total"}
FIRST_AWM_FILING = "2023-02-01"  # FY2022 10-K: first filing with the recast AWM perimeter


def _seg_metric(label: str) -> str | None:
    for pre, m in SEG_LABELS:
        if label.startswith(pre):
            return m
    return None


def _columns(f, hdr_nums: list[float]) -> list[tuple[str, str]]:
    """Map table columns -> (period_end, period_type) from the header-year row."""
    mmdd = f.reportDate[5:]
    if f.form == "10-K":
        return [(f"{int(y)}-12-31", "FY") for y in hdr_nums]
    if len(hdr_nums) == 2:  # Q1: current / prior quarter
        return [(f"{int(y)}-{mmdd}", "Q") for y in hdr_nums]
    return [(f"{int(hdr_nums[0])}-{mmdd}", "Q"), (f"{int(hdr_nums[1])}-{mmdd}", "Q"),
            (f"{int(hdr_nums[2])}-{mmdd}", "YTD"), (f"{int(hdr_nums[3])}-{mmdd}", "YTD")]


def _fact(f, metric, value, scale, period, col, label, raw, tbl):
    return dict(ticker="GS", unit="AWM", metric=metric, period_end=period[0], period_type=period[1],
                value=value * scale, currency="USD", scale="millions",
                perimeter="AWM" if f.filingDate >= FIRST_AWM_FILING else "legacy_AM",
                source_url=f.url, accession_no=f.accessionNumber, form_type=f.form,
                filed_date=f.filingDate, document=f.primaryDocument,
                locator=f"table#{tbl} row='{label}' col={col}", raw_text=raw,
                method="html_table", confidence=1.0, reviewed=True)


def _emit(f, tbl_idx, r, label_map, scale, cols, out):
    seen = set()
    for label, nums, raw in r:
        m = label_map(label)
        if not m or not nums or m in seen:
            continue
        seen.add(m)
        for c, per in enumerate(cols[: len(nums)]):
            out.append(_fact(f, m, nums[c], scale, per, c, label, raw, tbl_idx))


def _header(r):
    for label, nums, _ in r:
        if label.startswith("$ in") and len(nums) in (2, 3, 4) and all(1990 < n < 2100 for n in nums):
            return nums
    return None


def extract_filing(client: EdgarClient, f) -> list[dict]:
    sp = soup(client.get(f.url))
    out: list[dict] = []
    for i, t in find_tables(sp, "Management and other fees", "Pre-tax earnings", "Incentive fees"):
        r = rows(t)
        if any("Global Banking" in l for l, _, _ in r) or not any(l.endswith("net revenues") or l == "Net revenues" for l, _, _ in r):
            continue
        h = _header(r)
        if h:
            _emit(f, i, r, _seg_metric, 1, _columns(f, h), out)
            break
    for i, t in find_tables(sp, "Beginning balance", "Net market appreciation", "Ending balance"):
        r = rows(t)
        if not any(l.startswith("Total AUS net") for l, _, _ in r):
            continue
        h = _header(r)
        if h:
            _emit(f, i, r, FLOW_LABELS.get, 1000, _columns(f, h), out)
            break
    for i, t in find_tables(sp, "Asset Class", "Total long-term AUS", "Liquidity products"):
        r = rows(t)
        h = _header(r)
        if h:  # balance-sheet-date table: columns are [current, prior-year] as of the same date
            mmdd = f.reportDate[5:]
            cols = [(f"{int(y)}-{mmdd}", "Q") for y in h]
            seen = set()
            for label, nums, raw in r:
                m = END_LABELS.get(label)
                if m and nums and m not in seen:
                    seen.add(m)
                    for c, per in enumerate(cols[: len(nums)]):
                        out.append(_fact(f, m, nums[c], 1000, per, c, label, raw, i))
            break
    return out


def run(client: EdgarClient, manifest: pd.DataFrame) -> pd.DataFrame:
    fl = manifest[(manifest.ticker == "GS") & manifest.form.isin(["10-Q", "10-K"])]
    facts = []
    for f in fl.itertuples():
        got = extract_filing(client, f)
        print(f.form, f.reportDate, len(got), "facts")
        facts += got
    return pd.DataFrame(facts)


# ---- Exhibit 99.1 (earnings release) for quarters whose 10-Q is not yet filed ----
def extract_release(client: EdgarClient, url: str, accession: str, filed: str, period_end: str) -> list[dict]:
    sp = soup(client.get(url))
    f = type("F", (), dict(url=url, accessionNumber=accession, form="8-K-EX99.1", filingDate=filed,
                           primaryDocument=url.split("/")[-1], reportDate=period_end))
    out: list[dict] = []
    per = (period_end, "Q")
    for i, t in find_tables(sp, "Management and other fees", "Private banking and lending", "Net revenues"):
        r = rows(t)
        if any("Global Banking" in l for l, _, _ in r):
            continue
        for label, nums, raw in r:
            m = _seg_metric(label)
            if m and nums:
                out.append(_fact(f, m, nums[0], 1, per, 0, label, raw, i))
        if out:
            break
    for i, t in find_tables(sp, "ROLLFORWARD"):
        in_flows = False
        for label, nums, raw in rows(t):
            if label.startswith("ROLLFORWARD"):
                in_flows = True
                continue
            lab = label.replace(" / ", "/")
            if lab.startswith("Total long-term AUS net"):
                lab = "Total long-term AUS net inflows/(outflows)"
            m = (FLOW_LABELS if in_flows else END_LABELS).get(lab)
            if m and len(nums) >= 3:
                out.append(_fact(f, m, nums[-3], 1000, per, 0, label, raw, i))
        break
    return out
