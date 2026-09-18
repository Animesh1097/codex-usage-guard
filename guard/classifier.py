from __future__ import annotations

import re
import subprocess
from pathlib import Path

from .models import GuardPlan


COMPLEXITY_WEIGHTS: dict[str, int] = {
    "intermittent": 3,
    "race condition": 3,
    "root cause": 2,
    "investigate": 2,
    "debug": 1,
    "refactor": 2,
    "architecture": 3,
    "migration": 3,
    "database": 2,
    "schema": 2,
    "security": 3,
    "authentication": 2,
    "authorization": 2,
    "login": 1,
    "payment": 2,
    "production": 2,
    "deploy": 2,
    "deployment": 2,
    "all forms": 2,
    "entire project": 3,
    "finish the project": 3,
}

RISK_WEIGHTS: dict[str, int] = {
    "production": 3,
    "deploy": 2,
    "deployment": 2,
    "database": 2,
    "schema": 2,
    "migration": 3,
    "payment": 3,
    "security": 3,
    "authentication": 2,
    "authorization": 2,
    "login": 1,
    "delete": 2,
    "credential": 3,
    "secret": 3,
}


def _has(text: str, needle: str) -> bool:
    if " " in needle:
        return needle in text
    return re.search(rf"\b{re.escape(needle)}\b", text) is not None


def _git_counts(repo_path: Path) -> tuple[int, int]:
    """Return (changed_files, tracked_files), or (0, 0) outside a git repo."""
    try:
        status = subprocess.run(
            ["git", "-C", str(repo_path), "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=4,
            check=False,
        )
        tracked = subprocess.run(
            ["git", "-C", str(repo_path), "ls-files"],
            capture_output=True,
            text=True,
            timeout=4,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return 0, 0

    changed_files = len([line for line in status.stdout.splitlines() if line.strip()]) if status.returncode == 0 else 0
    tracked_files = len([line for line in tracked.stdout.splitlines() if line.strip()]) if tracked.returncode == 0 else 0
    return changed_files, tracked_files


def _detect_kind(text: str) -> str:
    if any(_has(text, word) for word in ("deploy", "deployment", "production", "vercel", "release")):
        return "deployment"
    if any(_has(text, word) for word in ("database", "schema", "migration", "sql")):
        return "database"
    if any(_has(text, word) for word in ("security", "vulnerability", "auth", "authentication", "authorization", "credential", "secret", "login")):
        return "security"
    if any(_has(text, word) for word in ("bug", "debug", "fix", "broken", "error", "fail", "investigate")):
        return "debugging"
    if any(_has(text, word) for word in ("refactor", "architecture", "restructure")):
        return "refactor"
    if any(_has(text, word) for word in ("test", "coverage", "pytest", "jest")):
        return "testing"
    if any(_has(text, word) for word in ("ui", "css", "layout", "form", "button", "frontend")):
        return "ui"
    if any(_has(text, word) for word in ("readme", "docs", "documentation")):
        return "docs"
    return "general"


def _steps_for(kind: str, complexity: int, risk: int) -> tuple[str, ...]:
    base: list[str] = ["inspect_relevant_code"]
    if kind == "debugging":
        base += ["reproduce_or_trace_failure", "make_smallest_fix", "run_targeted_tests"]
    elif kind == "deployment":
        base += ["inspect_deploy_path", "make_smallest_fix", "run_targeted_tests", "run_build"]
    elif kind == "database":
        base += ["inspect_schema_and_callers", "make_smallest_fix", "run_targeted_tests"]
    elif kind == "security":
        base += ["trace_trust_boundary", "make_smallest_fix", "run_targeted_tests"]
    elif kind == "refactor":
        base += ["map_dependencies", "edit_in_small_steps", "run_targeted_tests", "run_build"]
    elif kind == "testing":
        base += ["locate_behavior_under_test", "add_or_fix_tests", "run_targeted_tests"]
    elif kind == "ui":
        base += ["trace_ui_state", "make_smallest_fix", "run_targeted_tests", "run_build"]
    elif kind == "docs":
        base += ["edit_docs", "review_diff"]
    else:
        base += ["make_smallest_change", "run_targeted_tests"]

    if risk >= 5 or complexity >= 6:
        base.append("review_diff")
    if kind == "deployment" and risk >= 5:
        base.append("verify_production")
    base.append("stop_when_requirements_are_verified")
    return tuple(dict.fromkeys(base))


def classify_task(task: str, repo_path: str | Path = ".") -> GuardPlan:
    text = " ".join(task.lower().split())
    complexity = 1
    risk = 1
    reasons: list[str] = []

    if len(task) > 240:
        complexity += 1
        reasons.append("long task description")
    if sum(text.count(joiner) for joiner in (" and ", " then ", " also ")) >= 2:
        complexity += 1
        reasons.append("multiple requested actions")

    for needle, weight in COMPLEXITY_WEIGHTS.items():
        if _has(text, needle):
            complexity += weight
            reasons.append(f"complexity keyword: {needle}")

    for needle, weight in RISK_WEIGHTS.items():
        if _has(text, needle):
            risk += weight
            reasons.append(f"risk keyword: {needle}")

    changed_files, tracked_files = _git_counts(Path(repo_path))
    if changed_files >= 5:
        complexity += 1
        reasons.append(f"{changed_files} changed files already in repo")
    if changed_files >= 20:
        complexity += 1
    if tracked_files >= 1500:
        complexity += 1
        reasons.append("large repository")

    complexity = max(1, min(10, complexity))
    risk = max(1, min(10, risk))
    kind = _detect_kind(text)

    if complexity <= 2 and risk <= 3:
        strategy = "single_turn"
        profile = "guard_fast"
        model = "gpt-5.6-luna"
        reasoning = "low"
        context_budget = 8_000
        max_turns = 2
        max_retries = 1
    elif complexity <= 5 and risk <= 6:
        strategy = "single_agent"
        profile = "guard_worker"
        model = "gpt-5.6-terra"
        reasoning = "medium"
        context_budget = 16_000
        max_turns = 4
        max_retries = 2
    elif complexity <= 7:
        strategy = "bounded_agent_loop"
        profile = "guard_worker"
        model = "gpt-5.6-terra"
        reasoning = "high"
        context_budget = 24_000
        max_turns = 6
        max_retries = 2
    else:
        strategy = "plan_execute_verify"
        profile = "guard_reasoner"
        model = "gpt-5.6-sol"
        reasoning = "high"
        context_budget = 32_000
        max_turns = 8
        max_retries = 2

    return GuardPlan(
        task=task,
        task_kind=kind,
        complexity=complexity,
        risk=risk,
        strategy=strategy,
        agent_profile=profile,
        preferred_model=model,
        reasoning_effort=reasoning,
        context_budget_tokens=context_budget,
        max_model_turns=max_turns,
        max_retries=max_retries,
        max_parallel_agents=1,
        predicted_steps=_steps_for(kind, complexity, risk),
        reasons=tuple(reasons[:10]),
    )
