"""Four-layer merge defense, layers 1-2: topo-order merge + rebase-and-retest."""

from __future__ import annotations

import subprocess
from pathlib import Path

from agentflow.tickets import Ticket
from agentflow.worktree import branch_name, git, remove_worktree


class MergeError(RuntimeError):
    pass


class MergeGuard:
    def __init__(self, repo: Path, test_cmd: str):
        self.repo = repo
        self.test_cmd = test_cmd

    def _run_tests(self, cwd: Path) -> None:
        r = subprocess.run(self.test_cmd, shell=True, cwd=cwd, capture_output=True, text=True)
        if r.returncode != 0:
            raise MergeError(f"tests failed after rebase:\n{r.stdout}\n{r.stderr}")

    def merge(self, ticket: Ticket, worktree: Path) -> None:
        branch = branch_name(ticket.num)
        try:
            if git(worktree, "status", "--porcelain"):
                git(worktree, "add", "-A")
                git(
                    worktree, "-c", "user.email=hub@local", "-c", "user.name=hub",
                    "commit", "-m", f"ticket {ticket.num}: {ticket.title}",
                )
            try:
                git(worktree, "rebase", "main")
            except subprocess.CalledProcessError as e:
                git(worktree, "rebase", "--abort")
                raise MergeError(f"rebase of {branch} onto main failed: {e.stderr}") from e
            self._run_tests(worktree)   # test the REAL combination, not the stale one
            git(self.repo, "merge", "--ff-only", branch)
        finally:
            if worktree.exists():
                remove_worktree(self.repo, worktree)
