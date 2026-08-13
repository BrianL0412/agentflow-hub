"""Token accounting: Hub structured handoff vs naive paste-everything baseline.

Token counts are estimates (chars / 4) — good enough for relative comparison,
which is the portfolio evidence this module exists to produce.
"""

from __future__ import annotations

from pathlib import Path

from agentflow.graph import ancestors
from agentflow.ledger import Ledger
from agentflow.report import parse_report, report_path_for
from agentflow.tickets import Ticket


def estimate_tokens(chars: int) -> int:
    return max(1, chars // 4)


def _baseline_chars(ticket: Ticket, deps: dict[str, set[str]], runs_dir: Path) -> int:
    total = len(ticket.brief)
    for n in ancestors(deps, ticket.num):
        rp = report_path_for(runs_dir, n)
        if rp.exists():
            total += len(parse_report(rp).raw)
    return total


def build_comparison(
    tickets: list[Ticket],
    deps: dict[str, set[str]],
    ledger: Ledger,
    runs_dir: Path,
) -> str:
    dispatch_chars = {m["ticket"]: m["chars"] for m in ledger.meters() if m["kind"] == "dispatch"}
    lines = [
        "# Token report — Hub structured handoff vs naive copy-paste",
        "",
        "Tokens estimated as chars/4.",
        "",
        "| Ticket | Baseline tokens (paste everything upstream) | Hub tokens (structured context) |",
        "|--------|--------------------------------------------|--------------------------------|",
    ]
    tot_base = tot_hub = 0
    for t in tickets:
        base = estimate_tokens(_baseline_chars(t, deps, runs_dir))
        hub = estimate_tokens(dispatch_chars.get(t.num, 0))
        tot_base += base
        tot_hub += hub
        lines.append(f"| {t.num} | {base} | {hub} |")
    savings = (1 - tot_hub / tot_base) * 100 if tot_base else 0.0
    lines += [
        f"| **Total** | **{tot_base}** | **{tot_hub}** |",
        "",
        f"**Savings: {savings:.1f}%** of upstream-context tokens vs naive copy-paste.",
    ]
    return "\n".join(lines) + "\n"


def write_comparison(
    tickets: list[Ticket],
    deps: dict[str, set[str]],
    ledger: Ledger,
    runs_dir: Path,
) -> Path:
    out = runs_dir / "token-report.md"
    out.write_text(build_comparison(tickets, deps, ledger, runs_dir), encoding="utf-8")
    return out
