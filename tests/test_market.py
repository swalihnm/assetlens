import pytest

from assetlens.warehouse.build import DB

pytestmark = pytest.mark.skipif(not DB.exists(), reason="warehouse not built")


def test_market_betas_sane():
    from assetlens.market.sensitivity import run
    r = run()
    b = r["betas"].set_index("ticker")
    assert b.loc["TROW", "beta_equity"] > b.loc["BLK", "beta_equity"] > 0.3
    assert (b.r2.between(0, 1)).all() and r["sanity"]["bond_proxy_corr_with_ice"] > 0.9
