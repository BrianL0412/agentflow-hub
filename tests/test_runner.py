from pathlib import Path

from agentflow.report import parse_report
from agentflow.runner import Dispatch, FakeRunner, RunResult
from agentflow.tickets import Ticket


def mk_dispatch(tmp_path: Path, num: str = "01") -> Dispatch:
    t = Ticket(num, f"slug-{num}", f"T{num}", [], [], "brief", Path(f"{num}.md"))
    wt = tmp_path / "wt"
    wt.mkdir()
    return Dispatch(
        ticket=t,
        worktree=wt,
        brief_path=tmp_path / f"{num}-brief.md",
        context_path=tmp_path / f"{num}-context.md",
        report_path=tmp_path / f"{num}-report.md",
    )


def test_fake_runner_success_writes_files_and_report(tmp_path: Path):
    d = mk_dispatch(tmp_path)
    r = FakeRunner({"01": {"exit": 0, "report": None, "files": {"src/x.py": "x = 1\n"}}}).run(d)
    assert r == RunResult(ok=True, exit_code=0)
    assert (d.worktree / "src/x.py").read_text() == "x = 1\n"
    parse_report(d.report_path)  # default report is valid — must not raise


def test_fake_runner_failure(tmp_path: Path):
    d = mk_dispatch(tmp_path)
    r = FakeRunner({"01": {"exit": 1, "report": None, "files": {}}}).run(d)
    assert r.ok is False and r.exit_code == 1


def test_fake_runner_bad_report_passes_through(tmp_path: Path):
    d = mk_dispatch(tmp_path)
    FakeRunner({"01": {"exit": 0, "report": "garbage\n", "files": {}}}).run(d)
    assert d.report_path.read_text() == "garbage\n"
