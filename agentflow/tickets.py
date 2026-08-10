"""Parse to-tickets local-markdown output (one NN-slug.md per ticket)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

HEADER_RE = re.compile(r"^#\s+(\d+)\s+—\s+(.+?)\s*$", re.M)
BLOCKED_RE = re.compile(r"^\*\*Blocked by:\*\*\s*(.+?)\s*$", re.M)
TOUCHES_RE = re.compile(r"^\*\*Touches:\*\*\s*(.+?)\s*$", re.M)
NUM_RE = re.compile(r"(\d+)")


class TicketError(ValueError):
    pass


@dataclass(frozen=True)
class Ticket:
    num: str
    slug: str
    title: str
    blocked_by: list[str]
    touches: list[str]
    brief: str
    path: Path


def _parse_nums(text: str) -> list[str]:
    if text.lower().startswith("none"):
        return []
    return NUM_RE.findall(text)


def _parse_list(text: str) -> list[str]:
    return [x.strip() for x in text.split(",") if x.strip()]


def load_tickets(issues_dir: Path) -> list[Ticket]:
    tickets: list[Ticket] = []
    for path in sorted(issues_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        header = HEADER_RE.search(text)
        if not header:
            raise TicketError(f"{path.name}: missing '# NN — Title' header")
        num, title = header.group(1), header.group(2)
        blocked = BLOCKED_RE.search(text)
        if not blocked:
            raise TicketError(f"{path.name}: missing '**Blocked by:**' line")
        touches = TOUCHES_RE.search(text)
        tickets.append(
            Ticket(
                num=num,
                slug=path.stem.split("-", 1)[1] if "-" in path.stem else path.stem,
                title=title,
                blocked_by=_parse_nums(blocked.group(1)),
                touches=_parse_list(touches.group(1)) if touches else [],
                brief=text,
                path=path,
            )
        )
    if not tickets:
        raise TicketError(f"no ticket files in {issues_dir}")
    tickets.sort(key=lambda t: t.num)
    return tickets
