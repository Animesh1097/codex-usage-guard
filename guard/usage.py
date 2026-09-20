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


def _global_token_total(home: Path) -> int | None:
    db = _state_db_path(home)
    if db is None:
        return None
    try:
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        row = conn.execute("SELECT COALESCE(SUM(tokens_used), 0) FROM threads").fetchone()
        return int(row[0]) if row else 0
    except sqlite3.Error:
        return None
    finally:
        try:
            conn.close()
        except (UnboundLocalError, sqlite3.Error):
            pass


def _rollout_files(home: Path, thread_id: str | None = None) -> list[Path]:
    sessions = home / "sessions"
    if not sessions.exists():
        return []
    pattern = f"*{thread_id}*.jsonl" if thread_id and not thread_id.startswith("__usage_guard_") else "rollout-*.jsonl"
    try:
        return sorted(
            sessions.rglob(pattern),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
    except OSError:
        return []


def _latest_token_event(home: Path, thread_id: str | None = None) -> dict[str, Any] | None:
    for path in _rollout_files(home, thread_id)[:12]:
        latest: dict[str, Any] | None = None
        try:
            with path.open("r", encoding="utf-8", errors="replace") as handle:
                for line in handle:
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if obj.get("type") == "event_msg" and obj.get("payload", {}).get("type") == "token_count":
                        latest = obj["payload"]
        except OSError:
            continue
        if latest is not None:
            return latest
    return None


def _latest_rate_limits(home: Path, thread_id: str | None = None) -> dict[str, Any] | None:
    event = _latest_token_event(home, thread_id)
    limits = event.get("rate_limits") if isinstance(event, dict) else None
    return limits if isinstance(limits, dict) else None


def _token_breakdown(home: Path, thread_id: str | None = None) -> dict[str, Any] | None:
    event = _latest_token_event(home, thread_id)
    info = event.get("info") if isinstance(event, dict) else None
    total = info.get("total_token_usage") if isinstance(info, dict) else None
    if not isinstance(total, dict):
        return None
    return {
        "input_tokens": total.get("input_tokens"),
        "cached_input_tokens": total.get("cached_input_tokens"),
        "output_tokens": total.get("output_tokens"),
        "reasoning_output_tokens": total.get("reasoning_output_tokens"),
        "total_tokens": total.get("total_tokens"),
        "model_context_window": info.get("model_context_window"),
    }


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
    actual_thread = str(row.get("id")) if row else requested_thread
    limits = _latest_rate_limits(home, actual_thread)
    breakdown = _token_breakdown(home, actual_thread)
    return {
        "available": bool(row or limits),
        "thread_id": actual_thread,
        "tokens_total": int(row.get("tokens_used", 0)) if row else None,
        "tokens_global_total": _global_token_total(home),
        "token_breakdown": breakdown,
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
    token_scope = None
    if same_thread and isinstance(before, int) and isinstance(after, int):
        token_delta = max(0, after - before)
        token_scope = "thread"
    else:
        global_before = baseline.get("tokens_global_total")
        global_after = current.get("tokens_global_total")
        if isinstance(global_before, int) and isinstance(global_after, int):
            token_delta = max(0, global_after - global_before)
            token_scope = "global-approximate"

    def pct_delta(window: str) -> float | None:
        b = ((baseline.get("rate_limits") or {}).get(window) or {}).get("used_percent")
        a = ((current.get("rate_limits") or {}).get(window) or {}).get("used_percent")
        if isinstance(b, (int, float)) and isinstance(a, (int, float)):
            return round(float(a) - float(b), 3)
        return None

    breakdown_delta: dict[str, int] | None = None
    if same_thread:
        b_break = baseline.get("token_breakdown")
        a_break = current.get("token_breakdown")
        if isinstance(b_break, dict) and isinstance(a_break, dict):
            keys = ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens", "total_tokens")
            values: dict[str, int] = {}
            for key in keys:
                b_value = b_break.get(key)
                a_value = a_break.get(key)
                if isinstance(b_value, int) and isinstance(a_value, int):
                    values[key] = max(0, a_value - b_value)
            breakdown_delta = values or None

    return {
        "same_thread": same_thread,
        "tokens_delta": token_delta,
        "token_delta_scope": token_scope,
        "token_breakdown_delta": breakdown_delta,
        "primary_used_percent_delta": pct_delta("primary"),
        "secondary_used_percent_delta": pct_delta("secondary"),
    }
