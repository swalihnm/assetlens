"""M15 - export the star schema (Parquet + CSV) for Power BI and generate spot-check expectations."""
from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from assetlens.warehouse.build import DB

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "outputs" / "powerbi"

COMPANIES = pd.DataFrame([
    ("GS", "Goldman Sachs", "Asset & Wealth Management segment", "AUS", "12-31"),
    ("BLK", "BlackRock", "Whole company", "AUM", "12-31"),
    ("TROW", "T. Rowe Price", "Whole company", "AUM", "12-31"),
    ("IVZ", "Invesco", "Whole company", "AUM", "12-31"),
    ("MS", "Morgan Stanley", "Investment Management segment", "AUM", "12-31"),
    ("MSWM", "Morgan Stanley", "Wealth Management segment (P&L only)", "Client assets", "12-31"),
    ("JPM", "JPMorgan Chase", "Asset & Wealth Management segment", "AUM", "12-31"),
    ("BEN", "Franklin Resources", "Whole company", "AUM", "09-30")],
    columns=["ticker", "company", "unit_analysed", "asset_measure", "fiscal_year_end"])
SCENARIOS = pd.DataFrame({"scenario": ["base", "bull", "bear", "stress"], "sort": [2, 1, 3, 4]})


def dim_date(start="2018-01-01", end="2028-12-31") -> pd.DataFrame:
    """Daily calendar (role-playing: period-end date, filing date, posting date all relate to it)."""
    d = pd.DataFrame({"date": pd.date_range(start, end, freq="D")})
    d["year"], d["quarter_no"], d["month_no"] = d.date.dt.year, d.date.dt.quarter, d.date.dt.month
    d["quarter_key"] = d.year * 10 + d.quarter_no
    d["quarter_label"] = d.year.astype(str) + " Q" + d.quarter_no.astype(str)
    d["month_label"] = d.date.dt.strftime("%Y-%m")
    d["quarter_end_date"] = d.date + pd.offsets.QuarterEnd(0)
    d["is_quarter_end"] = d.date == d.quarter_end_date
    d["is_year_end"] = d.is_quarter_end & (d.quarter_no == 4)
    return d


def run() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB), read_only=True)
    q = lambda s: con.execute(s).df()
    tables: dict[str, pd.DataFrame] = {
        "dim_company": COMPANIES, "dim_date": dim_date(), "dim_scenario": SCENARIOS,
        "dim_metric": q("select distinct metric from fact_financials order by 1"),
        "dim_business": q("select * from dim_business"), "dim_region": q("select * from dim_region"),
        "dim_function": q("select * from dim_function"), "dim_advisor": q("select * from dim_advisor"),
        "dim_vendor": q("select vendor_id, vendor_name, category, tier, synthetic from dim_vendor"),
        "dim_initiative": q("select initiative_id, category, owner, depends_on, synthetic from fact_savings"),
        "fact_financials": q("""select f.fact_id, f.ticker, f.unit, f.metric, cast(f.period_end as date) period_end, f.value,
                             cast(p.filed_date as date) filed_date, p.accession_no, p.form_type, p.method
                             from fact_financials f join fact_provenance p using(fact_id)"""),
        "fact_benchmark": q("select * from mart_peer_benchmark"),
        "fact_forecast": q("select * from fact_forecast"),
        "fact_budget": q("select * from mart_budget_variance"),
        "fact_top_down_bottom_up": q("select * from mart_top_down_vs_bottom_up"),
        "fact_profitability": q("select * from mart_profitability_by_business"),
        "fact_allocation": q("select * from fact_allocation"),
        "fact_business_pnl": q("select * from fact_business_pnl"),
        "fact_headcount": q("select * from fact_headcount"),
        "fact_advisor_monthly": q("select * from fact_advisor_monthly"),
        "fact_savings": q("select * from fact_savings"),
        "fact_te": q("select * from fact_te"),
        "fact_gl": q("select txn_id, posting_date, period_end, cost_center, owner, region, category, vendor_id, is_comp, amount_musd, synthetic from fact_gl"),
        "mart_fee_compression": q("select * from mart_fee_compression"),
        "mart_aum_decomposition": q("select * from mart_aum_decomposition"),
        "comparability_flags": q("select * from comparability_flags"),
        # row-level security mapping (replace with real UPNs in your tenant)
        "security_user_map": pd.DataFrame([
            ("business.head.pe@example.com", "PE", "ALL"), ("business.head.alt@example.com", "ALT", "ALL"),
            ("regional.cfo.emea@example.com", "ALL", "EMEA"), ("regional.cfo.amer@example.com", "ALL", "AMER"),
            ("cfo@example.com", "ALL", "ALL")], columns=["user_principal_name", "business", "region"]),
    }
    for c in ("period_end",):
        for n, t in tables.items():
            if c in t.columns and t[c].dtype == object:
                t[c] = pd.to_datetime(t[c])
    for name, df in tables.items():
        df.to_parquet(OUT / f"{name}.parquet", index=False)
        if len(df) <= 300_000:
            df.to_csv(OUT / f"{name}.csv", index=False)
    # 12 spot checks for the DAX measures (compare in Power BI against these warehouse values)
    b = tables["fact_benchmark"]
    checks = []
    for tkr in ("GS", "BLK", "TROW", "IVZ"):
        r = b[(b.ticker == tkr) & b.fee_yield_t4q_bps.notna()].sort_values("period_end").iloc[-1]
        checks.append((tkr, str(r.period_end)[:10], "Fee Yield T4Q (bps)", round(float(r.fee_yield_t4q_bps), 4)))
        checks.append((tkr, str(r.period_end)[:10], "Ending AUM ($m)", round(float(r.aum_end), 1)))
    fc = tables["fact_forecast"]
    checks.append(("GS", "base t8", "Net Revenue forecast ($m)", round(float(fc[(fc.scenario == "base") & (fc.t == 8)].net_revenues.iloc[0]), 3)))
    checks.append(("GS", "stress t8", "Pre-tax margin", round(float(fc[(fc.scenario == "stress") & (fc.t == 8)].pretax_margin.iloc[0]), 5)))
    pr = tables["fact_profitability"]
    last = pr.period_end.max()
    x = pr[(pr.period_end == last) & (pr.method == "abc") & (pr.business == "LIQ")]
    checks.append(("LIQ", str(last)[:10], "Fully allocated margin (ABC)", round(float(x.fully_allocated_margin.iloc[0]), 5)))
    pd.DataFrame(checks, columns=["entity", "period", "measure", "expected_value"]).to_csv(OUT / "dax_spot_checks.csv", index=False)
    con.close()
    write_power_query(tables)
    return {n: len(t) for n, t in tables.items()}


def _mtype(dtype) -> str:
    k = str(dtype)
    if k.startswith(("int", "Int")):
        return "Int64.Type"
    if k.startswith(("float", "Float")):
        return "type number"
    if k.startswith("datetime"):
        return "type datetime"
    if k.startswith("bool"):
        return "type logical"
    return "type text"


def write_power_query(tables: dict[str, pd.DataFrame]) -> None:
    """One Power Query (M) script per table, with explicit column types. Set the FolderPath parameter."""
    nl = chr(10)
    pq = ROOT / "powerbi" / "powerquery"
    pq.mkdir(parents=True, exist_ok=True)
    (pq / "00_parameters.m").write_text(
        "// Create a Power Query parameter named FolderPath (type Text), for example:" + nl
        + '"C:\\Users\\you\\AssetLens\\outputs\\powerbi\\"' + nl, encoding="utf8")
    for name, df in tables.items():
        types = ("," + nl + "        ").join('{"%s", %s}' % (c, _mtype(t)) for c, t in df.dtypes.items())
        parquet = len(df) > 300_000
        if parquet:
            src = 'Parquet.Document(File.Contents(FolderPath & "%s.parquet"), [Compressed = true])' % name
        else:
            src = ('Csv.Document(File.Contents(FolderPath & "%s.csv"), '
                   '[Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv])' % name)
        lines = ["let", "    Source = " + src + ","]
        prev = "Source"
        if not parquet:
            lines.append("    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),")
            prev = "Promoted"
        lines += ["    Typed = Table.TransformColumnTypes(" + prev + ", {", "        " + types, '    }, "en-US")', "in", "    Typed"]
        (pq / f"{name}.m").write_text(nl.join(lines) + nl, encoding="utf8")


if __name__ == "__main__":
    print(run())
