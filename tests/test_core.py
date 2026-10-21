import duckdb
import pandas as pd
import pytest

from assetlens.extract import rollforward as RF
from assetlens.extract.tables import rows, soup, to_num
from assetlens.warehouse.build import DB

HTML = """<table>
<tr><td>Three months ended</td></tr>
<tr><td>Beginning balance</td><td>$</td><td>1,000.0</td><td>$</td><td>900.0</td></tr>
<tr><td>Net cash flows</td><td>(20.0</td><td>)</td><td>5.0</td></tr>
<tr><td>Net market appreciation</td><td>70.0</td><td>NM</td></tr>
<tr><td>Ending balance</td><td>$</td><td>1,050.0</td><td>$</td><td>905.0</td></tr></table>"""


def test_to_num():
    assert to_num("(1,234.5)") == -1234.5 and to_num("abc") is None


def test_rows_handles_parens_and_nm():
    r = rows(soup(HTML).find("table"))
    assert r[2][1] == [-20.0, 5.0] and r[3][1] == [70.0, None]


def test_rollforward_requires_closure():
    sp = soup(HTML)
    b = RF.best(sp, ["Beginning balance"])
    assert b and (b.begin, b.flows, b.market, b.end) == (1000.0, -20.0, 70.0, 1050.0)
    broken = HTML.replace("1,050.0", "1,200.0")
    assert RF.best(soup(broken), ["Beginning balance"]) is None  # does not close -> rejected


needs_db = pytest.mark.skipif(not DB.exists(), reason="warehouse not built")


@needs_db
def test_every_fact_has_provenance():
    con = duckdb.connect(str(DB), read_only=True)
    n = con.execute("select count(*) from fact_financials f left join fact_provenance p using(fact_id) "
                    "where p.fact_id is null").fetchone()[0]
    con.close()
    assert n == 0


@needs_db
def test_gs_rollforward_closes_and_chains():
    con = duckdb.connect(str(DB), read_only=True)
    d = con.execute("select period_end, metric, value from fact_financials where ticker='GS'").df()
    con.close()
    w = d.pivot_table(index="period_end", columns="metric", values="value").sort_index()
    w = w.dropna(subset=["aum_begin", "net_flows", "market", "aum_end"])
    acq = w["acquisitions"].fillna(0) if "acquisitions" in w else 0
    gap = (w.aum_begin + w.net_flows + w.market + acq - w.aum_end).abs()
    assert (gap <= 1000).all()


@needs_db
def test_benchmark_metric_definitions():
    con = duckdb.connect(str(DB), read_only=True)
    m = con.execute("select * from mart_peer_benchmark where fees is not null and aum_avg is not null").df()
    con.close()
    assert ((m.fees * 4 / m.aum_avg * 10000 - m.fee_yield_bps).abs() < 1e-6).all()
    assert m.fee_yield_bps.between(1, 100).all()


@needs_db
def test_phase2_peers_present_and_chained():
    con = duckdb.connect(str(DB), read_only=True)
    m = con.execute("select ticker, count(*) n, count(fee_yield_bps) y from mart_peer_benchmark group by 1").df().set_index("ticker")
    assert {"MS", "JPM", "BEN"} <= set(m.index) and m.loc["JPM", "y"] >= 6 and m.loc["BEN", "y"] >= 20
    f = con.execute("select ticker, period_end, metric, value from fact_financials where ticker in ('JPM','BEN') "
                    "and metric in ('aum_begin','aum_end')").df()
    con.close()
    for t, g in f.groupby("ticker"):
        p = g.pivot_table(index="period_end", columns="metric", values="value").dropna().sort_index()
        gap = (p.aum_begin - p.aum_end.shift(1)).dropna().abs()
        assert (gap < 0.001 * p.aum_end.iloc[1:].values).all()
