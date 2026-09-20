from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any


def codex_home() -> Path:
    configured = os.environ.get("CODEX_HOME")
    return Path(configured).expanduser() if configured else Path.home() / ".codex"


def _state_db_path(home: Path) -> Path | None:
    candidates: list[tuple[int, Path]] = []
    for path in home.glob("state_*.sqlite"):
        suffix = path.stem.removeprefix("state_")
        if suffix.isdigit():
            candidates.append((int(suffix), path))
    return max(candidates, default=(0, None), key=lambda item: item[0])[1]


def _read_thread(
    *,
    home: Path,
    thread_id: str | None = None,
    repo_root: str | None = None,
) -> dict[str, Any] | None:
    db = _state_db_path(home)
    if db is None:
        return None
    try:
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
    except sqlite3.Error:
        return None

    try:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(threads)")}
        if not {"id", "tokens_used"}.issubset(columns):
            return None

        optional = [name for name in ("model", "cwd", "updated_at") if name in columns]
        select = ", ".join(["id", "tokens_used", *optional])

        if thread_id:
            row = conn.execute(
                f"SELECT {select} FROM threads WHERE id = ? LIMIT 1",
                (thread_id,),
            ).fetchone()
        elif repo_root and "cwd" in columns:
            order = "updated_at DESC" if "updated_at" in columns else "rowid DESC"
            row = conn.execute(
                f"SELECT {select} FROM threads WHERE cwd = ? ORDER BY {order} LIMIT 1",
                (repo_root,),
            ).fetchone()
        else:
            order = "updated_at DESC" if "updated_at" in columns else "rowid DESC"
            row = conn.execute(f"SELECT {select} FROM threads ORDER BY {order} LIMIT 1").fetchone()

        if row is None:
            return None
        data = dict(row)
        data["tokens_used"] = int(data.get("tokens_used") or 0)
        data["db"] = str(db)
        return data
    except sqlite3.Error:
        return None
    finally:
        conn.close()


def _latest_rate_limits(home: Path) -> dict[str, Any] | None:
    sessions = home / "sessions"
    if not sessions.exists():
        return None

    try:
        files = sorted(
            sessions.rglob("rollout-*.jsonl"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
    except OSError:
        return None

    for path in files[:12]:
        latest: dict[str, Any] | None = None
        try:
            with path.open("r", encoding="utf-8", errors="replace") as handle:
                for line in handle:
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if obj.get("type") != "event_msg":
                        continue
                    payload = obj.get("payload", {})
                    if payload.get("type") != "token_count":
                        continue
                    limits = payload.get("rate_limits")
                    if isinstance(limits, dict):
                        latest = limits
        except OSError:
            continue
        if latest is not None:
            return latest
    return None


def _window(limits: dict[str, Any] | None, key: str) -> dict[str, Any] | None:
    if not isinstance(limits, dict):
        return None
    raw = limits.get(key)
    if not isinstance(raw, dict):
        return None
    return {
        "used_percent": raw.get("used_percent"),
        "window_minutes": raw.get("window_minutes") or raw.get("window_duration_mins"),
        "resets_at": raw.get("resets_at"),
        "resets_in_seconds": raw.get("resets_in_seconds"),
    }


def usage_snapshot(
    *,
    thread_id: str | None = None,
    repo_root: str | None = None,
    home: Path | None = None,
) -> dict[str, Any]:
    home = home or codex_home()
    requested_thread = thread_id or os.environ.get("CODEX_THREAD_ID")
    row = _read_thread(home=home, thread_id=requested_thread, repo_root=repo_root)
    limits = _latest_rate_limits(home)

    actual_thread = str(row.get("id")) if row else requested_thread
    return {
        "available": bool(row or limits),
        "thread_id": actual_thread,
        "tokens_total": int(row.get("tokens_used", 0)) if row else None,
        "model": row.get("model") if row else None,
        "cwd": row.get("cwd") if row else repo_root,
        "source_db": row.get("db") if row else None,
        "rate_limits": {
            "primary": _window(limits, "primary"),
            "secondary": _window(limits, "secondary"),
            "plan_type": limits.get("plan_type") if isinstance(limits, dict) else None,
        },
    }


def usage_delta(baseline: dict[str, Any] | None, current: dict[str, Any] | None) -> dict[str, Any]:
    baseline = baseline or {}
    current = current or {}
    before = baseline.get("tokens_total")
    after = current.get("tokens_total")
    same_thread = bool(
        baseline.get("thread_id")
        and current.get("thread_id")
        and baseline.get("thread_id") == current.get("thread_id")
    )
    token_delta = None
    if same_thread and isinstance(before, int) and isinstance(after, int):
        token_delta = max(0, after - before)

    def pct_delta(window: str) -> float | None:
        b = ((baseline.get("rate_limits") or {}).get(window) or {}).get("used_percent")
        a = ((current.get("rate_limits") or {}).get(window) or {}).get("used_percent")
        if isinstance(b, (int, float)) and isinstance(a, (int, float)):
            return round(float(a) - float(b), 3)
        return None

    return {
        "same_thread": same_thread,
        "tokens_delta": token_delta,
        "primary_used_percent_delta": pct_delta("primary"),
        "secondary_used_percent_delta": pct_delta("secondary"),
    }
