import pytest

from assetlens.excel.build_model import OUT


@pytest.mark.slow
@pytest.mark.skipif(not OUT.exists(), reason="workbook not built")
def test_excel_python_parity_and_no_errors():
    from assetlens.excel import parity
    r = parity.run()
    assert not r["failures"], r["failures"]
    assert all(v["max_rel_error"] < 1e-4 for v in r["scenarios"].values())
