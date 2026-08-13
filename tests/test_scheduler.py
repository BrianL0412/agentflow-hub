import threading
from pathlib import Path

from agentflow.ledger import (
    STATUS_BLOCKED, STATUS_DONE, STATUS_FAILED, Ledger,
)
from agentflow.runner import FakeRunner
from agentflow.scheduler import Scheduler
from agentflow.tickets import Ticket
from agentflow.worktree import init_git_repo


def mk(num: str, blocked: list[str] | None = None, touches: list[str] | None = None) -> Ticket:
    return Ticket(num, f"slug-{num}", f"T{num}", blocked or [], touches or [], "brief", Path(f"{num}.md"))


FIVE = [
    mk("01"),
    mk("02", ["01"], ["src/a"]),
    mk("03", ["01"], ["src/b"]),
    mk("04", ["03"]),
    mk("05", ["03"]),
]


def build(tmp_path: Path, runner, approve=lambda t: True, tickets=FIVE):
    repo = init_git_repo(tmp_path / "repo")
    runs = tmp_path / "runs"
    runs.mkdir(exist_ok=True)                         # resume reuses the runs dir
    s = Scheduler(tickets, repo, runs, runner, "true", approve)
    return s, Ledger(runs / "ledger.jsonl")


def test_full_dag_executes_in_topo_waves(tmp_path: Path):
    runner = FakeRunner()
    s, lg = build(tmp_path, runner)
    assert s.run() == 0
    assert set(lg.states().values()) == {STATUS_DONE}
    assert runner.calls[0] == "01"                    # wave 1
    assert set(runner.calls[1:3]) == {"02", "03"}     # wave 2 parallel
    assert set(runner.calls[3:]) == {"04", "05"}      # wave 3


def test_failure_blocks_descendants_and_aborts(tmp_path: Path):
    runner = FakeRunner({"03": {"exit": 1, "report": None, "files": {}}})
    s, lg = build(tmp_path, runner)
    assert s.run() == 1
    st = lg.states()
    assert st["03"] == STATUS_FAILED
    assert st["04"] == STATUS_BLOCKED and st["05"] == STATUS_BLOCKED
    assert "04" not in runner.calls                   # never dispatched


def test_resume_skips_done(tmp_path: Path):
    s1, lg = build(tmp_path, FakeRunner({"03": {"exit": 1, "report": None, "files": {}}}))
    s1.run()
    runner2 = FakeRunner()                            # fixed now
    s2, lg2 = build(tmp_path, runner2)
    assert s2.run() == 0
    assert "01" not in runner2.calls                  # done tickets not re-run
    assert "02" not in runner2.calls


def test_approval_rejection_blocks_merge(tmp_path: Path):
    s, lg = build(tmp_path, FakeRunner(), approve=lambda t: t.num != "02")
    assert s.run() == 1
    st = lg.states()
    assert st["01"] == STATUS_DONE
    assert st["02"] == STATUS_FAILED                  # rejected at gate


def test_meter_events_written(tmp_path: Path):
    s, lg = build(tmp_path, FakeRunner())
    s.run()
    kinds = {(m["ticket"], m["kind"]) for m in lg.meters()}
    assert ("01", "dispatch") in kinds and ("01", "report") in kinds


def test_ledger_single_writer_all_appends_on_main_thread(tmp_path: Path):
    # Global Constraints: "Ledger ... single writer (the scheduler main thread)."
    # A ThreadPoolExecutor worker must not append. We pin the main thread's ident
    # and fail if any append lands on a different thread.
    s, lg = build(tmp_path, FakeRunner())
    main_ident = threading.current_thread().ident
    writer_idents: list[int] = []
    orig_append = s.ledger.append

    def spy(ticket: str, type: str, payload: dict) -> None:
        writer_idents.append(threading.current_thread().ident)
        orig_append(ticket, type, payload)

    s.ledger.append = spy
    s.run()
    assert writer_idents, "no ledger writes captured"
    off_main = [tid for tid in writer_idents if tid != main_ident]
    assert not off_main, f"ledger written off the main thread: {off_main}"
