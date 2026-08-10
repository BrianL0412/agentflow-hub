from pathlib import Path

import pytest

from agentflow.tickets import Ticket, TicketError, load_tickets


def write_ticket(d: Path, name: str, body: str) -> Path:
    p = d / name
    p.write_text(body, encoding="utf-8")
    return p


GOOD = """# 01 — Ledger storage

**What to build:** JSONL event ledger with crash recovery.

**Blocked by:** None — can start immediately

**Touches:** agentflow/ledger.py, tests/test_ledger.py

**Status:** ready-for-agent

- [ ] appends events
- [ ] rebuilds state after crash
"""

DEP = """# 03 — Scheduler core

**What to build:** Wave scheduler.

**Blocked by:** 01 — Ledger storage, 02 — Graph validation

**Status:** ready-for-agent

- [ ] schedules waves
"""


def test_load_single_ticket(tmp_path: Path):
    write_ticket(tmp_path, "01-ledger-storage.md", GOOD)
    (t,) = load_tickets(tmp_path)
    assert t.num == "01"
    assert t.slug == "ledger-storage"
    assert t.title == "Ledger storage"
    assert t.blocked_by == []
    assert t.touches == ["agentflow/ledger.py", "tests/test_ledger.py"]
    assert "crash recovery" in t.brief


def test_blocked_by_parsing(tmp_path: Path):
    write_ticket(tmp_path, "03-scheduler-core.md", DEP)
    (t,) = load_tickets(tmp_path)
    assert t.blocked_by == ["01", "02"]
    assert t.touches == []  # Touches line is optional


def test_tickets_sorted_by_num(tmp_path: Path):
    write_ticket(tmp_path, "03-scheduler-core.md", DEP)
    write_ticket(tmp_path, "01-ledger-storage.md", GOOD)
    assert [t.num for t in load_tickets(tmp_path)] == ["01", "03"]


def test_malformed_missing_blocked_by(tmp_path: Path):
    write_ticket(tmp_path, "01-bad.md", "# 01 — Bad\n\nno fields here\n")
    with pytest.raises(TicketError, match="Blocked by"):
        load_tickets(tmp_path)
