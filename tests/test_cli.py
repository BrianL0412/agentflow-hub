from pathlib import Path

from agentflow.cli import main
from agentflow.tickets import load_tickets  # noqa: F401  (fixture sanity)
from agentflow.worktree import init_git_repo

TICKET = """# {num} — Task {num}

**What to build:** thing {num}.

**Blocked by:** {blocked}

**Status:** ready-for-agent

- [ ] done
"""


def make_issues(d: Path) -> None:
    d.mkdir()
    (d / "01-first.md").write_text(TICKET.format(num="01", blocked="None — can start immediately"))
    (d / "02-second.md").write_text(TICKET.format(num="02", blocked="01 — Task 01"))


def test_run_demo_mode_end_to_end(tmp_path: Path, capsys):
    issues = tmp_path / "issues"
    make_issues(issues)
    repo = init_git_repo(tmp_path / "repo")
    runs = tmp_path / "runs"
    rc = main(["run", "--issues-dir", str(issues), "--repo", str(repo),
               "--runs-dir", str(runs), "--yes"])
    assert rc == 0
    assert "demo" in capsys.readouterr().out.lower()  # FakeRunner warning shown


def test_status_and_report(tmp_path: Path, capsys):
    issues = tmp_path / "issues"
    make_issues(issues)
    repo = init_git_repo(tmp_path / "repo")
    runs = tmp_path / "runs"
    main(["run", "--issues-dir", str(issues), "--repo", str(repo),
          "--runs-dir", str(runs), "--yes"])
    capsys.readouterr()
    assert main(["status", "--runs-dir", str(runs)]) == 0
    out = capsys.readouterr().out
    assert "01" in out and "done" in out
    assert main(["report", "--runs-dir", str(runs)]) == 0
    assert "Savings" in capsys.readouterr().out
