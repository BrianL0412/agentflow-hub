from pathlib import Path

from agentflow.context import assemble_context
from agentflow.report import report_path_for, valid_report_text
from agentflow.tickets import Ticket


def mk(num: str, blocked: list[str]) -> Ticket:
    return Ticket(num, f"slug-{num}", f"T{num}", blocked, [], "brief", Path(f"{num}.md"))


def test_context_contains_ancestors_only(tmp_path: Path):
    deps = {"01": set(), "02": {"01"}, "03": set()}
    by_num = {"01": mk("01", []), "02": mk("02", ["01"]), "03": mk("03", [])}
    report_path_for(tmp_path, "01").write_text(valid_report_text(changes="from 01"))
    report_path_for(tmp_path, "03").write_text(valid_report_text(changes="from 03 UNRELATED"))
    out = assemble_context(by_num["02"], deps, by_num, tmp_path)
    text = out.read_text()
    assert "from 01" in text
    assert "UNRELATED" not in text          # non-ancestor excluded
    assert "01-report.md" in text           # Raw Layer pointer present


def test_context_with_no_ancestors(tmp_path: Path):
    deps = {"01": set()}
    t = mk("01", [])
    out = assemble_context(t, deps, {"01": t}, tmp_path)
    assert "no upstream" in out.read_text().lower()
