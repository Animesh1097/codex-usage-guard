from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .budget import assert_action_allowed, budget_status
from .repo import RepoProfile, changed_file_hashes
from .usage import usage_delta, usage_snapshot


DATA_ROOT = Path.home() / ".codex-usage-guard-data"
TASKS_ROOT = DATA_ROOT / "tasks"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _task_path(task_id: str, root: Path = TASKS_ROOT) -> Path:
    return root / f"{task_id}.json"


def start_task(task: str, plan: dict[str, Any], repo: RepoProfile, *, root: Path = TASKS_ROOT) -> dict[str, Any]:
    task_id = uuid.uuid4().hex[:12]
    baseline_usage = usage_snapshot(repo_root=repo.root)
    state = {
        "version": 3,
        "task_id": task_id,
        "objective": task,
        "repo_root": repo.root,
        "created_at": _now(),
        "updated_at": _now(),
        "status": "active",
        "plan": plan,
        "repo": repo.to_dict(),
        "file_hashes": changed_file_hashes(repo),
        "counters": {"actions": 0, "model_turns": 0, "retries": 0},
        "events": [],
        "completed": [],
        "unresolved": [],
        "usage": {
            "baseline": baseline_usage,
            "finish": None,
            "delta": None,
        },
    }
    path = _task_path(task_id, root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    return state


def load_task(task_id: str, *, root: Path = TASKS_ROOT) -> dict[str, Any]:
    path = _task_path(task_id, root)
    if not path.exists():
        raise FileNotFoundError(f"unknown task id: {task_id}")
    return json.loads(path.read_text(encoding="utf-8"))


def save_task(state: dict[str, Any], *, root: Path = TASKS_ROOT) -> None:
    state["updated_at"] = _now()
    path = _task_path(str(state["task_id"]), root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def record_action(
    task_id: str,
    *,
    action: str,
    kind: str = "deterministic",
    outcome: str = "info",
    details: str = "",
    retry: bool = False,
    root: Path = TASKS_ROOT,
) -> dict[str, Any]:
    state = load_task(task_id, root=root)
    allowed, reason = assert_action_allowed(state, kind=kind, is_retry=retry)
    if not allowed:
        return {"recorded": False, "reason": reason, "budget": budget_status(state)}

    event = {
        "time": _now(),
        "action": action,
        "kind": kind,
        "outcome": outcome,
        "retry": retry,
        "details": details[:1200],
    }
    state["events"].append(event)
    state["counters"]["actions"] += 1
    if kind == "model":
        state["counters"]["model_turns"] += 1
    if retry:
        state["counters"]["retries"] += 1

    if outcome == "pass":
        if action not in state["completed"]:
            state["completed"].append(action)
        state["unresolved"] = [x for x in state["unresolved"] if x != action]
    elif outcome == "fail" and action not in state["unresolved"]:
        state["unresolved"].append(action)

    save_task(state, root=root)
    return {"recorded": True, "budget": budget_status(state), "event": event}


def finish_task(task_id: str, *, status: str = "completed", root: Path = TASKS_ROOT) -> dict[str, Any]:
    state = load_task(task_id, root=root)
    state["status"] = status
    current = usage_snapshot(
        thread_id=(state.get("usage") or {}).get("baseline", {}).get("thread_id"),
        repo_root=state.get("repo_root"),
    )
    usage = state.setdefault("usage", {})
    usage["finish"] = current
    usage["delta"] = usage_delta(usage.get("baseline"), current)
    save_task(state, root=root)
    return state
