from pathlib import Path

import pytest

from agentflow.ledger import Ledger
from agentflow.meter import build_comparison, estimate_tokens, write_comparison
from agentflow.report import valid_report_text, report_path_for
from agentflow.tickets import Ticket


def mk(num: str, blocked: list[str] | None = None) -> Ticket:
    return Ticket(num, f"slug-{num}", f"T{num}", blocked or [], [], "b" * 100, Path(f"{num}.md"))


def test_estimate_tokens():
    assert estimate_tokens(400) == 100
    assert estimate_tokens(0) == 1


def test_comparison_shows_savings(tmp_path: Path):
    tickets = [mk("01"), mk("02", ["01"])]
    deps = {"01": set(), "02": {"01"}}
    report_path_for(tmp_path, "01").write_text(valid_report_text())  # ~200 chars raw
    lg = Ledger(tmp_path / "ledger.jsonl")
    # hub dispatch for 02 = brief(100) + small context; baseline = brief(100) + FULL raw report of 01
    lg.append("02", "meter", {"kind": "dispatch", "chars": 150})
    out = build_comparison(tickets, deps, lg, tmp_path)
    assert "Baseline" in out and "Hub" in out and "Savings" in out
    p = write_comparison(tickets, deps, lg, tmp_path)
    assert p.name == "token-report.md" and p.exists()


def test_baseline_raises_on_missing_ancestor_report(tmp_path: Path):
    """Spec: baseline = brief + ALL ancestors' report full text. Missing report
    (partial/crashed run) must raise, not silently count as zero chars."""
    tickets = [mk("01"), mk("02", ["01"])]
    deps = {"01": set(), "02": {"01"}}
    lg = Ledger(tmp_path / "ledger.jsonl")
    lg.append("02", "meter", {"kind": "dispatch", "chars": 150})
    # NOTE: no report file written for ancestor 01
    with pytest.raises(FileNotFoundError):
        build_comparison(tickets, deps, lg, tmp_path)
