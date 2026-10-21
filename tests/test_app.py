import pytest
from streamlit.testing.v1 import AppTest

from assetlens.warehouse.build import DB

pytestmark = pytest.mark.skipif(not DB.exists(), reason="warehouse not built")


@pytest.mark.slow
def test_every_page_renders_without_exception():
    at = AppTest.from_file("../app/streamlit_app.py", default_timeout=120).run()
    assert not at.exception
    pages = at.sidebar.radio[0].options
    for p in pages:
        at.sidebar.radio[0].set_value(p).run()
        assert not at.exception, (p, [e.value for e in at.exception])
