import pytest

from agentflow.graph import CycleError, assert_acyclic, build_deps, topo_order
from agentflow.tickets import TicketError


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
    from agentflow.tickets import Ticket

    t = Ticket("01", "a", "A", ["99"], [], "brief", tmp_path / "01-a.md")
    with pytest.raises(TicketError, match="99"):
        build_deps([t])
