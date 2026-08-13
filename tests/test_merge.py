import subprocess
from pathlib import Path

import pytest

from agentflow.merge import MergeError, MergeGuard
from agentflow.tickets import Ticket
from agentflow.worktree import create_worktree, init_git_repo


def mk(num: str) -> Ticket:
    return Ticket(num, f"slug-{num}", f"T{num}", [], [], "brief", Path(f"{num}.md"))


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def test_merge_lands_change_on_main(tmp_path: Path):
    repo = init_git_repo(tmp_path / "repo")
    wt = create_worktree(repo, "01")
    (wt / "feature.py").write_text("x = 1\n")
    MergeGuard(repo, "test -f feature.py").merge(mk("01"), wt)
    assert (repo / "feature.py").read_text() == "x = 1\n"
    assert not wt.exists()  # worktree cleaned up


def test_failing_test_blocks_merge_and_preserves_main(tmp_path: Path):
    repo = init_git_repo(tmp_path / "repo")
    before = git(repo, "rev-parse", "main")
    wt = create_worktree(repo, "01")
    (wt / "bad.py").write_text("x = 1\n")
    with pytest.raises(MergeError):
        MergeGuard(repo, "exit 1").merge(mk("01"), wt)
    assert git(repo, "rev-parse", "main") == before
    assert not (repo / "bad.py").exists()


def test_rebase_over_updated_main(tmp_path: Path):
    repo = init_git_repo(tmp_path / "repo")
    wt1 = create_worktree(repo, "01")
    wt2 = create_worktree(repo, "02")
    (wt1 / "a.py").write_text("a = 1\n")
    (wt2 / "b.py").write_text("b = 1\n")
    guard = MergeGuard(repo, "test -f a.py -o -f b.py")
    guard.merge(mk("01"), wt1)   # main now has a.py
    guard.merge(mk("02"), wt2)   # must rebase 02 over the new main before merging
    assert (repo / "a.py").exists() and (repo / "b.py").exists()
