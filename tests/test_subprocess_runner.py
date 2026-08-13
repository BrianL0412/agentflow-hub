from pathlib import Path

from agentflow.runner import Dispatch
from agentflow.subprocess_runner import SubprocessRunner
from agentflow.tickets import Ticket


def mk_dispatch(tmp_path: Path) -> Dispatch:
    t = Ticket("01", "slug-01", "T01", [], [], "brief", Path("01.md"))
    wt = tmp_path / "wt"
    wt.mkdir()
    for name in ("brief", "context", "report"):
        (tmp_path / f"01-{name}.md").write_text("", encoding="utf-8")
    return Dispatch(t, wt, tmp_path / "01-brief.md", tmp_path / "01-context.md", tmp_path / "01-report.md")


def test_success_exit_zero(tmp_path: Path):
    d = mk_dispatch(tmp_path)
    r = SubprocessRunner("echo hello > {worktree}/out.txt").run(d)
    assert r.ok and (d.worktree / "out.txt").read_text() == "hello\n"


def test_failure_exit_code_passed_through(tmp_path: Path):
    r = SubprocessRunner("exit 3").run(mk_dispatch(tmp_path))
    assert not r.ok and r.exit_code == 3
