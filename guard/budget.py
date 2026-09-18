from __future__ import annotations

from typing import Any


def budget_status(state: dict[str, Any]) -> dict[str, Any]:
    plan = state.get("plan", {})
    counters = state.get("counters", {})
    limits = {
        "actions": int(plan.get("max_actions", 10)),
        "model_turns": int(plan.get("max_model_turns", 4)),
        "retries": int(plan.get("max_retries", 2)),
    }
    used = {
        "actions": int(counters.get("actions", 0)),
        "model_turns": int(counters.get("model_turns", 0)),
        "retries": int(counters.get("retries", 0)),
    }
    exhausted = {key: used[key] >= limits[key] for key in limits}
    return {
        "limits": limits,
        "used": used,
        "remaining": {key: max(0, limits[key] - used[key]) for key in limits},
        "exhausted": exhausted,
        "may_continue": not exhausted["actions"],
        "may_use_model": not exhausted["actions"] and not exhausted["model_turns"],
        "may_retry": not exhausted["actions"] and not exhausted["retries"],
    }


def assert_action_allowed(state: dict[str, Any], *, kind: str, is_retry: bool = False) -> tuple[bool, str]:
    status = budget_status(state)
    if not status["may_continue"]:
        return False, "task action budget exhausted; reassess before more work"
    if kind == "model" and not status["may_use_model"]:
        return False, "model-turn budget exhausted; continue with deterministic evidence or reassess"
    if is_retry and not status["may_retry"]:
        return False, "retry budget exhausted; new evidence or escalation is required"
    return True, "allowed"
