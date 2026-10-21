import numpy as np
import pytest

from assetlens.warehouse.build import DB

pytestmark = pytest.mark.skipif(not DB.exists(), reason="warehouse not built")


@pytest.mark.parametrize("scenario", ["base", "bull", "bear", "stress"])
def test_vectorised_simulation_matches_engine(scenario):
    from assetlens.forecast.engine import CFG, load_base, run_scenario
    from assetlens.forecast.montecarlo import simulate
    b = load_base()
    sc = CFG["scenarios"][scenario]
    eq, bd = np.array([sc["equity_ret_q"]]), np.array([sc["bond_ret_q"]])
    sim = simulate(eq, bd, b, scenario)
    ref = run_scenario(scenario, b)
    assert np.allclose(sim["net_revenues"][0], ref.net_revenues, rtol=1e-9)
    assert np.allclose(sim["pretax"][0], ref.pretax, rtol=1e-9)


def test_bootstrap_shapes_and_quantile_order():
    from assetlens.forecast.montecarlo import block_bootstrap, historical_returns, run
    h = historical_returns()
    e, b = block_bootstrap(h, 500)
    assert e.shape == (500, 8) and b.shape == (500, 8)
    r = run(n=2000)
    f = r["fan"]
    assert (f.p10 <= f.p50).all() and (f.p50 <= f.p90).all()
    assert 0 <= r["prob"]["margin_below_threshold_q8"] <= r["prob"]["margin_below_threshold_any"] <= 1
