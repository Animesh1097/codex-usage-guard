from __future__ import annotations

import re
from pathlib import Path

from .capabilities import recommend_skill_refs
from .models import GuardPlan
from .repo import RepoProfile, inspect_repo


COMPLEXITY_WEIGHTS: dict[str, int] = {
    "intermittent": 3,
    "race condition": 3,
    "root cause": 2,
    "investigate": 2,
    "debug": 1,
    "bug": 1,
    "refactor": 2,
    "architecture": 3,
    "migration": 3,
    "database": 2,
    "schema": 2,
    "security": 3,
    "authentication": 2,
    "authorization": 2,
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
    "delete": 2,
    "credential": 3,
    "secret": 3,
}


def _has(text: str, needle: str) -> bool:
    if " " in needle:
        return needle in text
    return re.search(rf"\b{re.escape(needle)}\b", text) is not None


def _detect_kind(text: str, profile: RepoProfile) -> str:
    if any(_has(text, word) for word in ("deploy", "deployment", "production", "vercel", "release")):
        return "deployment"
    if any(_has(text, word) for word in ("database", "schema", "migration", "sql", "prisma")):
        return "database"
    if any(_has(text, word) for word in ("security", "vulnerability", "auth", "authentication", "authorization", "credential", "secret", "login")):
        return "security"
    if any(_has(text, word) for word in ("bug", "debug", "fix", "broken", "error", "fail", "investigate")):
        return "debugging"
    if any(_has(text, word) for word in ("refactor", "architecture", "restructure")):
        return "refactor"
    if any(_has(text, word) for word in ("test", "coverage", "pytest", "jest", "vitest")):
        return "testing"
    if any(_has(text, word) for word in ("ui", "css", "layout", "form", "button", "frontend")):
        return "ui"
    if any(_has(text, word) for word in ("readme", "docs", "documentation")) or profile.docs_only:
        return "docs"

    sensitive = " ".join(profile.sensitive_files).lower()
    if any(word in sensitive for word in ("migration", "schema", "prisma", "database")):
        return "database"
    if any(word in sensitive for word in ("auth", "security", "permission", "credential", "secret", "payment", "billing")):
        return "security"
    if any(word in sensitive for word in ("workflow", "deploy", "vercel", "netlify", "docker", "terraform", "infra")):
        return "deployment"
    return "general"


def _steps_for(kind: str, profile: RepoProfile, complexity: int, risk: int) -> tuple[str, ...]:
    base: list[str] = ["inspect_relevant_code"]
    if kind == "debugging":
        base += ["reproduce_or_trace_failure", "make_smallest_fix"]
    elif kind == "deployment":
        base += ["inspect_deploy_path", "make_smallest_fix"]
    elif kind == "database":
        base += ["inspect_schema_and_callers", "make_smallest_fix"]
    elif kind == "security":
        base += ["trace_trust_boundary", "make_smallest_fix"]
    elif kind == "refactor":
        base += ["map_dependencies", "edit_in_small_steps"]
    elif kind == "testing":
        base += ["locate_behavior_under_test", "add_or_fix_tests"]
    elif kind == "ui":
        base += ["trace_ui_state", "make_smallest_fix"]
    elif kind == "docs":
        base += ["edit_docs"]
    else:
        base += ["make_smallest_change"]

    if profile.test_command and not profile.docs_only:
        base.append("run_targeted_tests")
    if profile.typecheck_command and not profile.docs_only:
        base.append("run_typecheck")
    if profile.build_command and (kind in {"deployment", "ui", "refactor", "database", "security"} or risk >= 5):
        base.append("run_build")
    if profile.lint_command and (len(profile.changed_files) >= 4 or risk >= 5):
        base.append("run_lint")

    base.append("review_diff")
    if kind == "deployment" and risk >= 5:
        base.append("verify_production")
    base.append("stop_when_requirements_are_verified")
    return tuple(dict.fromkeys(base))


def policy_for_scores(complexity: int, risk: int) -> dict[str, object]:
    if complexity <= 2 and risk <= 3:
        return {
            "strategy": "single_turn",
            "routed_agent": "guard_fast",
            "routed_model": "gpt-5.6-luna",
            "routed_reasoning": "low",
            "context_budget": 8_000,
            "max_turns": 2,
            "max_retries": 1,
            "max_actions": 6,
        }
    if complexity <= 5 and risk <= 5:
        return {
            "strategy": "single_agent",
            "routed_agent": "guard_worker",
            "routed_model": "gpt-5.6-terra",
            "routed_reasoning": "medium",
            "context_budget": 14_000,
            "max_turns": 4,
            "max_retries": 2,
            "max_actions": 10,
        }
    if complexity <= 7 and risk <= 7:
        return {
            "strategy": "bounded_agent_loop",
            "routed_agent": "guard_worker",
            "routed_model": "gpt-5.6-terra",
            "routed_reasoning": "high",
            "context_budget": 20_000,
            "max_turns": 5,
            "max_retries": 2,
            "max_actions": 14,
        }
    return {
        "strategy": "plan_execute_verify",
        "routed_agent": "guard_reasoner",
        "routed_model": "gpt-5.6",
        "routed_reasoning": "high",
        "context_budget": 28_000,
        "max_turns": 6,
        "max_retries": 2,
        "max_actions": 16,
    }


def classify_task(
    task: str,
    repo_path: str | Path = ".",
    *,
    route_models: bool = False,
) -> GuardPlan:
    profile = inspect_repo(repo_path)
    text = " ".join(task.lower().split())
    complexity = 1
    risk = 1
    reasons: list[str] = []

    if len(task) > 240:
        complexity += 1
        reasons.append("long task description")
    if sum(text.count(joiner) for joiner in (" and ", " then ", " also ")) >= 1:
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

    if profile.tracked_files >= 1500:
        complexity += 1
        reasons.append("large repository")
    if len(profile.changed_files) >= 10:
        complexity += 1
        reasons.append("many changed files already present")
    if profile.changed_lines >= 500:
        complexity += 2
        reasons.append("large existing diff")
    elif profile.changed_lines >= 150:
        complexity += 1
        reasons.append("moderate existing diff")

    if profile.sensitive_files:
        complexity += 1
        risk += 2
        reasons.append("sensitive paths changed")

    if profile.docs_only:
        complexity = min(complexity, 2)
        risk = min(risk, 2)
        reasons.append("documentation-only change")

    complexity = max(1, min(10, complexity))
    risk = max(1, min(10, risk))
    kind = _detect_kind(text, profile)

    policy = policy_for_scores(complexity, risk)
    strategy = str(policy["strategy"])
    routed_agent = str(policy["routed_agent"])
    routed_model = str(policy["routed_model"])
    routed_reasoning = str(policy["routed_reasoning"])
    context_budget = int(policy["context_budget"])
    max_turns = int(policy["max_turns"])
    max_retries = int(policy["max_retries"])
    max_actions = int(policy["max_actions"])

    if route_models:
        agent = routed_agent
        model = routed_model
        reasoning = routed_reasoning
    else:
        agent = "current_session"
        model = "current"
        reasoning = "current"
        reasons.append("current Codex session preserved; model routing is opt-in")

    requires_tests = bool(profile.test_command and not profile.docs_only)
    requires_build = bool(
        profile.build_command
        and not profile.docs_only
        and (kind in {"deployment", "ui", "refactor", "database", "security"} or risk >= 5)
    )
    requires_lint = bool(profile.lint_command and not profile.docs_only and (len(profile.changed_files) >= 4 or risk >= 5))

    return GuardPlan(
        task=task,
        task_kind=kind,
        complexity=complexity,
        risk=risk,
        strategy=strategy,
        agent_profile=agent,
        preferred_model=model,
        reasoning_effort=reasoning,
        context_budget_tokens=context_budget,
        max_model_turns=max_turns,
        max_retries=max_retries,
        max_actions=max_actions,
        max_parallel_agents=1,
        requires_tests=requires_tests,
        requires_build=requires_build,
        requires_lint=requires_lint,
        predicted_steps=_steps_for(kind, profile, complexity, risk),
        repo_signals=profile.signals,
        skill_refs=tuple(recommend_skill_refs(task, profile, kind)),
        reasons=tuple(reasons[:12]),
    )
