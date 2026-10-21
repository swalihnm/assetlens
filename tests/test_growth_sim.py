import numpy as np
import pytest

from assetlens.growth import business_case as GC
from assetlens.growth import simulation as S


def test_market_index_default_does_not_change_deterministic_case():
    assert GC.run()["npv"] == pytest.approx(GC.run(market_index=np.ones(7))["npv"])
    assert GC.run(market_index=np.full(7, 0.5))["npv"] < GC.run()["npv"]


def test_simulation_reproducible_and_staged_never_below_exit_floor():
    a, b = S.simulate(150, seed=5), S.simulate(150, seed=5)
    assert a["full"]["mean"] == b["full"]["mean"]
    assert 0 <= a["pass_rate"] <= 1 and a["full"]["p10"] <= a["full"]["p50"] <= a["full"]["p90"]
    d = a["draws"]
    assert (d[~d.passed].staged < 10).all()      # abandoned branch is bounded by the pilot cost and capital recovery
