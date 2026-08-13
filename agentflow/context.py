"""Active Context assembly: ancestor deliverables + Raw Layer pointers."""

from __future__ import annotations

from pathlib import Path

from agentflow.graph import ancestors
from agentflow.report import parse_report, report_path_for
from agentflow.tickets import Ticket


def context_path_for(runs_dir: Path, num: str) -> Path:
    return runs_dir / f"{num}-context.md"


def assemble_context(
    ticket: Ticket,
    deps: dict[str, set[str]],
    by_num: dict[str, Ticket],
    runs_dir: Path,
) -> Path:
    ups = sorted(ancestors(deps, ticket.num))
    out = context_path_for(runs_dir, ticket.num)
    parts = [
        f"# Active context for ticket {ticket.num} — {ticket.title}",
        "",
        "You receive ONLY structured deliverables from upstream tickets.",
        "If a summary is insufficient, read the Raw Layer file it points to.",
        "",
    ]
    if not ups:
        parts.append("No upstream tickets — this ticket has no dependencies.")
    for n in ups:
        rp = report_path_for(runs_dir, n)
        rep = parse_report(rp)
        parts.append(f"---\n## Upstream ticket {n} — {by_num[n].title}")
        for section, text in rep.sections.items():
            parts.append(f"### {section}\n{text}")
        parts.append(f"Raw layer: {rp}")
    out.write_text("\n\n".join(parts) + "\n", encoding="utf-8")
    return out
