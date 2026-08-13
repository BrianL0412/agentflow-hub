from pathlib import Path

import pytest

from agentflow.report import (
    REQUIRED_SECTIONS,
    ReportError,
    parse_report,
    valid_report_text,
)


def test_valid_report_parses(tmp_path: Path):
    p = tmp_path / "r.md"
    p.write_text(valid_report_text(changes="added ledger module"))
    r = parse_report(p)
    assert r.sections["Changes"] == "added ledger module"
    for s in REQUIRED_SECTIONS:
        assert s in r.sections


def test_missing_section_rejected(tmp_path: Path):
    p = tmp_path / "r.md"
    p.write_text("## Changes\ndid stuff\n")
    with pytest.raises(ReportError, match="Decisions"):
        parse_report(p)


def test_empty_section_rejected(tmp_path: Path):
    p = tmp_path / "r.md"
    p.write_text(valid_report_text(**{"Test evidence": "   "}))
    with pytest.raises(ReportError, match="Test evidence"):
        parse_report(p)
