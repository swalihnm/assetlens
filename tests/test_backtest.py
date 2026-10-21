import pytest

from assetlens.warehouse.build import DB

pytestmark = pytest.mark.skipif(not DB.exists(), reason="warehouse not built")


def test_backtest_regression_and_no_leakage():
    from assetlens.forecast import backtest as B
    r = B.run(log_mlflow=False)
    t = r["total"].set_index("model").mape
    # regression guard: errors must not silently degrade (baseline run: 2.5% conditional, 3.5% unconditional)
    assert t["model_realised_mkt"] < 0.035 and t["model_assumed_mkt"] < 0.05
    assert t["model_realised_mkt"] < r["best_naive_mape"]            # conditional model beats best baseline
    # no look-ahead: forecasts must not change when future rows are removed from the data
    w, mk = B.data()
    o = w.index[-6]
    full = B.model_fees(w, mk, o, 2, True)
    trunc = B.model_fees(w[w.index <= o + __import__("pandas").offsets.QuarterEnd(2)], mk, o, 2, True)
    assert full == pytest.approx(trunc)
