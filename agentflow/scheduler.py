"""Wave-based DAG scheduler. Parallel within a wave, serialized merges in topo order."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable

from agentflow.context import assemble_context
from agentflow.graph import build_deps_with_conflicts, descendants, topo_order
from agentflow.ledger import (
    STATUS_BLOCKED, STATUS_DONE, STATUS_FAILED, STATUS_MERGING,
    STATUS_READY, STATUS_REVIEW, STATUS_RUNNING, Ledger,
)
from agentflow.merge import MergeError, MergeGuard
from agentflow.report import ReportError, parse_report, report_path_for
from agentflow.runner import AgentRunner, Dispatch, brief_path_for
from agentflow.tickets import Ticket
from agentflow.worktree import create_worktree, remove_worktree


class Scheduler:
    def __init__(
        self,
        tickets: list[Ticket],
        repo: Path,
        runs_dir: Path,
        runner: AgentRunner,
        test_cmd: str,
        approve: Callable[[Ticket], bool],
        ledger: Ledger | None = None,
    ):
        self.tickets = tickets
        self.by_num = {t.num: t for t in tickets}
        self.repo = repo
        self.runs_dir = runs_dir
        runs_dir.mkdir(parents=True, exist_ok=True)
        self.runner = runner
        self.guard = MergeGuard(repo, test_cmd)
        self.approve = approve
        self.ledger = ledger or Ledger(runs_dir / "ledger.jsonl")
        self.deps = build_deps_with_conflicts(tickets)
        self.order = topo_order(self.deps)
        self.aborted = False

    def _set_status(self, num: str, status: str) -> None:
        self.ledger.append(num, "status", {"status": status})

    def _fail(self, num: str) -> bool:
        self._set_status(num, STATUS_FAILED)
        return False

    def _prepare(self, t: Ticket) -> Dispatch:
        """Main thread: worktree + brief + context + dispatch metering (git ops stay single-threaded)."""
        num = t.num
        self._set_status(num, STATUS_RUNNING)
        wt = create_worktree(self.repo, num)
        brief = brief_path_for(self.runs_dir, num)
        brief.write_text(t.brief, encoding="utf-8")
        ctx = assemble_context(t, self.deps, self.by_num, self.runs_dir)
        self.ledger.append(num, "meter", {"kind": "dispatch", "chars": len(t.brief) + len(ctx.read_text(encoding="utf-8"))})
        return Dispatch(t, wt, brief, ctx, report_path_for(self.runs_dir, num))

    def _run_agent(self, dispatch: Dispatch) -> tuple[bool, int]:
        """Worker thread: agent run + report validation only. No git, no merge, no ledger
        writes — the ledger is single-writer (main thread). Returns (ok, report_chars)."""
        result = self.runner.run(dispatch)
        if not result.ok:
            return (False, 0)
        try:
            rep = parse_report(dispatch.report_path)
        except ReportError:
            return (False, 0)
        return (True, len(rep.raw))

    def _settle(self, t: Ticket, dispatch: Dispatch) -> bool:
        """Main thread, topo order: approval gate -> merge -> done."""
        num = t.num
        self._set_status(num, STATUS_REVIEW)
        if not self.approve(t):
            return self._fail(num)
        self._set_status(num, STATUS_MERGING)
        try:
            self.guard.merge(t, dispatch.worktree)
        except MergeError:
            return self._fail(num)
        self._set_status(num, STATUS_DONE)
        return True

    def _block_descendants(self, num: str) -> None:
        for n in descendants(self.deps, num):
            self._set_status(n, STATUS_BLOCKED)

    def run(self) -> int:
        states = self.ledger.states()
        done = {n for n, s in states.items() if s == STATUS_DONE}
        failed_any = False
        while not self.aborted:
            ready = [
                n for n in self.order
                if n not in done
                and states.get(n) not in (STATUS_DONE, STATUS_FAILED, STATUS_BLOCKED)
                and self.deps[n] <= done
            ]
            if not ready:
                break
            for n in ready:
                self._set_status(n, STATUS_READY)
            dispatches = {n: self._prepare(self.by_num[n]) for n in ready}   # main thread
            with ThreadPoolExecutor(max_workers=len(ready)) as pool:
                results = dict(zip(ready, pool.map(lambda n: self._run_agent(dispatches[n]), ready)))
            for n in ready:  # settle serially in topological order (self.order is sorted)
                ok, report_chars = results[n]
                if ok:
                    self.ledger.append(n, "meter", {"kind": "report", "chars": report_chars})  # main thread: single-writer
                if ok and self._settle(self.by_num[n], dispatches[n]):
                    done.add(n)
                else:
                    if not ok:
                        self._set_status(n, STATUS_FAILED)          # agent/report failure: _settle never ran
                    failed_any = True
                    self.aborted = True
                    if dispatches[n].worktree.exists():
                        remove_worktree(self.repo, dispatches[n].worktree)
                    self._block_descendants(n)
            states = self.ledger.states()
        remaining = [
            n for n in self.order
            if states.get(n) not in (STATUS_DONE, STATUS_FAILED, STATUS_BLOCKED)
        ]
        for n in remaining:  # unreachable after abort (e.g. blocked transitively later)
            self._set_status(n, STATUS_BLOCKED)
        return 1 if failed_any or remaining else 0
