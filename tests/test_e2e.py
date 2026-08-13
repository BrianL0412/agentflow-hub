from pathlib import Path

from agentflow.ledger import STATUS_DONE, Ledger
from agentflow.meter import build_comparison
from agentflow.runner import FakeRunner
from agentflow.scheduler import Scheduler
from agentflow.tickets import Ticket
from agentflow.worktree import init_git_repo


def mk(num: str, blocked: list[str] | None = None, touches: list[str] | None = None) -> Ticket:
    return Ticket(num, f"slug-{num}", f"T{num}", blocked or [], touches or [], "brief", Path(f"{num}.md"))


def test_spec_golden_path_five_tickets(tmp_path: Path):
    """The spec's E2E: 1 -> {2,3} -> {4,5} (4,5 depend on 3), full system, FakeRunner."""
    tickets = [
        mk("01"),
        mk("02", ["01"], ["src/a"]),
        mk("03", ["01"], ["src/b"]),
        mk("04", ["03"]),
        mk("05", ["03"]),
    ]
    repo = init_git_repo(tmp_path / "repo")
    runs = tmp_path / "runs"
    runs.mkdir()
    script = {n: {"exit": 0, "report": None, "files": {f"src/mod{n}.py": f"# ticket {n}\n"}} for n in
              ["01", "02", "03", "04", "05"]}
    runner = FakeRunner(script)
    s = Scheduler(tickets, repo, runs, runner, "true", approve=lambda t: True)
    assert s.run() == 0
    # every ticket's file landed on main, in dependency order
    for n in ["01", "02", "03", "04", "05"]:
        assert (repo / f"src/mod{n}.py").exists()
    assert set(Ledger(runs / "ledger.jsonl").states().values()) == {STATUS_DONE}
    report = build_comparison(tickets, s.deps, s.ledger, runs)
    assert "Savings" in report
