import pytest
from fastapi.testclient import TestClient

from assetlens.api.app import app
from assetlens.warehouse.build import DB

pytestmark = pytest.mark.skipif(not DB.exists(), reason="warehouse not built")
c = TestClient(app)


def test_endpoints():
    assert len(c.get("/benchmarks").json()) >= 7
    assert len(c.get("/forecast?scenario=stress").json()) == 8
    assert c.get("/forecast?scenario=x").status_code == 404
    r = c.post("/mandate/price", json={}).json()
    assert r["recommendation"]["marginal_be_bps"] < r["recommendation"]["fully_allocated_be_bps"]
    assert c.get("/allocation?method=abc").status_code == 200
    assert c.get("/growth-case?location=KAFD").json()["location"] == "KAFD"
    assert c.post("/mandate/price", json={"hazard_annual": 2}).status_code == 422
