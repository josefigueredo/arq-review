"""Every write arq makes to Jira/JSM, one JSON line each in .arq/jira-writes.jsonl (same idea as jira-kanban)."""
from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path
from typing import Callable, List, Optional


def _utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def journal(repo: Path, command: str, now: Optional[Callable[[], str]] = None) -> Callable[[dict], None]:
    """A writer for Jira(journal=...). It never raises: a log that cannot be written must not undo the write."""
    clock = now or _utc_now

    def write(entry: dict) -> None:
        try:
            path = repo / ".arq" / "jira-writes.jsonl"
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({"ts": clock(), "tool": "arq-review", "command": command, **entry},
                                        ensure_ascii=False) + "\n")
        except OSError:
            pass

    return write


def read_entries(repo: Path) -> List[dict]:
    """Every journaled write, oldest first. A broken line is skipped, never fatal."""
    path = repo / ".arq" / "jira-writes.jsonl"
    if not path.exists():
        return []
    entries: List[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(entry, dict):
            entries.append(entry)
    return entries
