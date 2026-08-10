"""Dependency graph over tickets: validation, topological order."""

from __future__ import annotations

from agentflow.tickets import Ticket, TicketError


class CycleError(ValueError):
    def __init__(self, cycle: list[str]):
        self.cycle = cycle
        super().__init__(f"dependency cycle: {' -> '.join(cycle)}")


def build_deps(tickets: list[Ticket]) -> dict[str, set[str]]:
    known = {t.num for t in tickets}
    deps: dict[str, set[str]] = {}
    for t in tickets:
        unknown = set(t.blocked_by) - known
        if unknown:
            raise TicketError(f"{t.num}: unknown blocker(s) {sorted(unknown)}")
        deps[t.num] = set(t.blocked_by)
    assert_acyclic(deps)
    return deps


def assert_acyclic(deps: dict[str, set[str]]) -> None:
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {n: WHITE for n in deps}
    stack: list[str] = []

    def visit(n: str) -> None:
        color[n] = GRAY
        stack.append(n)
        for m in deps[n]:
            if color[m] == GRAY:
                raise CycleError(stack[stack.index(m):] + [m])
            if color[m] == WHITE:
                visit(m)
        stack.pop()
        color[n] = BLACK

    for n in sorted(deps):
        if color[n] == WHITE:
            visit(n)


def topo_order(deps: dict[str, set[str]]) -> list[str]:
    assert_acyclic(deps)
    indeg = {n: len(d) for n, d in deps.items()}
    ready = sorted(n for n, d in indeg.items() if d == 0)
    order: list[str] = []
    while ready:
        n = ready.pop(0)
        order.append(n)
        for m in sorted(deps):
            if n in deps[m]:
                indeg[m] -= 1
                if indeg[m] == 0:
                    ready.append(m)
        ready.sort()
    return order
