"""M7 - synthetic internal AWM data, calibrated to PUBLIC GS AWM segment totals.

Every table carries synthetic = True. Public totals (revenue lines, provision, operating expenses) are
reproduced exactly by construction (largest-remainder style normalisation), so the calibration test is tight.
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import yaml

from assetlens.warehouse.build import DB

ROOT = Path(__file__).resolve().parents[3]
CFG = yaml.safe_load((ROOT / "config" / "synthetic.yaml").read_text())
POOL_NAMES = {"TECH": "Technology", "OPS": "Operations", "RISK": "Risk & Compliance",
              "FHL": "Finance / HR / Legal", "PREM": "Premises"}
REGIONS = list(CFG["regions"])


def public_quarterly() -> pd.DataFrame:
    con = duckdb.connect(str(DB), read_only=True)
    f = con.execute("select period_end, metric, value from fact_financials where ticker='GS'").df()
    con.close()
    w = f.pivot_table(index="period_end", columns="metric", values="value", aggfunc="first").sort_index()
    q = CFG["quarters"]
    w = w[(w.index >= q["start"]) & ((w.index <= q["end"]) if q["end"] != "latest" else True)]
    need = ["rev_mgmt_other_fees", "rev_incentive_fees", "rev_private_banking_lending", "rev_investments",
            "net_revenues", "provision", "opex", "pretax_earnings", "aum_end", "aus_equity",
            "aus_fixed_income", "aus_liquidity", "aus_alternatives"]
    missing = [c for c in need if c not in w]
    if missing:
        raise RuntimeError(f"public inputs missing: {missing}")
    return w[need].dropna(subset=["net_revenues", "opex"])


def _norm(weights: np.ndarray, total: float) -> np.ndarray:
    return weights / weights.sum() * total


def business_pnl(pub: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    B = CFG["businesses"]
    keys = list(B)
    rows = []
    for pe, p in pub.iterrows():
        rev = pd.DataFrame(0.0, index=keys, columns=["mgmt_fees", "incentive_fees", "pbl", "investments"])
        mg = p.rev_mgmt_other_fees
        rev.loc["PWM", "mgmt_fees"] = mg * CFG["pwm_fee_share"]
        rest = mg * (1 - CFG["pwm_fee_share"])
        core = [k for k in keys if B[k]["fee_asset"]]
        wts = np.array([p[B[k]["fee_asset"]] * B[k]["yield_rel"] for k in core])
        rev.loc[core, "mgmt_fees"] = _norm(wts, rest)
        for k, s in CFG["incentive_split"].items():
            rev.loc[k, "incentive_fees"] = p.rev_incentive_fees * s
        rev.loc["PBL", "pbl"] = p.rev_private_banking_lending
        for k, s in CFG["investments_split"].items():
            rev.loc[k, "investments"] = p.rev_investments * s
        rev["net_revenues"] = rev.sum(axis=1)
        # costs: pools first (shared), remainder is direct and follows revenue x intensity (+ small noise)
        pool_total = p.opex * sum(CFG["pools"].values())
        direct_total = p.opex - pool_total
        inten = np.array([B[k]["intensity"] for k in keys]) * rng.normal(1, 0.03, len(keys))
        direct = _norm(rev.net_revenues.values * inten, direct_total)
        prov = np.zeros(len(keys))
        prov[keys.index("PBL")] = p.provision
        comp_share = 0.72  # direct costs are mostly compensation (assumption)
        d = rev.copy()
        d["direct_comp"] = direct * comp_share
        d["direct_noncomp"] = direct * (1 - comp_share)
        d["provision"] = prov
        d["contribution_margin"] = d.net_revenues - d.direct_comp - d.direct_noncomp - d.provision
        d["period_end"] = pe
        d["business"] = keys
        rows.append(d.reset_index(drop=True))
    out = pd.concat(rows, ignore_index=True)
    return out


def pool_costs(pub: pd.DataFrame) -> pd.DataFrame:
    rows = [dict(period_end=pe, pool=k, cost=p.opex * s) for pe, p in pub.iterrows()
            for k, s in CFG["pools"].items()]
    return pd.DataFrame(rows)


def drivers(pnl: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Activity drivers by business and pool; deliberately NOT proportional to revenue."""
    keys = list(CFG["businesses"])
    base = {  # relative consumption of each pool's driver (assumptions)
        "TECH": dict(PE=1.4, FIMA=1.2, LIQ=0.30, ALT=1.6, PWM=2.0, PBL=1.0),    # application usage
        "OPS":  dict(PE=1.3, FIMA=1.3, LIQ=1.00, ALT=0.9, PWM=1.8, PBL=1.1),    # transaction counts
        "RISK": dict(PE=1.0, FIMA=1.0, LIQ=0.30, ALT=1.5, PWM=1.0, PBL=2.4),    # accounts / tickets
        "FHL":  dict(PE=1.0, FIMA=1.0, LIQ=0.25, ALT=1.2, PWM=1.8, PBL=0.8),    # headcount
        "PREM": dict(PE=1.0, FIMA=1.0, LIQ=0.20, ALT=0.9, PWM=2.2, PBL=0.7),    # floor space
    }
    unit = {"TECH": "app_sessions", "OPS": "transactions", "RISK": "tickets_accounts",
            "FHL": "fte", "PREM": "sqft"}
    rows = []
    for pe in pnl.period_end.unique():
        for pool, rel in base.items():
            v = np.array([rel[k] for k in keys]) * rng.normal(1, 0.04, len(keys))
            v = v / v.sum() * 1_000_000
            for k, x in zip(keys, v):
                rows.append(dict(period_end=pe, pool=pool, business=k, driver=unit[pool], quantity=x))
    return pd.DataFrame(rows)


def support_usage() -> pd.DataFrame:
    """Support-to-support usage shares (for step-down / reciprocal). Rows: provider, cols: user."""
    pools = list(CFG["pools"])
    m = pd.DataFrame(0.0, index=pools, columns=pools)
    m.loc["TECH", ["OPS", "RISK", "FHL"]] = [0.10, 0.06, 0.05]
    m.loc["OPS", ["TECH", "RISK", "FHL"]] = [0.04, 0.05, 0.02]
    m.loc["RISK", ["TECH", "OPS"]] = [0.03, 0.04]
    m.loc["FHL", ["TECH", "OPS", "RISK", "PREM"]] = [0.06, 0.05, 0.05, 0.03]
    m.loc["PREM", ["TECH", "OPS", "RISK", "FHL"]] = [0.08, 0.07, 0.04, 0.05]
    return m.rename_axis("provider").reset_index().melt("provider", var_name="user", value_name="share")


def headcount(pnl: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    H = CFG["headcount"]
    keys = list(CFG["businesses"])
    rows = []
    qs = sorted(pnl.period_end.unique())
    for i, pe in enumerate(qs):
        total = H["start_total"] * (1 + H["annual_growth"]) ** (i / 4)
        fo = total * (1 - H["support_share"])
        d = pnl[pnl.period_end == pe].set_index("business")
        share = d.direct_comp / d.direct_comp.sum()
        for k in keys:
            for r, rs in CFG["regions"].items():
                rows.append(dict(period_end=pe, business=k, function="Front office", region=r,
                                 headcount=fo * share[k] * rs))
        for pool, ps in CFG["pools"].items():
            tot = sum(CFG["pools"].values())
            for r, rs in CFG["regions"].items():
                rows.append(dict(period_end=pe, business="SHARED", function=POOL_NAMES[pool], region=r,
                                 headcount=total * H["support_share"] * ps / tot * rs))
    return pd.DataFrame(rows)


def advisors(pnl: pd.DataFrame, rng: np.random.Generator) -> tuple[pd.DataFrame, pd.DataFrame]:
    A = CFG["advisors"]
    n = A["n"]
    qs = sorted(pnl.period_end.unique())
    q0 = pd.Timestamp(qs[0])
    hire = q0 - pd.to_timedelta(rng.uniform(0, 365 * 12, n), unit="D")
    new = rng.random(n) < 0.18  # hired during the window
    hire = np.where(new, q0 + pd.to_timedelta(rng.uniform(0, (pd.Timestamp(qs[-1]) - q0).days, n), unit="D"), hire)
    region = rng.choice(REGIONS, n, p=list(CFG["regions"].values()))
    book0 = np.exp(rng.normal(np.log(A["book_median_musd"]), A["book_sigma"], n))
    attr_q = 1 - (1 - A["annual_attrition"]) ** 0.25
    left = np.full(n, np.datetime64("NaT"), dtype="datetime64[ns]")
    for j in range(n):
        for pe in qs:
            if pd.Timestamp(pe) > pd.Timestamp(hire[j]) and rng.random() < attr_q:
                left[j] = pd.Timestamp(pe).to_datetime64()
                break
    dim = pd.DataFrame(dict(advisor_id=[f"ADV{j:04d}" for j in range(n)], hire_date=pd.to_datetime(hire),
                            left_date=left, region=region, book_initial_musd=book0, synthetic=True))
    dim["cohort"] = dim.hire_date.dt.year
    rows = []
    for pe in qs:
        t = pd.Timestamp(pe)
        active = (dim.hire_date <= t) & (dim.left_date.isna() | (dim.left_date > t))
        tenure = ((t - dim.hire_date).dt.days / 365.25).clip(lower=0)
        ramp = 1 / (1 + np.exp(-(tenure - 1.2) * 2.2))              # logistic productivity ramp
        w = (dim.book_initial_musd * (0.35 + 0.65 * ramp) * rng.lognormal(0, A["fee_bps_noise"], n)) * active
        pwm = pnl[(pnl.period_end == pe) & (pnl.business == "PWM")].iloc[0]
        rev = _norm(w.values, pwm.mgmt_fees)                          # calibrated to PWM mgmt fees
        aum_k = rev * 4 / A["fee_yield"] * rng.lognormal(0, 0.10, n)       # book consistent with an ~85 bps fee yield
        flows = rng.normal(0.012, 0.02, n) * aum_k * active.values          # NNA ~1.2% of book per quarter, noisy
        for j in np.flatnonzero(active.values):
            rows.append((pe, dim.advisor_id[j], rev[j], flows[j], aum_k[j], int(rng.integers(40, 160)), tenure[j]))
    fa = pd.DataFrame(rows, columns=["period_end", "advisor_id", "revenue_musd", "nna_musd", "aum_musd",
                                     "clients", "tenure_years"])
    fa["synthetic"] = True
    return dim, fa


CATS = ["Technology services", "Market data", "Professional fees", "Occupancy", "Travel & entertainment",
        "Marketing", "Communications", "Custody & admin", "Recruiting", "Other"]
CAT_W = np.array([0.24, 0.12, 0.14, 0.12, 0.05, 0.05, 0.06, 0.12, 0.04, 0.06])


def general_ledger(pnl: pd.DataFrame, pub: pd.DataFrame, rng: np.random.Generator) -> tuple[pd.DataFrame, pd.DataFrame]:
    """GL transactions whose quarterly totals equal public opex (comp postings + non-comp vendor spend)."""
    qs = sorted(pnl.period_end.unique())[-CFG["gl_quarters"]:]
    n_vendor = 1200
    vend = pd.DataFrame(dict(vendor_id=[f"V{i:04d}" for i in range(n_vendor)],
                             vendor_name=[f"Vendor {i:04d}" for i in range(n_vendor)],
                             category=rng.choice(CATS, n_vendor, p=CAT_W)))
    vend["tier"] = np.where(rng.random(n_vendor) < 0.1, "strategic", "tail")
    vw = np.exp(rng.normal(0, 1.4, n_vendor))  # heavy-tailed vendor sizes
    keys = list(CFG["businesses"])
    pools = list(CFG["pools"])
    cc = pd.DataFrame([(f"CC-{k}-{r}", k, r, "front") for k in keys for r in REGIONS] +
                      [(f"CC-{p}-{r}", p, r, "support") for p in pools for r in REGIONS],
                      columns=["cost_center", "owner", "region", "type"])
    cc["synthetic"] = True
    rows_target = CFG["gl"]["target_rows"]
    per_month = rows_target // (len(qs) * 3)
    parts = []
    cc_w = np.array([CFG["businesses"][o]["intensity"] * 1.0 if t == "front" else CFG["pools"][o] * 6
                     for o, t in zip(cc.owner, cc.type)]) * np.array([CFG["regions"][r] for r in cc.region])
    for pe in qs:
        p = pub.loc[pe]
        d = pnl[pnl.period_end == pe].set_index("business")
        pool_cost = {k: p.opex * s for k, s in CFG["pools"].items()}
        # cost to book per owner (direct + pool), then split to months and regions
        owner_cost = {k: d.loc[k, "direct_comp"] + d.loc[k, "direct_noncomp"] for k in keys}
        owner_cost.update(pool_cost)
        comp_share = {k: (d.loc[k, "direct_comp"] / (d.loc[k, "direct_comp"] + d.loc[k, "direct_noncomp"])
                          if k in keys else 0.60) for k in owner_cost}
        qend = pd.Timestamp(pe)
        months = [qend - pd.offsets.MonthEnd(2), qend - pd.offsets.MonthEnd(1), qend]
        mw = rng.dirichlet(np.array([33.0, 33.0, 34.0]) * 40)
        for mi, m_end in enumerate(months):
            n = per_month
            owner_ids = rng.choice(len(cc), n, p=cc_w / cc_w.sum())
            cc_row = cc.iloc[owner_ids]
            is_comp = rng.random(n) < 0.06  # payroll/bonus accrual postings
            raw = np.exp(rng.normal(0, 1.1, n))
            vi = rng.choice(n_vendor, n, p=vw / vw.sum())
            cat = np.where(is_comp, "Compensation & benefits", vend.category.values[vi])
            df = pd.DataFrame(dict(
                posting_date=m_end - pd.to_timedelta(rng.integers(0, 28, n), unit="D"),
                cost_center=cc_row.cost_center.values, owner=cc_row.owner.values, region=cc_row.region.values,
                category=cat, vendor_id=np.where(is_comp, "", vend.vendor_id.values[vi]), raw=raw,
                is_comp=is_comp, period_end=pe))
            # scale so each owner's comp / non-comp monthly total hits the public-calibrated target
            amt = np.zeros(n)
            for o in df.owner.unique():
                for comp_flag in (True, False):
                    msk = ((df.owner == o) & (df.is_comp == comp_flag)).values
                    if not msk.any():
                        continue
                    share = comp_share[o] if comp_flag else 1 - comp_share[o]
                    amt[msk] = _norm(raw[msk], owner_cost[o] * share * mw[mi] * 1.0)
            df["amount_musd"] = amt
            df.drop(columns=["raw"], inplace=True)
            parts.append(df)
    gl = pd.concat(parts, ignore_index=True)
    gl["txn_id"] = np.arange(1, len(gl) + 1)
    gl["synthetic"] = True
    return gl, vend.merge(pd.DataFrame({"vendor_id": vend.vendor_id, "weight": vw / vw.sum()}), on="vendor_id")


def travel_expenses(rng: np.random.Generator, gl_vendors: pd.DataFrame) -> pd.DataFrame:
    T = CFG["te"]
    n = T["n_claims"]
    emp = rng.integers(0, 7000, n)
    date = pd.Timestamp("2025-07-01") + pd.to_timedelta(rng.integers(0, 365, n), unit="D")
    wk = date.weekday >= 5                                           # business travel is mostly on weekdays:
    shift = np.where(rng.random(n) < 0.88, 1, 0) * np.where(date.weekday == 5, 2, 1)   # move 88% of weekend claims
    date = date + pd.to_timedelta(np.where(wk, shift, 0), unit="D")
    cat = rng.choice(["Airfare", "Hotel", "Meals", "Ground transport", "Client entertainment"], n,
                     p=[0.28, 0.27, 0.22, 0.13, 0.10])
    limit = pd.Series(cat).map({"Airfare": 3500, "Hotel": 450, "Meals": 120, "Ground transport": 150,
                                "Client entertainment": 350}).values
    amt = np.minimum(limit * rng.beta(2, 3.5, n) * 1.15, limit * 0.98)
    df = pd.DataFrame(dict(claim_id=np.arange(1, n + 1), employee_id=emp, claim_date=date, category=cat,
                           amount_usd=amt.round(2), limit_usd=limit, has_receipt=True, violation_type=""))
    k = int(n * T["violation_rate"])
    idx = rng.choice(n, k, replace=False)
    types = rng.choice(["over_limit", "duplicate", "split_transaction", "weekend_holiday", "missing_receipt"], k)
    for i, t in zip(idx, types):
        df.at[i, "violation_type"] = t
        if t == "over_limit":
            df.at[i, "amount_usd"] = round(limit[i] * rng.uniform(1.15, 1.9), 2)
        elif t == "missing_receipt":
            df.at[i, "has_receipt"] = False
            df.at[i, "amount_usd"] = round(max(amt[i], limit[i] * 0.6), 2)
        elif t == "weekend_holiday":
            d = df.at[i, "claim_date"]
            df.at[i, "claim_date"] = d + pd.Timedelta(days=(5 - d.weekday()) % 7 or 6)
    split_rows = []
    for i, t in zip(idx, types):
        if t == "split_transaction":                                 # two sub-limit claims, same day, sum above the limit
            df.at[i, "amount_usd"] = round(limit[i] * 0.62, 2)
            twin = df.loc[i].copy()
            twin["claim_id"] = n + 100_000 + len(split_rows)
            split_rows.append(twin)
    if split_rows:
        df = pd.concat([df, pd.DataFrame(split_rows)], ignore_index=True)
    dup_idx = [i for i, t in zip(idx, types) if t == "duplicate"]
    dups = df.loc[dup_idx].copy()
    dups["claim_id"] = np.arange(n + 1, n + 1 + len(dups))
    dups["violation_type"] = "duplicate"
    df = pd.concat([df, dups], ignore_index=True)
    df["is_violation"] = df.violation_type != ""
    df["synthetic"] = True
    return df


def savings_initiatives(rng: np.random.Generator) -> pd.DataFrame:
    n = CFG["savings"]["n_initiatives"]
    cat = rng.choice(["Technology rationalisation", "Vendor consolidation", "Real estate", "Process automation",
                      "Headcount / location mix", "Travel & expense policy", "Market data"], n)
    target = np.round(rng.lognormal(np.log(6), 0.8, n), 1)
    df = pd.DataFrame(dict(
        initiative_id=[f"INI{i:03d}" for i in range(1, n + 1)], category=cat,
        target_savings_musd=target, implementation_cost_musd=np.round(target * rng.uniform(0.15, 0.9, n), 1),
        headcount_impact=np.where(np.isin(cat, ["Headcount / location mix", "Process automation"]),
                                  rng.integers(5, 120, n), 0),
        owner=rng.choice(["COO", "CTO", "CFO", "Head of AM", "Head of PWM", "CRO"], n),
        confidence=np.round(rng.uniform(0.4, 0.95, n), 2),
        realised_to_date_musd=0.0))
    df["depends_on"] = ""
    for i in rng.choice(n, 8, replace=False):
        if i > 0:
            df.at[i, "depends_on"] = df.initiative_id[int(rng.integers(0, i))]
    df["realised_to_date_musd"] = (df.target_savings_musd * df.confidence * rng.uniform(0.2, 0.8, n)).round(2)
    df["synthetic"] = True
    return df


def build() -> dict:
    rng = np.random.default_rng(CFG["seed"])
    pub = public_quarterly()
    pnl = business_pnl(pub, rng)
    tables = {
        "fact_business_pnl": pnl.assign(synthetic=True),
        "fact_cost_pools": pool_costs(pub).assign(synthetic=True),
        "fact_drivers": drivers(pnl, rng).assign(synthetic=True),
        "dim_support_usage": support_usage().assign(synthetic=True),
        "fact_headcount": headcount(pnl, rng).assign(synthetic=True),
    }
    dim_adv, fa = advisors(pnl, rng)
    gl, vendors = general_ledger(pnl, pub, rng)
    tables.update(dim_advisor=dim_adv, fact_advisor_monthly=fa, dim_vendor=vendors.assign(synthetic=True),
                  fact_gl=gl, fact_te=travel_expenses(rng, vendors), fact_savings=savings_initiatives(rng),
                  dim_business=pd.DataFrame([dict(business=k, name=v["name"], synthetic=True)
                                             for k, v in CFG["businesses"].items()]),
                  dim_region=pd.DataFrame([dict(region=r, share=s, synthetic=True) for r, s in CFG["regions"].items()]),
                  dim_function=pd.DataFrame([dict(pool=k, name=v, synthetic=True) for k, v in POOL_NAMES.items()]))
    con = duckdb.connect(str(DB))
    for name, df in tables.items():
        con.register("x", df)
        con.execute(f"create or replace table {name} as select * from x")
        con.unregister("x")
    con.close()
    return {k: len(v) for k, v in tables.items()}


if __name__ == "__main__":
    print(build())
