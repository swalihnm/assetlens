from dataclasses import replace

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from assetlens.pricing import mandate as P

M = P.Mandate()


@pytest.mark.parametrize("basis", ["marginal", "fully_allocated"])
@pytest.mark.parametrize("horizon", ["year1", "lifetime"])
def test_break_even_fee_makes_profit_zero(basis, horizon):
    be = P.break_even_fee(M, basis, horizon)
    lam = be / P.effective_bps(P.cash_flows(M)["avg_aum"][0], M.tiers)
    val = P.cash_flows(M, lam)[basis][0] if horizon == "year1" else P.lifetime_value(M, basis, lam)
    assert abs(val) < 1e-6


def test_fully_allocated_break_even_exceeds_marginal():
    assert P.break_even_fee(M, "fully_allocated") > P.break_even_fee(M, "marginal") > 0


def test_min_viable_aum_zero_profit_and_monotonic():
    a = P.min_viable_aum(M, "marginal")
    assert abs(P.cash_flows(replace(M, initial_aum=a))["marginal"][0]) < 1e-5
    assert P.min_viable_aum(M, "fully_allocated") > a


def test_tiered_fee_is_continuous_and_matches_manual():
    assert P.tiered_fee(250, M.tiers) == pytest.approx(250 * 40 / 1e4)
    assert P.tiered_fee(1000, M.tiers) == pytest.approx(250 * 40 / 1e4 + 250 * 32 / 1e4 + 500 * 24 / 1e4)


@settings(max_examples=40, deadline=None)
@given(st.floats(0.01, 0.5))
def test_ltv_decreases_with_hazard(h):
    assert P.lifetime_value(replace(M, hazard_annual=h)) >= P.lifetime_value(replace(M, hazard_annual=min(0.9, h + 0.1)))


def test_weibull_survival_matches_hazard():
    assert 1 - P.survival(replace(M, hazard_annual=0.2, weibull_shape=1.5), np.array([1.0]))[0] == pytest.approx(0.2)


def test_monte_carlo_collapses_to_deterministic_when_no_vol():
    mc = P.monte_carlo_ltv(M, n=50, mkt_mu=M.growth_annual, mkt_sigma=0.0, flow_sigma=0.0)
    # deterministic path uses (1+g)^t; MC with sigma 0 compounds identically
    assert mc["mean"] == pytest.approx(P.lifetime_value(M, "fully_allocated"), rel=1e-9)


def test_recommendation_rule_never_below_marginal():
    cheap = replace(M, tiers=[(float("inf"), 1.0)])
    assert P.recommend(cheap)["verdict"].startswith("REJECT")
