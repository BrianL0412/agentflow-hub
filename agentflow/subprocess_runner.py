"""Drives a real headless CLI agent as a subprocess.

The agent command receives file paths, not content — the SDD file-handoff
contract. It MUST write a structured report (see agentflow.report) to {report}.
Example: --agent-cmd "my-agent --brief {brief} --context {context} --report-out {report}"
"""

from __future__ import annotations

import shlex
import subprocess

from agentflow.runner import Dispatch, RunResult

TIMEOUT_SECONDS = 30 * 60


class SubprocessRunner:
    def __init__(self, cmd_template: str):
        self.cmd_template = cmd_template

    def run(self, dispatch: Dispatch) -> RunResult:
        cmd = self.cmd_template.format(
            brief=shlex.quote(str(dispatch.brief_path)),
            context=shlex.quote(str(dispatch.context_path)),
            report=shlex.quote(str(dispatch.report_path)),
            worktree=shlex.quote(str(dispatch.worktree)),
        )
        try:
            r = subprocess.run(cmd, shell=True, cwd=dispatch.worktree,
                               capture_output=True, text=True, timeout=TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            return RunResult(ok=False, exit_code=124)
        return RunResult(ok=r.returncode == 0, exit_code=r.returncode)
