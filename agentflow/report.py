"""Structured ticket reports — the Summary Layer. Template-filled, never LLM-compressed."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

REQUIRED_SECTIONS = ["Changes", "Decisions", "Interfaces", "Open issues", "Test evidence"]
SECTION_RE = re.compile(r"^##\s+(.+?)\s*$", re.M)


class ReportError(ValueError):
    pass


@dataclass(frozen=True)
class Report:
    sections: dict[str, str]
    raw: str


def report_path_for(runs_dir: Path, num: str) -> Path:
    return runs_dir / f"{num}-report.md"


def parse_report(path: Path) -> Report:
    raw = path.read_text(encoding="utf-8")
    marks = list(SECTION_RE.finditer(raw))
    sections: dict[str, str] = {}
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(raw)
        sections[m.group(1)] = raw[m.end():end].strip()
    for s in REQUIRED_SECTIONS:
        if not sections.get(s):
            raise ReportError(f"{path.name}: missing or empty '## {s}' section")
    return Report(sections=sections, raw=raw)


def valid_report_text(**overrides: str) -> str:
    body = {
        "Changes": "one change",
        "Decisions": "one decision, because reasons",
        "Interfaces": "run() -> int",
        "Open issues": "none",
        "Test evidence": "pytest: 4 passed",
    }
    # Match override keys case-insensitively against known section names,
    # so callers can write valid_report_text(changes=...) or valid_report_text(**{"Test evidence": ...}).
    lower_to_key = {k.lower(): k for k in body}
    for key, val in overrides.items():
        body[lower_to_key.get(key.lower(), key)] = val
    return "# Ticket report\n\n" + "\n\n".join(f"## {k}\n{v}" for k, v in body.items()) + "\n"
