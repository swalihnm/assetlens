"""Consolidate GS facts: latest-vintage selection, Q4 = FY - 9M derivation, reconciliation."""
from __future__ import annotations

import pandas as pd

FLOW_METRICS = ["rev_mgmt_other_fees", "rev_incentive_fees", "rev_private_banking_lending",
                "rev_equity_investments", "rev_debt_investments", "rev_investments", "net_revenues",
                "provision", "comp_benefits", "other_opex", "opex", "acquisitions", "pretax_earnings", "flow_alternatives", "flow_equity",
                "flow_fixed_income", "flow_long_term", "flow_liquidity", "net_flows", "market"]
STOCK_METRICS = ["aus_end", "aus_alternatives", "aus_equity", "aus_fixed_income",
                 "aus_long_term", "aus_liquidity", "aus_total"]


def harmonise(df: pd.DataFrame) -> pd.DataFrame:
    """Within each filing+period, derive rev_investments = equity + debt where only the split exists."""
    key = ["accession_no", "period_end", "period_type"]
    have = df[df.metric == "rev_investments"].set_index(key).index
    eq = df[df.metric == "rev_equity_investments"].set_index(key)
    de = df[df.metric == "rev_debt_investments"].set_index(key)
    add = []
    for k in eq.index.intersection(de.index):
        if k in have:
            continue
        row = eq.loc[k].copy()
        row["metric"] = "rev_investments"
        row["value"] = eq.loc[k, "value"] + de.loc[k, "value"]
        row["method"] = "derived"
        row["locator"] = "equity investments + debt investments"
        add.append(row.rename_axis(key).reset_index() if False else row.to_frame().T.assign(
            **dict(zip(key, k))))
    return pd.concat([df] + add, ignore_index=True) if add else df


def latest(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Latest filed value per (metric, period). Also returns a restatement log."""
    df = harmonise(df).sort_values("filed_date")
    key = ["ticker", "unit", "metric", "period_end", "period_type"]
    g = df.groupby(key)
    cur = g.tail(1).copy()
    first = g.head(1).set_index(key)["value"]
    cur_i = cur.set_index(key)
    chg = cur_i[(cur_i["value"] - first.reindex(cur_i.index)).abs() > 0.5].copy()
    chg["original_value"] = first.reindex(chg.index)
    return cur, chg.reset_index()


def quarterly(cur: pd.DataFrame, perimeter: str = "AWM") -> pd.DataFrame:
    """Wide quarterly table with Q4 derived as FY - 9M YTD (provenance noted in `derived`)."""
    d = cur[cur.perimeter == perimeter]
    v = d.set_index(["metric", "period_end", "period_type"])["value"]
    ends = sorted(d.period_end.unique())
    out: dict[tuple[str, str], tuple[float, str]] = {}
    for m in FLOW_METRICS + STOCK_METRICS + ["aus_begin"]:
        for pe in ends:
            if (m, pe, "Q") in v.index:
                out[(m, pe)] = (v[(m, pe, "Q")], "reported")
    for m in FLOW_METRICS:
        for pe in ends:
            if pe.endswith("-12-31") and (m, pe, "FY") in v.index:
                y = pe[:4]
                ytd = (m, f"{y}-09-30", "YTD")
                if ytd in v.index:
                    out[(m, pe)] = (v[(m, pe, "FY")] - v[ytd], "derived: FY - 9M YTD")
    for m in STOCK_METRICS:
        for pe in ends:
            if pe.endswith("-12-31") and (m, pe, "FY") in v.index:
                out[(m, pe)] = (v[(m, pe, "FY")], "reported")
    rows = [{"metric": k[0], "period_end": k[1], "value": val[0], "derivation": val[1]}
            for k, val in out.items()]
    df = pd.DataFrame(rows)
    wide = df.pivot_table(index="period_end", columns="metric", values="value", aggfunc="first")
    # aus_begin = prior-quarter ending balance; use reported begin where available
    wide = wide.sort_index()
    wide["aus_end"] = wide["aus_end"].fillna(wide.get("aus_total"))
    prior = wide["aus_end"].shift(1)
    wide["aus_begin"] = wide["aus_begin"].fillna(prior)
    wide["derived_q4"] = [pe.endswith("-12-31") for pe in wide.index]
    return wide


def annual(cur: pd.DataFrame, perimeter: str = "AWM") -> pd.DataFrame:
    d = cur[(cur.perimeter == perimeter) & (cur.period_type == "FY")]
    return d.pivot_table(index="period_end", columns="metric", values="value", aggfunc="first")


def reconcile(w: pd.DataFrame) -> pd.DataFrame:
    res = []

    def add(check, pe, ok, detail):
        res.append(dict(check=check, period_end=pe, passed=bool(ok), detail=detail))

    prev_end = None
    for pe, r in w.iterrows():
        # revenue lines sum to net revenues
        lines = [c for c in ["rev_mgmt_other_fees", "rev_incentive_fees",
                             "rev_private_banking_lending", "rev_investments"] if pd.notna(r.get(c))]
        if pd.notna(r.get("net_revenues")) and len(lines) == 4:
            tot = sum(r[c] for c in lines)
            add("revenue_lines_sum", pe, abs(tot - r["net_revenues"]) <= 1.5,
                f"sum={tot:.0f} reported={r['net_revenues']:.0f}")
        # pre-tax = net revenue - provision - opex
        if all(pd.notna(r.get(c)) for c in ["net_revenues", "provision", "comp_benefits", "other_opex", "opex", "acquisitions", "pretax_earnings"]):
            calc = r["net_revenues"] - r["provision"] - r["opex"]
            add("pretax_identity", pe, abs(calc - r["pretax_earnings"]) <= 1.5,
                f"calc={calc:.0f} reported={r['pretax_earnings']:.0f}")
        # AUS roll-forward closes
        if all(pd.notna(r.get(c)) for c in ["aus_begin", "net_flows", "market", "aus_end"]):
            calc = r["aus_begin"] + r["net_flows"] + r["market"] + (r["acquisitions"] if pd.notna(r.get("acquisitions")) else 0)
            tol = max(0.005 * r["aus_end"], 1000)
            add("rollforward_closes", pe, abs(calc - r["aus_end"]) <= tol,
                f"calc={calc:,.0f} end={r['aus_end']:,.0f}")
            if prev_end is not None:
                add("begin_equals_prior_end", pe, abs(r["aus_begin"] - prev_end) <= 1000,
                    f"begin={r['aus_begin']:,.0f} prior_end={prev_end:,.0f}")
        # flows by class sum to total
        cls = ["flow_alternatives", "flow_equity", "flow_fixed_income", "flow_liquidity"]
        if all(pd.notna(r.get(c)) for c in cls + ["net_flows"]):
            add("flows_by_class_sum", pe, abs(sum(r[c] for c in cls) - r["net_flows"]) <= 1000,
                f"sum={sum(r[c] for c in cls):,.0f} total={r['net_flows']:,.0f}")
        if pd.notna(r.get("aus_end")):
            prev_end = r["aus_end"]
    return pd.DataFrame(res)
