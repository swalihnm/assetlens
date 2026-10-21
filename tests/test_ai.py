import json

import pytest

from assetlens.ai import guardrail, llm_extract, text2sql
from assetlens.ai.eval_set import ADVERSARIAL, items
from assetlens.ai.gateway import Gateway
from assetlens.extract.tables import soup
from assetlens.warehouse.build import DB

db = pytest.mark.skipif(not DB.exists(), reason="warehouse not built")

HTML = """<table><tr><td>Three months ended</td></tr>
<tr><td>Beginning balance</td><td>$</td><td>1,000.0</td></tr><tr><td>Net cash flows</td><td>(20.0</td><td>)</td></tr>
<tr><td>Net market appreciation</td><td>70.0</td></tr><tr><td>Ending balance</td><td>$</td><td>1,050.0</td></tr></table>"""


def test_validator_rejects_every_adversarial_query():
    for s in ADVERSARIAL:
        with pytest.raises(text2sql.SQLRejected):
            text2sql.validate(s)


def test_validator_accepts_safe_select_and_adds_limit():
    out = text2sql.validate("select ticker from mart_peer_benchmark where ticker = 'GS'")
    assert "LIMIT 1000" in out
    assert "LIMIT 5" in text2sql.validate("select ticker from mart_peer_benchmark limit 5")


@db
def test_text2sql_baseline_execution_accuracy():
    r = text2sql.execution_accuracy(items())
    assert r["n"] >= 60 and r["execution_accuracy"] >= 0.75


def test_guardrail_rounding_ok_and_wrong_number_blocked():
    facts = {"y": 34.7782, "g": 0.1493}
    assert guardrail.verify("Fee yield was 34.8 bps and organic growth 14.9%.", facts).ok
    assert not guardrail.verify("Fee yield was 36.8 bps.", facts).ok
    assert guardrail.verify("In Q3 2026 the yield was 34.8 bps.", facts).ok       # years / quarter tags ignored


@db
def test_seeded_hallucinated_numbers_all_blocked():
    from assetlens.ai.commentary import seeded_catch_rate
    r = seeded_catch_rate(n_per=25)
    assert r["clean_pass"] == r["clean_drafts"] and r["catch_rate"] == 1.0, r["missed"]


def test_llm_extraction_schema_grounding_and_queue(tmp_path, monkeypatch):
    tbl = soup(HTML).find("table")
    good = lambda s, p: json.dumps(dict(begin=1000, net_flows=-20, market=70, other=0, end=1050, unit="millions",
                                        source_rows=["Beginning balance", "Ending balance"]))
    halluc = lambda s, p: json.dumps(dict(begin=1000, net_flows=-20, market=75, other=0, end=1055, unit="millions",
                                          source_rows=["Beginning balance", "Ending balance"]))
    nonclosing = lambda s, p: json.dumps(dict(begin=1000, net_flows=-20, market=70, other=0, end=1200, unit="millions",
                                              source_rows=["Beginning balance", "Ending balance"]))
    ok = llm_extract.extract(Gateway("mock", mock_fn=good, log=False), tbl, {"doc": "t"})
    assert ok["status"] == "pending_review" and not ok["reviewed"]
    assert llm_extract.extract(Gateway("mock", mock_fn=halluc, log=False), tbl, {"doc": "t"})["status"] == "rejected"
    assert "closure" in llm_extract.extract(Gateway("mock", mock_fn=nonclosing, log=False), tbl, {"doc": "t"})["reason"]
    monkeypatch.setattr(llm_extract, "QUEUE", tmp_path / "q.csv")
    df = llm_extract.enqueue([ok])
    assert llm_extract.approved(tmp_path / "q.csv").empty      # nothing released without human review
    assert len(df) == 1


def test_gateway_mock_and_cost_log():
    g = Gateway("mock", mock_fn=lambda s, p: '{"a": 1}', log=False)
    assert g.json("s", "p") == {"a": 1} and g.calls[0].cost_usd == 0
