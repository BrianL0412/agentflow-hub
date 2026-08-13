import subprocess
from pathlib import Path

from agentflow.worktree import create_worktree, init_git_repo, remove_worktree


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def test_create_and_remove_worktree(tmp_path: Path):
    repo = init_git_repo(tmp_path / "repo")
    wt = create_worktree(repo, "01")
    assert (wt / "README.md").exists()          # branched off main's initial commit
    assert "agentflow/01" in git(repo, "branch", "--list")
    remove_worktree(repo, wt)
    assert not wt.exists()


def test_two_worktrees_coexist(tmp_path: Path):
    repo = init_git_repo(tmp_path / "repo")
    a = create_worktree(repo, "02")
    b = create_worktree(repo, "03")
    (a / "a.txt").write_text("a")
    assert not (b / "a.txt").exists()           # isolation


def test_reinit_is_idempotent(tmp_path: Path):
    # Resume re-inits an existing repo; the initial commit must not fail when
    # the working tree is already clean (matches MergeGuard's commit guard).
    repo = init_git_repo(tmp_path / "repo")
    first_head = git(repo, "rev-parse", "HEAD")
    repo2 = init_git_repo(tmp_path / "repo")           # re-init, no crash
    assert git(repo2, "rev-parse", "HEAD") == first_head

