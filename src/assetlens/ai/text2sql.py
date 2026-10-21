"""M17 - text-to-SQL agent over the marts (LangGraph): generate -> validate (sqlglot AST) -> execute (read-only) -> answer.

Generators are pluggable: `LLMGenerator` (via the provider-agnostic gateway; needs credentials) and `TemplateGenerator`
(deterministic rule-based baseline used for offline evaluation and as a fallback).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TypedDict

import duckdb
import pandas as pd
import sqlglot
from langgraph.graph import END, StateGraph
from sqlglot import exp

from assetlens.ai.gateway import Gateway
from assetlens.warehouse.build import DB

SCHEMA: dict[str, str] = {
    "mart_peer_benchmark": "ticker (GS,BLK,TROW,IVZ,MS,JPM,BEN), period_end (quarter end date), aum_end, aum_avg, net_flows, fees, net_revenues, op_income, comp, "
                           "fee_yield_bps, organic_growth_ann, fee_yield_t4q_bps, organic_growth_t4q, op_margin, op_margin_t4q, comp_ratio, comp_ratio_t4q, "
                           "operating_leverage_yoy, revenue_yoy, aum_yoy. $ in millions; ratios are fractions.",
    "mart_fee_compression": "ticker, slope_bps_per_year, ci_low, ci_high, pct_per_year, significant, start, end, n",
    "mart_aum_decomposition": "ticker, aum_begin, aum_end, net_flows, market_fx_other, organic_pct_of_begin, market_pct_of_begin (since 2022-03-31)",
    "fact_forecast": "scenario (base,bull,bear,stress), t (1..8), period_end, net_revenues, comp, noncomp, provision, pretax, pretax_margin, aus_total, mgmt_fees ($m)",
    "mart_budget_variance": "period_end, budget_revenue, budget_pretax, actual_revenue, actual_pretax, prior_year_revenue, rev_variance, rev_variance_pct, pretax_variance, flag",
    "mart_profitability_by_business": "period_end, method (revenue,headcount,abc,step_down,reciprocal), business (PE,FIMA,LIQ,ALT,PWM,PBL), net_revenues, "
                                      "contribution_margin, allocated_musd, fully_allocated_pretax, fully_allocated_margin (SYNTHETIC)",
    "mart_allocation_rank_sensitivity": "method, business, revenue, pretax, margin, rank (T4Q; SYNTHETIC)",
    "mart_market_sensitivity": "ticker, n, beta_equity, beta_bond, r2, alpha_q",
    "mart_sales_productivity": "period_end, region, advisors, revenue, nna, aum, clients, quota_attainment, revenue_per_advisor (SYNTHETIC)",
    "comparability_flags": "ticker, topic, note",
    "mart_montecarlo_prob": "margin_below_threshold_q8, margin_below_threshold_any, threshold, n",
    "mart_backtest_summary": "model, horizon, mape, bias, n",
    "fact_savings": "initiative_id, category, target_savings_musd, implementation_cost_musd, headcount_impact, owner, confidence, realised_to_date_musd (SYNTHETIC)",
}
ALLOWED = set(SCHEMA)
FORBIDDEN_FUNCS = {"read_csv", "read_csv_auto", "read_parquet", "read_json", "glob", "copy", "pragma", "install", "load", "attach", "system", "getenv"}
MAX_ROWS, MAX_JOINS = 1000, 3


class SQLRejected(Exception):
    pass


def validate(sql: str) -> str:
    """AST validation: single read-only SELECT over allow-listed tables, bounded joins, forced LIMIT. Returns the safe SQL."""
    try:
        trees = sqlglot.parse(sql, read="duckdb")
    except sqlglot.errors.ParseError as e:
        raise SQLRejected(f"parse error: {e}") from e
    if len(trees) != 1 or trees[0] is None:
        raise SQLRejected("exactly one statement allowed")
    t = trees[0]
    if not isinstance(t, (exp.Select, exp.Union, exp.With)) and not isinstance(t, exp.Subquery):
        raise SQLRejected(f"only SELECT allowed, got {type(t).__name__}")
    ctes = {c.alias_or_name.lower() for c in t.find_all(exp.CTE)}
    for tb in t.find_all(exp.Table):
        name = tb.name.lower()
        if name not in ALLOWED and name not in ctes:
            raise SQLRejected(f"table not allowed: {name}")
        if tb.args.get("db") or tb.args.get("catalog"):
            raise SQLRejected("schema-qualified tables not allowed")
    for f in t.find_all(exp.Anonymous):
        if f.name.lower() in FORBIDDEN_FUNCS:
            raise SQLRejected(f"function not allowed: {f.name}")
    for f in t.find_all(exp.Func):
        if type(f).__name__.lower() in FORBIDDEN_FUNCS:
            raise SQLRejected("function not allowed")
    joins = list(t.find_all(exp.Join))
    if len(joins) > MAX_JOINS:
        raise SQLRejected("too many joins")
    for j in joins:
        if j.args.get("kind") == "CROSS" or (not j.args.get("on") and not j.args.get("using") and j.args.get("kind") != "NATURAL"):
            raise SQLRejected("cross joins not allowed")
    lim = t.args.get("limit")
    if lim is None:
        t = t.limit(MAX_ROWS)
    else:
        try:
            if int(lim.expression.name) > MAX_ROWS:
                t = t.limit(MAX_ROWS)
        except (ValueError, AttributeError):
            raise SQLRejected("non-constant LIMIT")
    return t.sql(dialect="duckdb")


def execute(sql: str) -> pd.DataFrame:
    con = duckdb.connect(str(DB), read_only=True, config={"enable_external_access": False})
    try:
        return con.execute(sql).df()
    finally:
        con.close()


# ------------------------------------------------------------------ generators
METRICS = {
    "fee yield": "fee_yield_t4q_bps", "yield on fees": "fee_yield_t4q_bps", "fee rate": "fee_yield_t4q_bps",
    "organic growth": "organic_growth_t4q", "margin": "op_margin_t4q", "operating margin": "op_margin_t4q",
    "comp ratio": "comp_ratio_t4q", "compensation ratio": "comp_ratio_t4q",
    "aum": "aum_end", "assets under management": "aum_end", "aus": "aum_end", "assets under supervision": "aum_end",
    "net flows": "net_flows", "net revenue": "net_revenues", "revenue": "net_revenues"}
TICKERS = {"goldman": "GS", "gs": "GS", "blackrock": "BLK", "blk": "BLK", "t. rowe": "TROW", "t rowe": "TROW", "trow": "TROW", "invesco": "IVZ",
           "ivz": "IVZ", "morgan stanley": "MS", "ms": "MS", "jpmorgan": "JPM", "jpm": "JPM", "franklin": "BEN", "ben": "BEN"}
SCEN = ["base", "bull", "bear", "stress"]
BIZ = {"public equity": "PE", "fixed income": "FIMA", "liquidity": "LIQ", "alternatives": "ALT", "private wealth": "PWM", "private banking": "PBL"}


def _find(d: dict, q: str):
    for k in sorted(d, key=len, reverse=True):
        if re.search(rf"(?<![a-z]){re.escape(k)}(?![a-z])", q):
            return d[k]
    return None


class TemplateGenerator:
    """Deterministic baseline: keyword/pattern routing to SQL templates. Returns None when it cannot answer."""

    def __call__(self, question: str, error: str | None = None) -> str | None:
        q = question.lower().strip("?. ")
        metric, tkr = _find(METRICS, q), _find(TICKERS, q)
        qm = re.search(r"q([1-4])\s*(20\d{2})", q)
        scen = next((s for s in SCEN if re.search(rf"\b{s}\b", q)), None)
        mm = re.search(r"(step[_ -]down|reciprocal|abc|headcount|revenue)(?:[- ]based)?\s+(?:method|allocation)|(?:method|under)\s+(step[_ -]down|reciprocal|abc|headcount|revenue)", q)
        method = (mm.group(1) or mm.group(2)).replace("-", "_").replace(" ", "_") if mm else None
        biz = _find(BIZ, q)
        if "fee compression" in q or "fee trend" in q or "slope" in q:
            return f"select ticker, slope_bps_per_year from mart_fee_compression {f'where ticker = {chr(39)}{tkr}{chr(39)}' if tkr else ''} order by slope_bps_per_year"
        if "monte carlo" in q or "probability" in q:
            return "select margin_below_threshold_q8 from mart_montecarlo_prob"
        if "backtest" in q and "mape" in q:
            return "select model, avg(mape) as mape from mart_backtest_summary group by model order by mape"
        if "beta" in q and tkr:
            return f"select beta_equity, beta_bond from mart_market_sensitivity where ticker = '{tkr}'"
        if scen and ("forecast" in q or "scenario" in q or "quarter" in q or "pre-tax" in q or "pretax" in q):
            tq = re.search(r"(?:quarter|t)\s*(\d)", q)
            t = int(tq.group(1)) if tq else 8
            col = "pretax_margin" if "margin" in q else ("pretax" if "pre-tax" in q or "pretax" in q or "earnings" in q else "net_revenues")
            return f"select {col} from fact_forecast where scenario = '{scen}' and t = {t}"
        if (biz or "business" in q) and ("rank" in q or "margin" in q or "profit" in q):
            m = method or "abc"
            if biz and "rank" in q:
                return f"select rank from mart_allocation_rank_sensitivity where method = '{m}' and business = '{biz}'"
            if biz:
                return f"select margin from mart_allocation_rank_sensitivity where method = '{m}' and business = '{biz}'"
            return f"select business, margin from mart_allocation_rank_sensitivity where method = '{m}' order by margin desc"
        if metric and any(w in q for w in ["lowest", "smallest", "worst"]):
            return (f"select ticker from mart_peer_benchmark where {metric} is not null and period_end = (select max(period_end) from mart_peer_benchmark b2 "
                    f"where b2.ticker = mart_peer_benchmark.ticker and b2.{metric} is not null) order by {metric} asc limit 1")
        if metric and any(w in q for w in ["highest", "largest", "best", "top", "which company", "which firm", "leads"]):
            return (f"select ticker from mart_peer_benchmark where {metric} is not null and period_end = (select max(period_end) from mart_peer_benchmark b2 "
                    f"where b2.ticker = mart_peer_benchmark.ticker and b2.{metric} is not null) order by {metric} desc limit 1")
        if metric and tkr and qm:
            pe = {"1": "03-31", "2": "06-30", "3": "09-30", "4": "12-31"}[qm.group(1)]
            return f"select {metric} from mart_peer_benchmark where ticker = '{tkr}' and period_end = '{qm.group(2)}-{pe}'"
        if metric and tkr and any(w in q for w in ["latest", "current", "now", "most recent", "what is", "what was", "what's"]):
            return f"select {metric} from mart_peer_benchmark where ticker = '{tkr}' and {metric} is not null order by period_end desc limit 1"
        if "budget" in q and ("variance" in q or "flag" in q):
            return "select period_end, rev_variance, rev_variance_pct from mart_budget_variance where actual_revenue is not null order by period_end"
        if "savings" in q and ("total" in q or "target" in q):
            return "select sum(target_savings_musd) as target from fact_savings"
        return None


class LLMGenerator:
    def __init__(self, gw: Gateway):
        self.gw = gw

    def __call__(self, question: str, error: str | None = None) -> str | None:
        schema = "\n".join(f"- {t}: {c}" for t, c in SCHEMA.items())
        system = ("You write one DuckDB SELECT statement answering the question. Use ONLY these tables:\n" + schema +
                  "\nReturn only SQL, no prose. Quarter-end dates look like '2026-06-30'. Ratios are fractions. Never modify data.")
        prompt = question + (f"\nYour previous SQL failed: {error}. Fix it." if error else "")
        sql = self.gw.complete(system, prompt, max_tokens=500).text.strip()
        return re.sub(r"^```(?:sql)?|```$", "", sql, flags=re.M).strip() or None


# ------------------------------------------------------------------ LangGraph agent
class State(TypedDict, total=False):
    question: str
    sql: str | None
    error: str | None
    attempts: int
    result: pd.DataFrame | None
    answer: str


def build_agent(generator, max_attempts: int = 2):
    def gen(s: State) -> State:
        sql = generator(s["question"], s.get("error"))
        return {"sql": sql, "attempts": s.get("attempts", 0) + 1, "error": None if sql else "generator could not produce SQL"}

    def val(s: State) -> State:
        if not s.get("sql"):
            return {}
        try:
            return {"sql": validate(s["sql"]), "error": None}
        except SQLRejected as e:
            return {"error": f"rejected: {e}"}

    def run(s: State) -> State:
        if s.get("error") or not s.get("sql"):
            return {}
        try:
            return {"result": execute(s["sql"])}
        except duckdb.Error as e:
            return {"error": f"execution error: {e}"}

    def fin(s: State) -> State:
        if s.get("error"):
            return {"answer": f"Unable to answer: {s['error']}"}
        r = s["result"]
        return {"answer": r.to_string(index=False) if len(r) else "No rows"}

    def route(s: State) -> str:
        if s.get("error") and s.get("attempts", 0) < max_attempts and s.get("sql") is not None:
            return "gen"
        return "fin"

    g = StateGraph(State)
    g.add_node("gen", gen); g.add_node("val", val); g.add_node("run", run); g.add_node("fin", fin)
    g.set_entry_point("gen")
    g.add_edge("gen", "val"); g.add_edge("val", "run")
    g.add_conditional_edges("run", route, {"gen": "gen", "fin": "fin"})
    g.add_edge("fin", END)
    return g.compile()


def ask(question: str, generator=None) -> dict:
    agent = build_agent(generator or TemplateGenerator())
    out = agent.invoke({"question": question, "attempts": 0})
    return dict(question=question, sql=out.get("sql"), answer=out.get("answer"), error=out.get("error"), result=out.get("result"))


@dataclass
class EvalItem:
    question: str
    gold_sql: str
    category: str = "lookup"


def _norm(df: pd.DataFrame) -> list[tuple]:
    rows = []
    for r in df.itertuples(index=False):
        rows.append(tuple(round(float(x), 4) if isinstance(x, (int, float)) and not isinstance(x, bool) else str(x) for x in r))
    return sorted(rows, key=str)


def execution_accuracy(items: list[EvalItem], generator=None) -> dict:
    gen = generator or TemplateGenerator()
    ok = answered = 0
    fails = []
    for it in items:
        gold = execute(validate(it.gold_sql))
        res = ask(it.question, gen)
        if res["result"] is not None:
            answered += 1
            if _norm(res["result"]) == _norm(gold):
                ok += 1
                continue
        fails.append((it.question, res["sql"], res["error"]))
    return dict(n=len(items), correct=ok, answered=answered, execution_accuracy=ok / len(items), coverage=answered / len(items), failures=fails)
