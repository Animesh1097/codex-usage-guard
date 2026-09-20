from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .budget import assert_action_allowed, budget_status
from .state import DATA_ROOT, TASKS_ROOT, load_task, record_action, save_task
from .usage import usage_snapshot


@dataclass(frozen=True)
class EnforcementDecision:
    coordinator_model: str | None
    coordinator_reasoning: str | None
    requested_model: str
    requested_reasoning: str
    requires_worker: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "coordinator_model": self.coordinator_model,
            "coordinator_reasoning": self.coordinator_reasoning,
            "requested_model": self.requested_model,
            "requested_reasoning": self.requested_reasoning,
            "requires_worker": self.requires_worker,
            "reason": self.reason,
        }


def _norm(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    return text or None


def decide_enforcement(
    *,
    coordinator_model: str | None,
    coordinator_reasoning: str | None,
    requested_model: str,
    requested_reasoning: str,
) -> EnforcementDecision:
    model_match = _norm(coordinator_model) == _norm(requested_model)
    reasoning_match = _norm(coordinator_reasoning) == _norm(requested_reasoning)
    requires_worker = not (model_match and reasoning_match)
    if not model_match:
        reason = "coordinator model differs from selected route"
    elif not reasoning_match:
        reason = "coordinator reasoning differs from selected route"
    else:
        reason = "coordinator already matches selected model and reasoning"
    return EnforcementDecision(
        coordinator_model=coordinator_model,
        coordinator_reasoning=coordinator_reasoning,
        requested_model=requested_model,
        requested_reasoning=requested_reasoning,
        requires_worker=requires_worker,
        reason=reason,
    )


def _worker_prompt(state: dict[str, Any]) -> str:
    plan = state.get("plan", {})
    repo = state.get("repo", {})
    verification = {
        "test": repo.get("test_command"),
        "build": repo.get("build_command"),
        "lint": repo.get("lint_command"),
        "typecheck": repo.get("typecheck_command"),
    }
    refs = plan.get("skill_refs") or []
    skill_root = Path(__file__).resolve().parents[1] / ".agents" / "skills" / "usage-guard"
    ref_paths = [str(skill_root / str(item).removeprefix("references/")) for item in refs]
    refs_text = ", ".join(ref_paths) if ref_paths else "none"
    return (
        "You are the single pinned execution worker for Codex Usage Guard. "
        "Do not invoke $usage-guard, do not spawn subagents, and do not change the requested model. "
        "Work directly in the current repository. Preserve unrelated user changes. "
        "Use the minimum repository context needed. "
        f"Objective: {state.get('objective', '')}\n"
        f"Task kind: {plan.get('task_kind', 'general')}. "
        f"Context budget target: {plan.get('context_budget_tokens', 'unknown')} tokens. "
        f"Relevant craft reference files selected by the guard: {refs_text}. "
        "Read only those reference files when they exist, then apply their principles. Do not load unrelated guides. "
        f"Detected verification commands: {json.dumps(verification, ensure_ascii=False)}. "
        "Do not invent verification commands. "
        "Make the smallest complete change, run only justified deterministic checks, review the final diff, "
        "and stop when the objective is verified. In the final response, state what changed, what was verified, "
        "and any unresolved issue."
    )


def build_exec_command(
    *,
    task_id: str,
    repo_root: str | Path,
    model: str,
    reasoning_effort: str,
    prompt: str,
    output_file: str | Path,
    codex_executable: str = "codex",
) -> list[str]:
    command = [
        codex_executable,
        "exec",
        "--json",
        "--color",
        "never",
        "--cd",
        str(Path(repo_root)),
        "--model",
        model,
        "--sandbox",
        "workspace-write",
        "--config",
        f'model_reasoning_effort="{reasoning_effort}"',
        "--config",
        'approval_policy="never"',
        "--output-last-message",
        str(Path(output_file)),
    ]
    if not (Path(repo_root) / ".git").exists():
        command.append("--skip-git-repo-check")
    command.append(prompt)
    return command


def parse_thread_id(output: str) -> str | None:
    thread_id: str | None = None
    for raw in output.splitlines():
        try:
            event = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "thread.started":
            value = event.get("thread_id")
            if isinstance(value, str) and value:
                thread_id = value
    return thread_id


def _coordinator_snapshot(state: dict[str, Any]) -> dict[str, Any]:
    baseline = (state.get("usage") or {}).get("baseline") or {}
    thread_id = os.environ.get("CODEX_THREAD_ID") or baseline.get("thread_id")
    if thread_id == "__usage_guard_pending_thread__":
        thread_id = None
    return usage_snapshot(thread_id=thread_id, repo_root=state.get("repo_root"))


def enforcement_status(state: dict[str, Any]) -> dict[str, Any]:
    plan = state.get("plan", {})
    requested_model = str(plan.get("preferred_model") or "")
    requested_reasoning = str(plan.get("reasoning_effort") or "")
    coordinator = _coordinator_snapshot(state)
    decision = decide_enforcement(
        coordinator_model=coordinator.get("model"),
        coordinator_reasoning=coordinator.get("reasoning_effort"),
        requested_model=requested_model,
        requested_reasoning=requested_reasoning,
    )
    execution = state.get("execution")
    if isinstance(execution, dict) and execution:
        return execution
    return {
        **decision.to_dict(),
        "status": "pending-worker" if decision.requires_worker else "parent-match",
        "executed": False,
        "effective_model": coordinator.get("model") if not decision.requires_worker else None,
        "effective_reasoning": coordinator.get("reasoning_effort") if not decision.requires_worker else None,
    }


def enforce_task(
    task_id: str,
    *,
    force_worker: bool = False,
    timeout_seconds: int = 1800,
    root: Path = TASKS_ROOT,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    sleep_fn: Callable[[float], None] = time.sleep,
    codex_executable: str | None = None,
) -> dict[str, Any]:
    state = load_task(task_id, root=root)
    plan = state.get("plan", {})
    requested_model = str(plan.get("preferred_model") or "")
    requested_reasoning = str(plan.get("reasoning_effort") or "")
    coordinator = _coordinator_snapshot(state)
    decision = decide_enforcement(
        coordinator_model=coordinator.get("model"),
        coordinator_reasoning=coordinator.get("reasoning_effort"),
        requested_model=requested_model,
        requested_reasoning=requested_reasoning,
    )

    if not decision.requires_worker and not force_worker:
        execution = {
            **decision.to_dict(),
            "status": "parent-match",
            "executed": False,
            "effective_model": coordinator.get("model"),
            "effective_reasoning": coordinator.get("reasoning_effort"),
            "worker_thread_id": None,
            "observed_worker_model": None,
            "observed_worker_reasoning": None,
            "worker_usage": None,
            "exit_code": None,
            "final_message": None,
        }
        state["execution"] = execution
        save_task(state, root=root)
        return execution

    allowed, reason = assert_action_allowed(state, kind="model")
    if not allowed:
        execution = {
            **decision.to_dict(),
            "status": "budget-blocked",
            "executed": False,
            "effective_model": None,
            "effective_reasoning": None,
            "worker_thread_id": None,
            "observed_worker_model": None,
            "observed_worker_reasoning": None,
            "worker_usage": None,
            "exit_code": None,
            "final_message": None,
            "error": reason,
            "budget": budget_status(state),
        }
        state["execution"] = execution
        save_task(state, root=root)
        return execution

    executable = codex_executable or shutil.which("codex") or "codex"
    worker_root = DATA_ROOT / "workers"
    worker_root.mkdir(parents=True, exist_ok=True)
    output_file = worker_root / f"{task_id}.last.txt"
    try:
        output_file.unlink(missing_ok=True)
    except OSError:
        pass

    command = build_exec_command(
        task_id=task_id,
        repo_root=str(state.get("repo_root")),
        model=requested_model,
        reasoning_effort=requested_reasoning,
        prompt=_worker_prompt(state),
        output_file=output_file,
        codex_executable=executable,
    )

    env = os.environ.copy()
    for key in list(env):
        if key == "CODEX_THREAD_ID" or key.startswith("CODEX_USAGE_GUARD_"):
            env.pop(key, None)
    env["CODEX_USAGE_GUARD_PINNED_WORKER"] = "1"

    try:
        completed = runner(
            command,
            cwd=str(state.get("repo_root")),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        exit_code = int(completed.returncode)
    except (OSError, subprocess.SubprocessError) as exc:
        stdout = ""
        stderr = str(exc)
        exit_code = 2

    worker_thread_id = parse_thread_id(stdout)
    worker_usage: dict[str, Any] | None = None
    if worker_thread_id:
        for _ in range(20):
            candidate = usage_snapshot(thread_id=worker_thread_id, repo_root=str(state.get("repo_root")))
            if candidate.get("model") and candidate.get("reasoning_effort"):
                worker_usage = candidate
                break
            worker_usage = candidate
            sleep_fn(0.1)

    observed_model = worker_usage.get("model") if worker_usage else None
    observed_reasoning = worker_usage.get("reasoning_effort") if worker_usage else None
    model_match = _norm(observed_model) == _norm(requested_model)
    reasoning_match = _norm(observed_reasoning) == _norm(requested_reasoning)

    if exit_code != 0:
        route_status = "failed"
    elif not worker_thread_id:
        route_status = "unverified-no-thread"
    elif observed_model is None or observed_reasoning is None:
        route_status = "unverified"
    elif not model_match:
        route_status = "model-mismatch"
    elif not reasoning_match:
        route_status = "reasoning-mismatch"
    else:
        route_status = "verified"

    final_message: str | None = None
    try:
        if output_file.exists():
            final_message = output_file.read_text(encoding="utf-8", errors="replace").strip()[:6000] or None
    except OSError:
        final_message = None

    outcome = "pass" if route_status == "verified" else "fail"
    record_action(
        task_id,
        action="pinned execution worker",
        kind="model",
        outcome=outcome,
        details=(
            f"requested={requested_model}/{requested_reasoning}; "
            f"observed={observed_model}/{observed_reasoning}; "
            f"route_status={route_status}; exit_code={exit_code}"
        ),
        root=root,
    )

    state = load_task(task_id, root=root)
    execution = {
        **decision.to_dict(),
        "status": route_status,
        "executed": True,
        "effective_model": observed_model if route_status == "verified" else None,
        "effective_reasoning": observed_reasoning if route_status == "verified" else None,
        "worker_thread_id": worker_thread_id,
        "observed_worker_model": observed_model,
        "observed_worker_reasoning": observed_reasoning,
        "worker_usage": worker_usage,
        "exit_code": exit_code,
        "final_message": final_message,
        "stderr_excerpt": stderr[-2000:] if stderr else None,
    }
    state["execution"] = execution
    save_task(state, root=root)
    return execution
