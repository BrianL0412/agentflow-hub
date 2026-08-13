# AgentFlow Hub

A durable, multi-agent execution control plane for ticket DAGs.

Given a set of tickets with blocking edges (e.g. produced by a planning
session), AgentFlow Hub executes them with parallel headless CLI agents in
isolated git worktrees — preserving per-ticket engineering discipline
(structured briefs, test-gated completion, review gates) while adding what
single-session workflows lack: persistent state, crash recovery, DAG
parallelism, a four-layer merge defense, and a token accounting report.

## Quickstart (demo mode, no real agent)

    agentflow run --issues-dir ./issues --repo /path/to/target --yes
    agentflow status --runs-dir /path/to/target/.agentflow/runs
    agentflow report --runs-dir /path/to/target/.agentflow/runs

## Real agent

    agentflow run --issues-dir ./issues --repo /path/to/target \
      --test-cmd "pytest -x" \
      --agent-cmd "my-agent --brief {brief} --context {context} --report-out {report}"

The agent command receives file paths and must write a structured report
(Changes / Decisions / Interfaces / Open issues / Test evidence) to {report}.

## Ticket format

One markdown file per ticket, `NN-slug.md`:

    # 01 — Ledger storage
    **Blocked by:** None — can start immediately
    **Touches:** agentflow/ledger.py, tests/test_ledger.py   (optional; overlaps auto-serialize)

## Design

See docs/adr/0001 and 0002 (in the author's design workspace): portfolio-first
positioning, durable control plane, merge defense layers.
