"""Live evaluation (Ollama cloud by default) of (1) RAG answer generation with citations and (2) LLM table extraction
against warehouse ground truth. Both run through the guard rails (citation check, numeric grounding, closure)."""
from __future__ import annotations

import json
import re
import sys

import duckdb
import pandas as pd

from assetlens.ai import llm_extract, rag
from assetlens.ai.gateway import Gateway
from assetlens.extract import rollforward as RF
from assetlens.extract.tables import find_tables, soup
from assetlens.ingest.edgar_client import EdgarClient
from assetlens.warehouse.build import DB


def rag_eval(gw: Gateway, k: int = 4) -> dict:
    idx = rag.build_index()
    cited = grounded = answered = 0
    rows = []
    for q, t, subs in rag.EVAL:
        hits = idx.search(q, k, ticker=t)
        ctx = " ".join(c.text for c, _ in hits).lower().replace(",", "")
        out = rag.answer(idx, q, k=k, gateway=gw, ticker=t)
        txt = out["answer"]
        has_cite = bool(re.search(r"\[\d\]", txt))
        nums = [n.replace(",", "") for n in re.findall(r"\d[\d,]*\.?\d*", re.sub(r"\[\d\]", "", txt)) if len(n.replace(",", "")) >= 2]
        ok_nums = all(n in ctx for n in nums)
        declined = bool(re.search(r"does not|doesn't|not contain|cannot|no information", txt, re.I))
        answered += not declined
        cited += has_cite
        grounded += ok_nums
        rows.append(dict(q=q, cited=has_cite, numbers_grounded=ok_nums, declined=declined, n_numbers=len(nums)))
    n = len(rag.EVAL)
    return dict(n=n, cited_rate=cited / n, numeric_grounded_rate=grounded / n, answered_rate=answered / n, detail=rows)


CASES = [("IVZ", "2026-06-30", ["Beginning Assets", "Ending Assets"], 1.0), ("TROW", "2026-06-30", ["Three months ended", "Net cash flows"], 1.0),
         ("BEN", "2026-06-30", ["Beginning AUM", "Ending AUM"], 1.0)]


def extraction_eval(gw: Gateway) -> dict:
    """Give the model the actual release table; compare with the closure-checked deterministic parse in the warehouse."""
    con = duckdb.connect(str(DB), read_only=True)
    c = EdgarClient()
    out = []
    for t, pe, anchors, _ in CASES:
        rel = pd.read_csv(f"data/interim/{t}_releases.csv", dtype={"cik": str}).dropna(subset=["release_url"])
        for r in rel.itertuples():
            if pd.Timestamp(r.filingDate) < pd.Timestamp(pe) or pd.Timestamp(r.filingDate) > pd.Timestamp(pe) + pd.Timedelta(days=45):
                continue
            sp = soup(c.get(r.release_url))
            best = RF.best(sp, anchors, 100, cols={0, 3, 4} if t == "TROW" else {0})
            if not best:
                continue
            tbl = [tb for ti, tb in find_tables(sp, *anchors) if ti == best.table][0]
            rec = llm_extract.extract(gw, tbl, dict(ticker=t, period_end=pe))
            truth = dict(begin=best.begin, end=best.end, net_flows=best.flows)
            ext = json.loads(rec["extracted"]) if rec["extracted"] else {}
            correct = bool(ext) and all(abs(ext[k] - truth[k]) < 0.06 for k in truth)
            out.append(dict(ticker=t, status=rec["status"], correct=correct, reason=rec["reason"][:80]))
            break
    con.close()
    acc = [o for o in out if o["status"] == "pending_review"]
    return dict(n=len(out), accepted=len(acc), accepted_correct=sum(o["correct"] for o in acc),
                rejected=len(out) - len(acc), accepted_wrong=sum(not o["correct"] for o in acc), detail=out)


def run(provider: str = "ollama", model: str = "gemma4:31b-cloud") -> dict:
    gw = Gateway(provider, model=model, log=True)
    return dict(model=model, rag=rag_eval(gw), extraction=extraction_eval(gw))


if __name__ == "__main__":
    print(json.dumps(run(*sys.argv[1:3]), indent=1, default=str))
