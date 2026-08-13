"""agentflow CLI — run / status / report."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from agentflow.graph import apply_touch_conflicts, build_deps
from agentflow.ledger import Ledger
from agentflow.meter import write_comparison
from agentflow.runner import FakeRunner
from agentflow.scheduler import Scheduler
from agentflow.tickets import load_tickets


def _approve_prompt(ticket) -> bool:
    return input(f"Merge ticket {ticket.num} — {ticket.title}? [y/N] ").strip().lower() == "y"


def _cmd_run(args) -> int:
    tickets = load_tickets(Path(args.issues_dir))
    repo = Path(args.repo)
    runs_dir = Path(args.runs_dir) if args.runs_dir else repo / ".agentflow" / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(args.issues_dir, runs_dir / "issues", dirs_exist_ok=True)  # for `report` reload
    if args.agent_cmd:
        from agentflow.subprocess_runner import SubprocessRunner  # Task 12

        runner = SubprocessRunner(args.agent_cmd)
    else:
        print("WARNING: no --agent-cmd given; running in demo mode (FakeRunner, no real agent).")
        runner = FakeRunner()
    scheduler = Scheduler(
        tickets, repo, runs_dir, runner, args.test_cmd,
        approve=(lambda t: True) if args.yes else _approve_prompt,
    )
    rc = scheduler.run()
    write_comparison(tickets, scheduler.deps, scheduler.ledger, runs_dir)
    print(f"token report: {runs_dir / 'token-report.md'}")
    return rc


def _cmd_status(args) -> int:
    ledger = Ledger(Path(args.runs_dir) / "ledger.jsonl")
    states = ledger.states()
    if not states:
        print("no runs recorded")
        return 0
    for num, status in sorted(states.items()):
        print(f"{num}\t{status}")
    return 0


def _cmd_report(args) -> int:
    runs_dir = Path(args.runs_dir)
    issues_dir = runs_dir / "issues"
    tickets = load_tickets(issues_dir)
    deps = apply_touch_conflicts(tickets, build_deps(tickets))
    path = write_comparison(tickets, deps, Ledger(runs_dir / "ledger.jsonl"), runs_dir)
    print(path.read_text(encoding="utf-8"))
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="agentflow")
    sub = p.add_subparsers(dest="cmd", required=True)
    pr = sub.add_parser("run")
    pr.add_argument("--issues-dir", required=True)
    pr.add_argument("--repo", required=True)
    pr.add_argument("--runs-dir")
    pr.add_argument("--test-cmd", default="true")
    pr.add_argument("--agent-cmd")
    pr.add_argument("--yes", action="store_true")
    ps = sub.add_parser("status")
    ps.add_argument("--runs-dir", required=True)
    pp = sub.add_parser("report")
    pp.add_argument("--runs-dir", required=True)
    args = p.parse_args(argv)
    return {"run": _cmd_run, "status": _cmd_status, "report": _cmd_report}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
