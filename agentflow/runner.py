"""The single test seam: AgentRunner. MVP ships FakeRunner; SubprocessRunner in Task 12."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from agentflow.report import valid_report_text
from agentflow.tickets import Ticket


def brief_path_for(runs_dir: Path, num: str) -> Path:
    return runs_dir / f"{num}-brief.md"


@dataclass(frozen=True)
class Dispatch:
    ticket: Ticket
    worktree: Path
    brief_path: Path
    context_path: Path
    report_path: Path


@dataclass(frozen=True)
class RunResult:
    ok: bool
    exit_code: int


class AgentRunner(Protocol):
    def run(self, dispatch: Dispatch) -> RunResult: ...


class FakeRunner:
    """Scripted runner for tests. script[num] = {"exit": int, "report": str|None, "files": {rel: content}}."""

    def __init__(self, script: dict[str, dict] | None = None):
        self.script = script or {}
        self.calls: list[str] = []

    def run(self, dispatch: Dispatch) -> RunResult:
        num = dispatch.ticket.num
        self.calls.append(num)
        spec = {"exit": 0, "report": None, "files": {}, **self.script.get(num, {})}
        for rel, content in spec["files"].items():
            p = dispatch.worktree / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
        dispatch.report_path.write_text(
            spec["report"] if spec["report"] is not None else valid_report_text(),
            encoding="utf-8",
        )
        return RunResult(ok=spec["exit"] == 0, exit_code=spec["exit"])
