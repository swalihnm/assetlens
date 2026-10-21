"""M17 - variance / benchmark commentary: template drafts (offline) or LLM drafts, both passed through the numeric guardrail."""
from __future__ import annotations

import duckdb
import pandas as pd

from assetlens.ai import guardrail
from assetlens.ai.gateway import Gateway
from assetlens.warehouse.build import DB


def facts_and_drafts() -> list[tuple[str, dict[str, float]]]:
    """Template drafts, each with the exact facts it used."""
    con = duckdb.connect(str(DB), read_only=True)
    bud = con.execute("select * from mart_budget_variance").df()
    b = con.execute("select * from mart_peer_benchmark").df()
    fc = con.execute("select * from fact_forecast where scenario in ('base','stress') and t = 8").df()
    con.close()
    out = []
    for r in bud.dropna(subset=["actual_revenue"]).itertuples():
        q = pd.Timestamp(r.period_end)
        f = dict(actual=r.actual_revenue, budget=r.budget_revenue, var=r.rev_variance, var_pct=r.rev_variance_pct * 100, py=r.prior_year_revenue)
        t = (f"Net revenues in Q{q.quarter} {q.year} were ${r.actual_revenue:,.0f}m, {abs(r.rev_variance):,.0f}m "
             f"{'above' if r.rev_variance >= 0 else 'below'} the top-down budget of ${r.budget_revenue:,.0f}m "
             f"({r.rev_variance_pct * 100:+.1f}%), and {((r.actual_revenue / r.prior_year_revenue - 1) * 100):.1f}% versus the prior-year quarter "
             f"(${r.prior_year_revenue:,.0f}m).")
        f["yoy"] = (r.actual_revenue / r.prior_year_revenue - 1) * 100
        out.append((t, f))
    for tkr, g in b.sort_values("period_end").groupby("ticker"):
        g = g[g.fee_yield_t4q_bps.notna()]
        if len(g) < 5:
            continue
        a, p = g.iloc[-1], g.iloc[-5]
        f = dict(yield_now=a.fee_yield_t4q_bps, yield_prev=p.fee_yield_t4q_bps, chg=a.fee_yield_t4q_bps - p.fee_yield_t4q_bps,
                 organic=a.organic_growth_t4q * 100)
        t = (f"{tkr} trailing-four-quarter fee yield was {a.fee_yield_t4q_bps:.1f} bps, {a.fee_yield_t4q_bps - p.fee_yield_t4q_bps:+.1f} bps over the "
             f"last year, with organic growth of {a.organic_growth_t4q * 100:.1f}%.")
        out.append((t, f))
    base, stress = fc[fc.scenario == "base"].iloc[0], fc[fc.scenario == "stress"].iloc[0]
    f = dict(base_margin=base.pretax_margin * 100, stress_margin=stress.pretax_margin * 100, gap=(base.pretax_margin - stress.pretax_margin) * 100)
    out.append((f"By the eighth forecast quarter the pre-tax margin is {base.pretax_margin * 100:.1f}% in the base case and "
                f"{stress.pretax_margin * 100:.1f}% under stress, a gap of {(base.pretax_margin - stress.pretax_margin) * 100:.1f} percentage points.", f))
    return out


def llm_draft(gw: Gateway, facts: dict[str, float], topic: str) -> str:
    system = "You are an FP&A analyst. Write 2 sentences. Use ONLY the provided numbers, exactly as given. Do not invent figures."
    return gw.complete(system, f"Topic: {topic}\nFacts: {facts}").text


def guarded(text: str, facts: dict[str, float]) -> dict:
    r = guardrail.verify(text, facts)
    return dict(text=text, approved=r.ok, unmatched=r.unmatched, checked=r.checked)


def seeded_catch_rate(n_per: int = 5) -> dict:
    """Wrong-number drafts: perturb one number in each template draft; the guardrail must block them all."""
    drafts = facts_and_drafts()
    caught, total, missed = 0, 0, []
    clean_pass = sum(guardrail.verify(t, f).ok for t, f in drafts)
    for i, (t, f) in enumerate(drafts):
        for s in range(n_per):
            bad, changed = guardrail.perturb(t, seed=i * 100 + s)
            total += 1
            if not guardrail.verify(bad, f).ok:
                caught += 1
            else:
                missed.append((bad, changed))
    return dict(clean_drafts=len(drafts), clean_pass=clean_pass, seeded=total, caught=caught, catch_rate=caught / total, missed=missed[:3])


if __name__ == "__main__":
    for t, f in facts_and_drafts()[:3]:
        print(t, guardrail.verify(t, f))
    print(seeded_catch_rate())
