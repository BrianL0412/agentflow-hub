import json
from pathlib import Path

from agentflow.ledger import STATUS_DONE, STATUS_RUNNING, Ledger


def test_append_and_states(tmp_path: Path):
    lg = Ledger(tmp_path / "ledger.jsonl")
    lg.append("01", "status", {"status": STATUS_RUNNING})
    lg.append("01", "status", {"status": STATUS_DONE})
    lg.append("02", "status", {"status": STATUS_RUNNING})
    assert lg.states() == {"01": STATUS_DONE, "02": STATUS_RUNNING}


def test_meter_events_collected(tmp_path: Path):
    lg = Ledger(tmp_path / "ledger.jsonl")
    lg.append("01", "meter", {"kind": "dispatch", "chars": 120})
    lg.append("01", "status", {"status": STATUS_DONE})
    lg.append("01", "meter", {"kind": "report", "chars": 400})
    meters = lg.meters()
    # meters() returns full records (ts/ticket/type + payload); ts is non-deterministic,
    # so assert on the stable fields. Task 10 reads m["ticket"]/m["kind"]/m["chars"].
    assert [m["kind"] for m in meters] == ["dispatch", "report"]
    assert [m["chars"] for m in meters] == [120, 400]
    assert all(m["type"] == "meter" and m["ticket"] == "01" for m in meters)


def test_crash_recovery_reloads_from_disk(tmp_path: Path):
    p = tmp_path / "ledger.jsonl"
    Ledger(p).append("01", "status", {"status": STATUS_DONE})
    # simulate restart: brand new Ledger instance on the same file
    assert Ledger(p).states() == {"01": STATUS_DONE}


def test_every_line_is_valid_json(tmp_path: Path):
    p = tmp_path / "ledger.jsonl"
    lg = Ledger(p)
    lg.append("01", "status", {"status": STATUS_DONE})
    for line in p.read_text().splitlines():
        json.loads(line)  # must not raise
