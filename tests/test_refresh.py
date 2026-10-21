import json

from assetlens import refresh


def test_nothing_new_when_latest_10q_already_processed(monkeypatch, tmp_path):
    monkeypatch.setattr(refresh, "STATE", tmp_path / "s.json")
    monkeypatch.setattr(refresh, "latest_gs_10q", lambda: ("2026-06-30", "0000886982-26-000297"))
    assert refresh.run()["status"] == "nothing new"


def test_new_10q_triggers_all_steps_and_records_state(monkeypatch, tmp_path):
    calls = []

    class R:
        returncode, stdout, stderr = 0, "9 passed\n", ""

    monkeypatch.setattr(refresh, "STATE", tmp_path / "s.json")
    monkeypatch.setattr(refresh, "latest_gs_10q", lambda: ("2026-09-30", "0000886982-26-000999"))
    monkeypatch.setattr(refresh.subprocess, "run", lambda cmd, **k: calls.append(cmd) or R())
    out = refresh.run(remove_task="T")
    assert out["status"] == "refreshed" and out["period"] == "2026-09-30"
    assert len(calls) == len(refresh.STEPS) + 2                      # steps + pytest + schtasks delete
    assert calls[-1][:2] == ["schtasks", "/delete"]
    assert json.loads((tmp_path / "s.json").read_text())["period"] == "2026-09-30"


def test_failed_step_stops_and_keeps_old_period(monkeypatch, tmp_path):
    class R:
        returncode, stdout, stderr = 1, "", "boom"

    monkeypatch.setattr(refresh, "STATE", tmp_path / "s.json")
    monkeypatch.setattr(refresh, "latest_gs_10q", lambda: ("2026-09-30", "x"))
    monkeypatch.setattr(refresh.subprocess, "run", lambda cmd, **k: R())
    out = refresh.run()
    assert out["status"] == "failed" and json.loads((tmp_path / "s.json").read_text())["period"] == "2026-06-30"
