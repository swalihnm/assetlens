"""Phase-2 peers: Morgan Stanley (Investment Management and Wealth Management segments), JPMorgan (Asset & Wealth
Management segment) from 10-Q/10-K tables; Franklin Resources (BEN) from 8-K Ex.99.1.

Franklin's fiscal quarters end Mar/Jun/Sep/Dec, so quarterly data already align with calendar quarters
(calendarisation matters only for annual figures, which this project does not use).
Q4 flow metrics for 10-K filers are derived as FY minus the sum of Q1-Q3.
"""
from __future__ import annotations

import re

import pandas as pd

from assetlens.extract import releases as R
from assetlens.extract import rollforward as RF
from assetlens.extract.run_peers import INT, ROOT, meta, quarter_end_before
from assetlens.extract.tables import find_tables, norm, rows, soup
from assetlens.ingest.edgar_client import EdgarClient

TOL_BN = 1.6    # rounding tolerance for $bn roll-forwards


def _fact(mt: dict, metric: str, value: float, scale: float, locator: str, raw: str, ptype: str = "Q") -> dict:
    return {**mt, "metric": metric, "value": value * scale, "currency": "USD", "scale": "millions", "period_type": ptype,
            "locator": locator, "raw_text": raw, "method": "html_table", "confidence": 1.0, "reviewed": True}


def _pnl(sp, mt, anchors, labelmap: dict[str, str], ptype: str) -> list[dict]:
    out = []
    for ti, t in find_tables(sp, *anchors):
        got = {}
        for label, nums, raw in rows(t):
            for rx, metric in labelmap.items():
                if metric not in got and re.search(rx, label) and nums:
                    got[metric] = _fact(mt, metric, nums[0], 1, f"table#{ti} row='{norm(label)}' col=0", raw, ptype)
        if len(got) >= len(labelmap) - 1:
            return list(got.values())
    return out


MS_IM = {r"^Asset management and related fees": "fees_asset_management", r"^Net revenues$": "net_revenues",
         r"^Compensation and benefits$": "comp_total", r"^Total non-interest expenses$": "opex",
         r"^Income before provision for income taxes$": "pretax_income"}
MS_WM = {r"^Asset management$": "fees_asset_management", r"^Net revenues$": "net_revenues", r"^Compensation and benefits$": "comp_total",
         r"^Total non-interest expenses$": "opex", r"^Income before provision for income taxes$": "pretax_income"}


def ms_aum(sp, mt, begin_date: str) -> list[dict]:
    """IM roll-forward from the product table's 'Total' row: [begin, inflows, outflows, net flows, distributions, market, end]."""
    for ti, t in enumerate(sp.find_all("table")):
        head = norm(t.get_text(" "))
        low = head.lower()
        if not all(k in low for k in ("inflows", "outflows", "market impact")):
            continue
        mm = re.search(r"at (\w+ \d{1,2}, \d{4})", head, re.IGNORECASE)
        if not mm or pd.Timestamp(mm.group(1)) != pd.Timestamp(begin_date):
            continue
        rr = rows(t)
        names = {l.strip().lower() for l, _, _ in rr}
        if not ({"equity", "fixed income"} <= names):          # IM product table (not Wealth Management client assets)
            continue
        for label, nums, raw in rr:
            if label.strip() == "Total" and len(nums) == 5:          # older layout: begin, inflows, outflows, market, end
                b, inf, outf, mk, e = nums
                nf, dist = inf + outf, 0.0
                if abs(b + nf + mk - e) > TOL_BN:
                    continue
                loc = f"table#{ti} row='Total' (closure-checked)"
                return [_fact(mt, k, v, 1000, loc, raw) for k, v in
                        [("aum_begin", b), ("net_flows", nf), ("aum_other_change", dist), ("market", mk), ("aum_end", e)]]
            if label.strip() == "Total" and len(nums) >= 7:
                b, _, _, nf, dist, mk, e = nums[:7]
                if abs(b + nf + dist + mk - e) > TOL_BN:
                    continue
                loc = f"table#{ti} row='Total' (closure-checked)"
                return [_fact(mt, k, v, 1000, loc, raw) for k, v in
                        [("aum_begin", b), ("net_flows", nf), ("aum_other_change", dist), ("market", mk), ("aum_end", e)]]
    return []


def run_ms(client: EdgarClient, m: pd.DataFrame) -> pd.DataFrame:
    out = []
    for r in m[(m.ticker == "MS") & m.form.isin(["10-Q", "10-K"])].itertuples():
        if r.reportDate < "2019-03-31":
            continue
        sp = soup(client.get(r.url))
        annual = r.form == "10-K"
        pt = "FY" if annual else "Q"
        for unit, lm, anchors in [("IM", MS_IM, ["Asset management and related fees", "Performance-based income", "Net revenues", "Income before provision"]),
                                  ("WM", MS_WM, ["Asset management", "Transactional", "Net interest", "Net revenues", "Compensation and benefits"])]:
            mt = meta("MS", unit, r.reportDate, r.url, r.accessionNumber, r.form, r.filingDate)
            out += _pnl(sp, mt, anchors, lm, pt)
        mt = meta("MS", "IM", r.reportDate, r.url, r.accessionNumber, r.form, r.filingDate)
        pe = pd.Timestamp(r.reportDate)
        begin = (pe - pd.offsets.YearEnd(1)).strftime("%Y-%m-%d") if annual else (pe - pd.offsets.QuarterEnd(1)).strftime("%Y-%m-%d")
        out += [{**x, "period_type": pt} for x in ms_aum(sp, mt, begin)]
    return pd.DataFrame(out)


JPM_LM = {r"^Asset management fees$": "fees_asset_management", r"^Total net revenue$": "net_revenues", r"^Compensation expense$": "comp_total",
          r"^Total noninterest expense$": "opex", r"^Income before income tax expense$": "pretax_income"}


def jpm_aum(sp, mt) -> list[dict]:
    for ti, t in find_tables(sp, "Assets under management rollforward", "Market/performance/other impacts"):
        rr = rows(t)
        names = [l for l, _, _ in rr]
        try:
            i0 = names.index("Assets under management rollforward")
        except ValueError:
            continue
        seg = rr[i0 + 1:]
        b = f = mk = e = None
        flows = []
        in_flows = False
        for label, nums, raw in seg:
            if label.startswith("Client assets"):
                break
            if label.startswith("Beginning balance") and nums:
                b = nums[0]
            elif label.startswith("Net asset flows"):
                in_flows = True
            elif in_flows and label.startswith("Market/performance") and nums:
                mk, in_flows = nums[0], False
            elif in_flows and nums:
                flows.append(nums[0])
            elif label.startswith("Ending balance") and nums:
                e = nums[0]
                break
        if None in (b, mk, e) or not flows:
            continue
        f = sum(flows)
        if abs(b + f + mk - e) > TOL_BN:
            continue
        loc = f"table#{ti} AUM rollforward (closure-checked)"
        return [_fact(mt, k, v, 1000, loc, "", "Q") for k, v in
                [("aum_begin", b), ("net_flows", f), ("market", mk), ("aum_end", e)]]
    return []


def run_jpm(client: EdgarClient, m: pd.DataFrame) -> pd.DataFrame:
    out = []
    for r in m[(m.ticker == "JPM") & m.form.isin(["10-Q", "10-K"])].itertuples():
        if r.reportDate < "2019-03-31":
            continue
        sp = soup(client.get(r.url))
        mt = meta("JPM", "AWM", r.reportDate, r.url, r.accessionNumber, r.form, r.filingDate)
        pt = "FY" if r.form == "10-K" else "Q"
        out += _pnl(sp, mt, ["Revenue by line of business", "Asset management fees", "Total net revenue", "Compensation expense"], JPM_LM, pt)
        if r.form == "10-Q":
            out += jpm_aum(sp, mt)
        else:   # 10-K: AUM roll-forward is annual; keep FY roll for Q4 derivation
            out += [{**x, "period_type": "FY"} for x in jpm_aum(sp, mt)]
    return pd.DataFrame(out)


BEN_RULES = [
    (["Total operating revenues", "Compensation and benefits", "Operating Income"], [
        (r"^Investment management fees$", "fees_investment_management", 0, 1),
        (r"^Total operating revenues$", "net_revenues", 0, 1),
        (r"^Compensation and benefits$", "comp_total", 0, 1),
        (r"^Total operating expenses$", "opex", 0, 1),
        (r"^Operating Income$", "operating_income", 0, 1)]),
    (["Beginning AUM", "Ending AUM", "Average AUM"], [(r"^Average AUM$", "aum_avg", 0, 1000)]),
]


def run_ben(client: EdgarClient) -> pd.DataFrame:
    out = []
    rel = pd.read_csv(INT / "BEN_releases.csv", dtype={"cik": str})
    for r in rel.itertuples():
        if not isinstance(r.release_url, str):
            continue
        pe = quarter_end_before(r.filingDate)
        if pe < "2019-03-31":
            continue
        html = client.get(r.release_url)
        mt = meta("BEN", "Company", pe, r.release_url, r.accessionNumber, "8-K-EX99.1", r.filingDate)
        out += R.parse_release(html, BEN_RULES, mt)
        roll = RF.best(soup(html), ["Beginning AUM", "Ending AUM"], 100, cols={0})
        if roll:
            loc = f"table#{roll.table} (closure-checked)"
            out += [_fact(mt, k, v, 1000, loc, roll.raw) for k, v in
                    [("aum_begin", roll.begin), ("net_flows", roll.flows), ("market", roll.market), ("aum_other_change", roll.other), ("aum_end", roll.end)]]
    return pd.DataFrame(out)


def derive_q4(df: pd.DataFrame) -> pd.DataFrame:
    """Q4 = FY - (Q1+Q2+Q3) for flow metrics; Q4 begin = Q3 end; stock metrics (aum_end) taken from FY."""
    flows = {"fees_asset_management", "net_revenues", "comp_total", "opex", "pretax_income", "net_flows", "market", "aum_other_change"}
    rows_ = []
    fy = df[df.period_type == "FY"]
    for (t, u, mtr, pe), g in fy.groupby(["ticker", "unit", "metric", "period_end"]):
        year = pe[:4]
        q = df[(df.ticker == t) & (df.unit == u) & (df.metric == mtr) & (df.period_type == "Q") & df.period_end.str.startswith(year)
               & (df.period_end < pe)]
        base = g.iloc[-1].to_dict()
        if mtr == "aum_end":
            rows_.append({**base, "period_type": "Q", "locator": base["locator"] + " (FY balance = Q4 balance)"})
        elif mtr in flows and len(q) == 3:
            rows_.append({**base, "period_type": "Q", "value": base["value"] - q.value.sum(), "method": "derived",
                          "locator": f"DERIVED Q4 = FY ({base['accession_no']}) - Q1..Q3"})
    return pd.concat([df[df.period_type != "FY"], pd.DataFrame(rows_)], ignore_index=True)


SKIP: set[str] = set()


def run_all() -> dict[str, pd.DataFrame]:
    c = EdgarClient()
    m = pd.read_csv(ROOT / "data" / "raw" / "manifest.csv", dtype={"cik": str})
    res = {}
    for t, fn in [("MS", lambda: derive_q4(run_ms(c, m))), ("JPM", lambda: derive_q4(run_jpm(c, m))), ("BEN", lambda: run_ben(c))]:
        if (INT / f"{t}_raw_facts.csv").exists() and t in SKIP:
            continue
        try:
            df = fn()
        except Exception as e:      # network hiccup: keep going, rerun resumes from the disk cache
            print(t, "failed:", repr(e)[:120])
            continue
        df.to_csv(INT / f"{t}_raw_facts.csv", index=False)
        res[t] = df
    return res


if __name__ == "__main__":
    import sys
    SKIP.update(sys.argv[1:])
    pd.set_option("display.width", 250)
    for t, df in run_all().items():
        w = df[df.unit.isin(["IM", "AWM", "Company"])].pivot_table(index="period_end", columns="metric", values="value", aggfunc="first")
        print(t, len(df), "quarters:", len(w), "with AUM roll:", int(w.get("aum_end", pd.Series(dtype=float)).notna().sum()),
              "with revenue:", int(w.get("net_revenues", pd.Series(dtype=float)).notna().sum()))
