from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .compressor import estimate_tokens


DEFAULT_PATH = Path.home() / ".codex-usage-guard-data" / "telemetry.jsonl"


def record_compression(original: str, compacted: str, *, kind: str, path: Path = DEFAULT_PATH) -> dict[str, Any]:
    before = estimate_tokens(original)
    after = estimate_tokens(compacted)
    event = {
        "kind": kind,
        "estimated_tokens_before": before,
        "estimated_tokens_after": after,
        "estimated_tokens_avoided": max(0, before - after),
        "estimated_reduction_pct": round((1 - after / before) * 100, 1) if before else 0.0,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, separators=(",", ":")) + "\n")
    return event


def aggregate(path: Path = DEFAULT_PATH) -> dict[str, Any]:
    if not path.exists():
        return {"events": 0, "estimated_tokens_before": 0, "estimated_tokens_after": 0, "estimated_tokens_avoided": 0}
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    before = sum(int(e.get("estimated_tokens_before", 0)) for e in events)
    after = sum(int(e.get("estimated_tokens_after", 0)) for e in events)
    return {
        "events": len(events),
        "estimated_tokens_before": before,
        "estimated_tokens_after": after,
        "estimated_tokens_avoided": max(0, before - after),
        "estimated_reduction_pct": round((1 - after / before) * 100, 1) if before else 0.0,
    }
