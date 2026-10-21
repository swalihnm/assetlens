"""M17 - RAG over filings: hybrid retrieval (BM25 + dense LSA embeddings, reciprocal-rank fusion), answers cite the
accession number and section. Dense vectors are TF-IDF + truncated SVD (LSA) so the pipeline runs offline; swap in a
neural embedding model by replacing `Index._embed` (documented limitation)."""
from __future__ import annotations

import pickle
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from rank_bm25 import BM25Okapi
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer

from assetlens.extract.tables import soup
from assetlens.ingest.edgar_client import EdgarClient

ROOT = Path(__file__).resolve().parents[3]
CACHE = ROOT / "data" / "interim" / "rag_index.pkl"
TOKEN = re.compile(r"[a-z0-9]+(?:\.[0-9]+)?")


def tok(s: str) -> list[str]:
    return TOKEN.findall(s.lower())


@dataclass
class Chunk:
    text: str
    ticker: str
    form: str
    accession: str
    period: str
    section: str


def _chunks_from_html(html: bytes, meta: dict, words: int = 170) -> list[Chunk]:
    sp = soup(html)
    for t in sp(["table", "script", "style"]):
        t.decompose()
    lines = [re.sub(r"\s+", " ", x).strip() for x in sp.get_text("\n").split("\n")]
    lines = [x for x in lines if x]
    out, buf, section = [], [], "Document start"
    for ln in lines:
        is_head = len(ln) < 95 and not ln.endswith((".", ",", ";")) and sum(c.isupper() for c in ln) >= 2 and len(ln.split()) >= 2
        if is_head and not re.fullmatch(r"[\d\s,.$%()-]+", ln):
            if len(" ".join(buf).split()) > 60:
                out.append(Chunk(" ".join(buf), section=section, **meta)); buf = []
            section = ln
            continue
        buf.append(ln)
        if len(" ".join(buf).split()) >= words:
            out.append(Chunk(" ".join(buf), section=section, **meta)); buf = []
    if len(" ".join(buf).split()) > 40:
        out.append(Chunk(" ".join(buf), section=section, **meta))
    return out


def corpus_docs() -> list[tuple[str, dict]]:
    m = pd.read_csv(ROOT / "data" / "raw" / "manifest.csv", dtype={"cik": str})
    docs = []
    for t in ("GS", "TROW", "IVZ", "MS", "JPM", "BEN"):
        q = m[(m.ticker == t) & (m.form == "10-Q")].sort_values("reportDate")
        if len(q):
            r = q.iloc[-1]
            docs.append((r.url, dict(ticker=t, form="10-Q", accession=r.accessionNumber, period=r.reportDate)))
    b = m[(m.ticker == "BLK") & (m.form == "10-Q")].sort_values("reportDate")
    if len(b):
        r = b.iloc[-1]
        docs.append((r.url, dict(ticker="BLK", form="10-Q", accession=r.accessionNumber, period=r.reportDate)))
    for t, f in [("GS", "data/interim/gs_3q26.txt")]:
        pass
    rel = {"GS": ("https://www.sec.gov/Archives/edgar/data/0000886982/000088698226000529/a3q26gsearningsresults.htm", "0000886982-26-000529", "2026-09-30")}
    for t, (u, acc, pe) in rel.items():
        docs.append((u, dict(ticker=t, form="8-K Ex.99.1", accession=acc, period=pe)))
    for t in ("TROW", "IVZ", "BLK"):
        e = pd.read_csv(ROOT / "data" / "interim" / f"{t}_releases.csv", dtype={"cik": str}).dropna(subset=["release_url"]).iloc[-1]
        docs.append((e.release_url, dict(ticker=t, form="8-K Ex.99.1", accession=e.accessionNumber, period=str(e.filingDate))))
    return docs


class Index:
    def __init__(self, chunks: list[Chunk], dims: int = 128):
        self.chunks = chunks
        self.docs = [tok(c.text) for c in chunks]
        self.bm25 = BM25Okapi(self.docs)
        self.tfidf = TfidfVectorizer(tokenizer=tok, lowercase=False, token_pattern=None, sublinear_tf=True, min_df=2)
        X = self.tfidf.fit_transform([c.text for c in chunks])
        self.svd = TruncatedSVD(n_components=min(dims, X.shape[1] - 1), random_state=0).fit(X)
        self.emb = self._norm(self.svd.transform(X))

    @staticmethod
    def _norm(a):
        return a / (np.linalg.norm(a, axis=1, keepdims=True) + 1e-9)

    def _embed(self, texts: list[str]):
        return self._norm(self.svd.transform(self.tfidf.transform(texts)))

    def search(self, q: str, k: int = 5, mode: str = "hybrid", ticker: str | None = None) -> list[tuple[Chunk, float]]:
        bm = np.asarray(self.bm25.get_scores(tok(q)))
        de = self.emb @ self._embed([q])[0]
        if ticker:
            mask = np.array([c.ticker == ticker for c in self.chunks])
            bm, de = np.where(mask, bm, -1e9), np.where(mask, de, -1e9)
        if mode == "bm25":
            score = bm
        elif mode == "dense":
            score = de
        else:  # reciprocal rank fusion
            rb, rd = (-bm).argsort().argsort(), (-de).argsort().argsort()
            score = 1 / (60 + rb) + 1 / (60 + rd)
        top = np.argsort(-score)[:k]
        return [(self.chunks[i], float(score[i])) for i in top]


def build_index(force: bool = False) -> Index:
    if CACHE.exists() and not force:
        return pickle.loads(CACHE.read_bytes())
    c = EdgarClient()
    chunks: list[Chunk] = []
    for url, meta in corpus_docs():
        chunks += _chunks_from_html(c.get(url), meta)
    idx = Index(chunks)
    CACHE.write_bytes(pickle.dumps(idx))
    return idx


def answer(idx: Index, question: str, k: int = 4, gateway=None, ticker: str | None = None) -> dict:
    hits = idx.search(question, k, ticker=ticker)
    cites = [dict(ticker=c.ticker, form=c.form, accession=c.accession, period=c.period, section=c.section) for c, _ in hits]
    ctx = "\n\n".join(f"[{i + 1}] ({c.ticker} {c.form} {c.accession}, {c.section}) {c.text}" for i, (c, _) in enumerate(hits))
    if gateway is not None:
        txt = gateway.complete("Answer ONLY from the numbered context. Cite sources as [n]. If the context does not contain the answer, say so.",
                               f"Question: {question}\n\nContext:\n{ctx}", max_tokens=400).text
    else:   # extractive fallback: the context sentence with the most question-term overlap
        qs = set(tok(question))
        sents = [(len(qs & set(tok(s))), s, i) for i, (c, _) in enumerate(hits) for s in re.split(r"(?<=[.!?])\s+", c.text)]
        best = max(sents, key=lambda x: x[0])
        txt = f"{best[1]} [{best[2] + 1}]"
    return dict(answer=txt, citations=cites)


EVAL = [  # (question, ticker or None, substrings of which at least one must appear in the top-k text)
    ("What drove the increase in Management and other fees in Asset & Wealth Management?", "GS", ["average assets under supervision"]),
    ("Why did Incentive fees change in Asset & Wealth Management?", "GS", ["incentive fees"]),
    ("What did the decrease in Private banking and lending net revenues reflect?", "GS", ["private banking and lending"]),
    ("How is assets under supervision defined?", "GS", ["assets under supervision"]),
    ("What was Goldman Sachs net revenues for the third quarter?", "GS", ["18.68 billion", "18,679"]),
    ("What were T. Rowe Price assets under management at quarter end?", "TROW", ["1,893.4", "assets under management"]),
    ("What is T. Rowe Price's effective fee rate?", "TROW", ["effective fee"]),
    ("Which factors affected T. Rowe net cash flows?", "TROW", ["net cash flows"]),
    ("What were Invesco's net long-term flows?", "IVZ", ["net long-term flows", "long-term"]),
    ("What is Invesco's adjusted operating margin?", "IVZ", ["adjusted operating margin"]),
    ("How did BlackRock describe organic base fee growth?", "BLK", ["organic base fee growth", "base fee"]),
    ("What were BlackRock's net inflows?", "BLK", ["net inflows"]),
    ("What drove Morgan Stanley Investment Management asset management fees?", "MS", ["investment management"]),
    ("How did JPMorgan Asset & Wealth Management assets under management change?", "JPM", ["assets under management"]),
    ("What are Franklin's long-term net flows?", "BEN", ["net flows"]),
    ("What risks relate to fee pressure in asset management?", None, ["fee", "pressure", "compression"]),
    ("How are performance fees recognised?", None, ["performance", "incentive"]),
    ("What do the filings say about market appreciation affecting assets?", None, ["market appreciation", "market"]),
    ("Which firms report assets under management?", None, ["assets under management"]),
    ("What affects net interest income in private banking?", "GS", ["net interest", "private banking"]),
]


def evaluate(idx: Index, k: int = 5) -> dict:
    res = {}
    for mode in ("bm25", "dense", "hybrid"):
        hit = 0
        for q, t, subs in EVAL:
            txt = " ".join(c.text.lower() for c, _ in idx.search(q, k, mode, t))
            hit += any(s.lower() in txt for s in subs)
        res[mode] = hit / len(EVAL)
    res["n_questions"], res["chunks"], res["k"] = len(EVAL), len(idx.chunks), k
    return res


if __name__ == "__main__":
    idx = build_index()
    print(evaluate(idx))
    a = answer(idx, "What drove the increase in Management and other fees in Asset & Wealth Management?", ticker="GS")
    print(a["answer"][:300], a["citations"][:2])
