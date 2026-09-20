from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence

from .budget import budget_status
from .classifier import classify_task
from .repo import inspect_repo
from .state import start_task


@dataclass(frozen=True)
class LaunchSpec:
    task_id: str
    task: str
    repo_root: str
    agent_profile: str
    preferred_model: str
    reasoning_effort: str
    budget: dict[str, Any]
    verification: dict[str, str | None]
    command: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["command"] = list(self.command)
        return data


def resolve_launch_input(items: Sequence[str], repo: str | Path = ".") -> tuple[Path, str]:
    parts = [str(item) for item in items]
    repo_path = Path(repo).expanduser()

    if str(repo) == "." and parts:
        first = parts[0]
        candidate = Path(first).expanduser()
        looks_explicit = any(sep in first for sep in ("/", "\\")) or ":" in first or first.startswith(".")
        if candidate.is_dir() and (len(parts) == 1 or looks_explicit):
            repo_path = candidate
            parts = parts[1:]

    profile = inspect_repo(repo_path)
    task = " ".join(part.strip() for part in parts if part.strip()).strip()
    return Path(profile.root), task


def preview_launch(task: str, repo: str | Path = ".") -> dict[str, Any]:
    profile = inspect_repo(repo)
    plan = classify_task(task, profile.root, route_models=True)
    return {
        "task": task,
        "repo_root": profile.root,
        "agent_profile": plan.agent_profile,
        "preferred_model": plan.preferred_model,
        "reasoning_effort": plan.reasoning_effort,
        "limits": {
            "actions": plan.max_actions,
            "model_turns": plan.max_model_turns,
            "retries": plan.max_retries,
        },
        "verification": {
            "test": profile.test_command,
            "build": profile.build_command,
            "lint": profile.lint_command,
            "typecheck": profile.typecheck_command,
        },
    }


def _guard_prompt(task_id: str, task: str) -> str:
    return (
        f"$usage-guard Continue the pre-created guarded task ID {task_id}. "
        "Do not create a second guarded task. The launcher already selected the model, "
        "reasoning effort, and repository before this Codex session started. "
        f"Objective: {task}"
    )


def build_codex_command(
    *,
    task_id: str,
    task: str,
    repo_root: str | Path,
    model: str,
    reasoning_effort: str,
    codex_executable: str = "codex",
) -> list[str]:
    return [
        codex_executable,
        "--cd",
        str(Path(repo_root)),
        "--model",
        model,
        "-c",
        f'model_reasoning_effort="{reasoning_effort}"',
        _guard_prompt(task_id, task),
    ]


def prepare_launch(task: str, repo: str | Path = ".") -> LaunchSpec:
    profile = inspect_repo(repo)
    plan = classify_task(task, profile.root, route_models=True)
    state = start_task(task, plan.to_dict(), profile)
    executable = shutil.which("codex") or "codex"
    command = build_codex_command(
        task_id=str(state["task_id"]),
        task=task,
        repo_root=profile.root,
        model=plan.preferred_model,
        reasoning_effort=plan.reasoning_effort,
        codex_executable=executable,
    )
    return LaunchSpec(
        task_id=str(state["task_id"]),
        task=task,
        repo_root=profile.root,
        agent_profile=plan.agent_profile,
        preferred_model=plan.preferred_model,
        reasoning_effort=plan.reasoning_effort,
        budget=budget_status(state),
        verification={
            "test": profile.test_command,
            "build": profile.build_command,
            "lint": profile.lint_command,
            "typecheck": profile.typecheck_command,
        },
        command=tuple(command),
    )


def run_codex(spec: LaunchSpec) -> int:
    env = os.environ.copy()
    env["CODEX_USAGE_GUARD_ACTIVE"] = "1"
    env["CODEX_USAGE_GUARD_TASK_ID"] = spec.task_id
    env["CODEX_USAGE_GUARD_REPO"] = spec.repo_root
    env["CODEX_USAGE_GUARD_MODEL"] = spec.preferred_model
    env["CODEX_USAGE_GUARD_REASONING"] = spec.reasoning_effort
    try:
        completed = subprocess.run(
            list(spec.command),
            cwd=spec.repo_root,
            env=env,
            check=False,
        )
    except OSError as exc:
        print(f"Failed to launch Codex: {exc}")
        return 2
    return int(completed.returncode)
