"""Monthly fully allocated profitability pack (HTML). Synthetic businesses; revenue phased evenly within the quarter
(assumption - public revenue is quarterly only); costs are the month's GL postings; shared pools allocated with ABC."""
from __future__ import annotations

import duckdb
import pandas as pd

from assetlens.warehouse.build import DB
from assetlens.warehouse.docs_gen import ROOT

DISC = ("AssetLens is an independent educational project built from public SEC/FRED data. Business-unit data are synthetic "
        "and do not represent any company's internal figures. Nothing here is investment advice.")


def month_table(month: str) -> pd.DataFrame:
    con = duckdb.connect(str(DB), read_only=True)
    gl = con.execute("""select strftime(posting_date,'%Y-%m') m, owner, sum(amount_musd) as spend from fact_gl group by 1,2""").df()
    pnl = con.execute("select * from fact_business_pnl").df()
    drv = con.execute("select * from fact_drivers").df()
    con.close()
    pnl["period_end"] = pd.to_datetime(pnl.period_end)
    gl["m"] = gl.m.astype(str)
    qe = pd.Period(month, "M").asfreq("Q").end_time.normalize()
    cur = gl[gl.m == month].set_index("owner").spend
    prv = gl[gl.m == str(pd.Period(month, "M") - 1)].set_index("owner").spend

    def build(cost: pd.Series, qend) -> pd.DataFrame:
        p = pnl[pnl.period_end == qend].set_index("business")
        d = drv[pd.to_datetime(drv.period_end) == qend].pivot(index="pool", columns="business", values="quantity")
        share = d.div(d.sum(axis=1), axis=0)
        pools = cost.reindex(share.index).fillna(0)
        alloc = (share.mul(pools, axis=0)).sum()
        out = pd.DataFrame(index=p.index)
        out["revenue"] = p.net_revenues / 3
        out["provision"] = p.provision / 3
        out["direct_cost"] = cost.reindex(p.index).fillna(0)
        out["contribution"] = out.revenue - out.provision - out.direct_cost
        out["allocated_abc"] = alloc.reindex(p.index)
        out["fully_allocated"] = out.contribution - out.allocated_abc
        out["fa_margin"] = out.fully_allocated / out.revenue
        return out

    this = build(cur, qe)
    prev_q = qe if str(pd.Period(month, "M") - 1) in gl.m.values and pd.Period(month, "M") - 1 >= pd.Period(qe, "Q").asfreq("M", "s") else qe - pd.offsets.QuarterEnd(1)
    last = build(prv, pd.Timestamp(prev_q))
    this["prior_month_fa"] = last.fully_allocated
    this["mom_change"] = this.fully_allocated - this.prior_month_fa
    this["commentary"] = "[owner commentary required]"
    return this


def run(month: str = "2026-06") -> str:
    t = month_table(month)
    tot = t.select_dtypes("number").sum()
    fmt = {c: "{:,.1f}" for c in ["revenue", "provision", "direct_cost", "contribution", "allocated_abc", "fully_allocated", "prior_month_fa", "mom_change"]}
    fmt["fa_margin"] = "{:.1%}"
    html = f"""<html><head><meta charset="utf-8"><title>Profitability pack {month}</title>
<style>body{{font-family:Segoe UI,Arial;margin:32px;color:#0b0b0b}}table{{border-collapse:collapse}}td,th{{border-bottom:1px solid #ddd;padding:6px 10px;text-align:right}}
th:first-child,td:first-child{{text-align:left}}th{{background:#f1f1ee}}.n{{color:#52514e;font-size:12px}}</style></head><body>
<h2>Fully allocated profitability by business - {month} ($m) - SYNTHETIC</h2>
<p class="n">Revenue = quarterly segment revenue / 3 (phasing assumption). Costs = month's general-ledger postings. Shared pools allocated by activity-based costing.</p>
{t.drop(columns=['commentary']).to_html(float_format=lambda x: f"{x:,.1f}" if abs(x) > 1.5 else f"{x:.3f}", border=0)}
<p><b>Total fully allocated pre-tax:</b> {tot.fully_allocated:,.1f}; total revenue {tot.revenue:,.1f}; margin {tot.fully_allocated / tot.revenue:.1%}.</p>
<h3>Commentary (owner to complete)</h3><ul>{''.join(f'<li><b>{b}</b>: [owner commentary required]</li>' for b in t.index)}</ul>
<p class="n">{DISC}</p></body></html>"""
    out = ROOT / "outputs" / "reports" / f"profitability_pack_{month.replace('-', '')}.html"
    out.write_text(html, encoding="utf8")
    return str(out)


if __name__ == "__main__":
    print(run())
