"""Per-ticket git worktrees — the isolation layer for parallel agents."""

from __future__ import annotations

import subprocess
from pathlib import Path

WORKTREES_DIR = ".agentflow/worktrees"


def git(repo: Path, *args: str) -> str:
    """Run a git command in repo, returning stripped stdout. Raises on non-zero exit."""
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def branch_name(num: str) -> str:
    return f"agentflow/{num}"


def init_git_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-b", "main", str(path)], check=True, capture_output=True)
    (path / "README.md").write_text("# repo\n", encoding="utf-8")
    if git(path, "status", "--porcelain"):          # skip commit on re-init with clean tree
        git(path, "add", "README.md")
        git(path, "-c", "user.email=hub@local", "-c", "user.name=hub", "commit", "-m", "init")
    return path


def create_worktree(repo: Path, num: str) -> Path:
    wt = repo / WORKTREES_DIR / num
    git(repo, "worktree", "add", str(wt), "-b", branch_name(num), "main")
    return wt


def remove_worktree(repo: Path, path: Path) -> None:
    git(repo, "worktree", "remove", "--force", str(path))
