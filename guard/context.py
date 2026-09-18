from __future__ import annotations

from pathlib import Path
from typing import Any

from .budget import budget_status
from .repo import inspect_repo, changed_file_hashes
from .state import TASKS_ROOT, load_task, save_task


def refresh_file_hashes(state: dict[str, Any]) -> dict[str, Any]:
    repo = inspect_repo(state.get("repo_root", "."))
    current = changed_file_hashes(repo)
    previous = state.get("file_hashes", {})
    changed_since_snapshot = sorted(
        path for path, digest in current.items()
        if previous.get(path) != digest
    )
    removed = sorted(path for path in previous if path not in current)
    state["repo"] = repo.to_dict()
    state["file_hashes"] = current
    state["changed_since_snapshot"] = changed_since_snapshot
    state["removed_since_snapshot"] = removed
    return state


def make_capsule(task_id: str, *, root: Path = TASKS_ROOT) -> dict[str, Any]:
    state = load_task(task_id, root=root)
    state = refresh_file_hashes(state)
    save_task(state, root=root)

    plan = state.get("plan", {})
    repo = state.get("repo", {})
    recent = state.get("events", [])[-6:]
    return {
        "task_id": task_id,
        "objective": state.get("objective"),
        "status": state.get("status"),
        "hot": {
            "unresolved": state.get("unresolved", []),
            "changed_since_snapshot": state.get("changed_since_snapshot", []),
            "removed_since_snapshot": state.get("removed_since_snapshot", []),
            "changed_files": repo.get("changed_files", []),
            "sensitive_files": repo.get("sensitive_files", []),
        },
        "warm": {
            "completed": state.get("completed", [])[-12:],
            "recent_events": recent,
            "task_kind": plan.get("task_kind"),
            "strategy": plan.get("strategy"),
            "agent_profile": plan.get("agent_profile"),
            "reasoning_effort": plan.get("reasoning_effort"),
            "verification": {
                "test_command": repo.get("test_command"),
                "build_command": repo.get("build_command"),
                "lint_command": repo.get("lint_command"),
                "typecheck_command": repo.get("typecheck_command"),
            },
        },
        "cold": {
            "state_file": str(root / f"{task_id}.json"),
            "full_event_count": len(state.get("events", [])),
            "tracked_file_hashes": len(state.get("file_hashes", {})),
        },
        "budget": budget_status(state),
    }
