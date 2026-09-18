from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .compressor import estimate_tokens


DEFAULT_PATH = Path.home() / ".codex-usage-guard-data" / "telemetry.jsonl"


def _append(event: dict[str, Any], path: Path = DEFAULT_PATH) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, separators=(",", ":")) + "\n")
    return event


def record_compression(
    original: str,
    compacted: str,
    *,
    kind: str,
    task_id: str | None = None,
    path: Path = DEFAULT_PATH,
) -> dict[str, Any]:
    before = estimate_tokens(original)
    after = estimate_tokens(compacted)
    event = {
        "event": "compression",
        "kind": kind,
        "task_id": task_id,
        "estimated_tokens_before": before,
        "estimated_tokens_after": after,
        "estimated_tokens_avoided": max(0, before - after),
        "estimated_reduction_pct": round((1 - after / before) * 100, 1) if before else 0.0,
    }
    return _append(event, path)


def record_task_summary(
    task_id: str,
    *,
    status: str,
    counters: dict[str, int],
    path: Path = DEFAULT_PATH,
) -> dict[str, Any]:
    return _append(
        {
            "event": "task_summary",
            "task_id": task_id,
            "status": status,
            "counters": counters,
        },
        path,
    )


def aggregate(path: Path = DEFAULT_PATH, *, task_id: str | None = None) -> dict[str, Any]:
    if not path.exists():
        return {
            "events": 0,
            "estimated_tokens_before": 0,
            "estimated_tokens_after": 0,
            "estimated_tokens_avoided": 0,
            "estimated_reduction_pct": 0.0,
        }

    events: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if task_id and event.get("task_id") != task_id:
            continue
        events.append(event)

    compression = [e for e in events if e.get("event") == "compression"]
    before = sum(int(e.get("estimated_tokens_before", 0)) for e in compression)
    after = sum(int(e.get("estimated_tokens_after", 0)) for e in compression)
    return {
        "events": len(events),
        "compression_events": len(compression),
        "task_id": task_id,
        "estimated_tokens_before": before,
        "estimated_tokens_after": after,
        "estimated_tokens_avoided": max(0, before - after),
        "estimated_reduction_pct": round((1 - after / before) * 100, 1) if before else 0.0,
    }
