from pathlib import Path

import pytest

from agentflow.graph import (
    CycleError, ancestors, apply_touch_conflicts, assert_acyclic,
    build_deps, descendants, topo_order,
)
from agentflow.tickets import Ticket, TicketError


def deps(**kw):
    return {k: set(v) for k, v in kw.items()}


def test_topo_order_respects_edges():
    d = deps(**{"01": [], "02": ["01"], "03": ["01"], "04": ["03"], "05": ["03"]})
    order = topo_order(d)
    assert order[0] == "01"
    assert order.index("02") < order.index("05") or order.index("03") < order.index("05")
    assert order.index("03") < order.index("04")
    assert order.index("03") < order.index("05")
    assert sorted(order) == ["01", "02", "03", "04", "05"]


def test_topo_order_deterministic_tiebreak():
    d = deps(**{"02": [], "01": [], "03": []})
    assert topo_order(d) == ["01", "02", "03"]


def test_cycle_detected_with_path():
    d = deps(**{"01": ["03"], "02": ["01"], "03": ["02"]})
    with pytest.raises(CycleError) as exc:
        assert_acyclic(d)
    assert set(exc.value.cycle) == {"01", "02", "03"}


def test_diamond_is_acyclic():
    d = deps(**{"01": [], "02": ["01"], "03": ["01"], "04": ["02", "03"]})
    assert_acyclic(d)  # must not raise
    order = topo_order(d)
    assert order[-1] == "04"


def test_unknown_blocker_rejected(tmp_path):
    t = Ticket("01", "a", "A", ["99"], [], "brief", tmp_path / "01-a.md")
    with pytest.raises(TicketError, match="99"):
        build_deps([t])


def mk(num: str, touches: list[str], blocked: list[str] | None = None) -> Ticket:
    return Ticket(num, f"slug-{num}", f"T{num}", blocked or [], touches, "b", Path(f"{num}.md"))


def test_overlapping_touches_become_serialized():
    tickets = [mk("01", ["src/a"]), mk("02", ["src/a/helper", "src/b"])]
    d = build_deps(tickets)
    out = apply_touch_conflicts(tickets, d)
    assert "01" in out["02"]  # 02 now blocked by 01
    assert d["02"] == set()   # input not mutated


def test_disjoint_touches_left_parallel():
    tickets = [mk("01", ["src/a"]), mk("02", ["src/b"])]
    out = apply_touch_conflicts(tickets, build_deps(tickets))
    assert out["01"] == set() and out["02"] == set()


def test_related_tickets_get_no_synthetic_edge():
    tickets = [mk("01", ["src/a"]), mk("02", ["src/a"], blocked=["01"])]
    out = apply_touch_conflicts(tickets, build_deps(tickets))
    assert out["02"] == {"01"}  # unchanged, no duplicate


def test_ancestors_transitive():
    d = {"01": set(), "02": {"01"}, "03": {"01"}, "04": {"02", "03"}}
    assert ancestors(d, "04") == {"01", "02", "03"}
    assert ancestors(d, "01") == set()


def test_descendants_transitive():
    d = {"01": set(), "02": {"01"}, "03": {"01"}, "04": {"02", "03"}}
    assert descendants(d, "01") == {"02", "03", "04"}
    assert descendants(d, "04") == set()
