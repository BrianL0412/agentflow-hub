"""Append-only JSONL ledger. Single writer: the scheduler main thread."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

STATUS_PENDING = "pending"
STATUS_READY = "ready"
STATUS_RUNNING = "running"
STATUS_REVIEW = "review"
STATUS_MERGING = "merging"
STATUS_DONE = "done"
STATUS_FAILED = "failed"
STATUS_BLOCKED = "blocked"

TERMINAL_OK = {STATUS_DONE}
TERMINAL_BAD = {STATUS_FAILED, STATUS_BLOCKED}


class Ledger:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)

    def append(self, ticket: str, type: str, payload: dict) -> None:
        rec = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "ticket": ticket,
            "type": type,
            **payload,
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())

    def _records(self) -> list[dict]:
        return [
            json.loads(line)
            for line in self.path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def states(self) -> dict[str, str]:
        out: dict[str, str] = {}
        for rec in self._records():
            if rec["type"] == "status":
                out[rec["ticket"]] = rec["status"]
        return out

    def meters(self) -> list[dict]:
        return [rec for rec in self._records() if rec["type"] == "meter"]
