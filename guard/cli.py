from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from . import __version__
from .action_space import build_action_space
from .budget import budget_status
from .classifier import classify_task
from .compressor import compress, estimate_tokens
from .context import make_capsule
from .executor import enforce_task, enforcement_status
from .hud import AnimatedHUD, HUDState, visual_snapshot
from .launcher import prepare_launch, preview_launch, resolve_launch_input, run_codex
from .next_action import predict_next_action
from .repo import inspect_repo
from .state import finish_task, latest_active_task_id, load_task, record_action, start_task, update_visual_state
from .telemetry import aggregate, record_compression, record_task_summary
from .ui_quality import audit_ui, design_brief, inspect_ui_context
from .usage import usage_delta, usage_snapshot
from .visualizer import can_open_window, spawn_visualizer, visualizer_command, visualizer_enabled


def _json(data: object) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False))


def _read_input(file: str | None) -> str:
    if file:
        return Path(file).read_text(encoding="utf-8", errors="replace")
    return sys.stdin.read()


def _command_version(name: str) -> str | None:
    executable = shutil.which(name)
    if not executable:
        return None
    try:
        result = subprocess.run(
            [executable, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return executable
    text = (result.stdout or result.stderr).strip()
    return text or executable


def cmd_plan(args: argparse.Namespace) -> int:
    plan = classify_task(args.task, args.repo)
    data = plan.to_dict()
    data["repo"] = inspect_repo(args.repo).to_dict()
    _json(data)
    return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    _json(inspect_repo(args.repo).to_dict())
    return 0


def cmd_start(args: argparse.Namespace) -> int:
    profile = inspect_repo(args.repo)
    plan = classify_task(args.task, args.repo)
    state = start_task(args.task, plan.to_dict(), profile)

    launched = spawn_visualizer(str(state["task_id"]))
    update_visual_state(
        str(state["task_id"]),
        phase="analyze",
        activity="inspect",
        launched=launched,
    )
    state = load_task(str(state["task_id"]))

    _json(
        {
            "task_id": state["task_id"],
            "execution_mode": state.get("execution_mode", "current-session"),
            "plan": state["plan"],
            "repo": state["repo"],
            "budget": budget_status(state),
            "usage_before": (state.get("usage") or {}).get("baseline"),
            "visualizer_started": launched,
        }
    )
    return 0


def cmd_record(args: argparse.Namespace) -> int:
    result = record_action(
        args.task_id,
        action=args.action,
        kind=args.kind,
        outcome=args.outcome,
        details=args.details or "",
        retry=args.retry,
    )
    _json(result)
    return 0 if result.get("recorded") else 2


def cmd_capsule(args: argparse.Namespace) -> int:
    _json(make_capsule(args.task_id))
    return 0


def cmd_budget(args: argparse.Namespace) -> int:
    _json(budget_status(load_task(args.task_id)))
    return 0


def _resolve_active_task_id(task_id: str | None, repo: str) -> str:
    if task_id:
        return task_id
    profile = inspect_repo(repo)
    resolved = latest_active_task_id(profile.root)
    if not resolved:
        raise FileNotFoundError(f"no active guarded task found for {profile.root}")
    return resolved


def _status_payload(state: dict[str, object], *, include_routing: bool = False) -> dict[str, object]:
    baseline = (state.get("usage") or {}).get("baseline") or {}
    current = usage_snapshot(
        thread_id=os.environ.get("CODEX_THREAD_ID") or baseline.get("thread_id"),
        repo_root=state.get("repo_root"),
    )
    payload: dict[str, object] = {
        "task_id": state.get("task_id"),
        "status": state.get("status"),
        "objective": state.get("objective"),
        "repo_root": state.get("repo_root"),
        "execution_mode": state.get("execution_mode", "current-session"),
        "task_kind": state.get("plan", {}).get("task_kind"),
        "strategy": state.get("plan", {}).get("strategy"),
        "budget": budget_status(state),
        "usage": {
            "before": baseline,
            "current": current,
            "delta": usage_delta(baseline, current),
        },
        "verification": {
            "test": state.get("repo", {}).get("test_command"),
            "build": state.get("repo", {}).get("build_command"),
            "lint": state.get("repo", {}).get("lint_command"),
            "typecheck": state.get("repo", {}).get("typecheck_command"),
        },
        "skill_refs": state.get("plan", {}).get("skill_refs", []),
        "visual": state.get("visual"),
    }
    if include_routing:
        payload["advanced_routing"] = enforcement_status(state)
    return payload


def cmd_status(args: argparse.Namespace) -> int:
    task_id = _resolve_active_task_id(args.task_id, args.repo)
    state = load_task(task_id)
    if args.json:
        _json(_status_payload(state, include_routing=args.debug_routing))
    else:
        print(visual_snapshot(state))
    return 0


def cmd_usage(args: argparse.Namespace) -> int:
    profile = inspect_repo(args.repo)
    _json(usage_snapshot(repo_root=profile.root))
    return 0


def cmd_ui_context(args: argparse.Namespace) -> int:
    _json(inspect_ui_context(args.repo))
    return 0


def cmd_ui_brief(args: argparse.Namespace) -> int:
    _json(design_brief(args.task, args.repo))
    return 0


def cmd_ui_audit(args: argparse.Namespace) -> int:
    result = audit_ui(args.repo, max_files=args.max_files)
    if args.json:
        _json(result)
    else:
        counts = result["counts"]
        print(
            f"UI quality: {counts['blocker']} blocker / "
            f"{counts['important']} important / {counts['polish']} polish "
            f"across {result['files_scanned']} file(s)"
        )
        for item in result["findings"]:
            print(
                f"{item['severity'].upper():9} {item['path']}:{item['line']} "
                f"[{item['rule']}] {item['message']}"
            )
    if args.strict and not result["passes_strict_gate"]:
        return 2
    return 0


def cmd_enforce(args: argparse.Namespace) -> int:
    state = load_task(args.task_id)
    plan = state.get("plan", {})
    budget = budget_status(state)
    initial = enforcement_status(state)
    hud_state = HUDState(
        phase="execute",
        coordinator_model=initial.get("coordinator_model"),
        requested_model=initial.get("requested_model") or plan.get("preferred_model"),
        reasoning=initial.get("requested_reasoning") or plan.get("reasoning_effort"),
        action_used=budget["used"]["actions"],
        action_limit=budget["limits"]["actions"],
        model_turns_used=budget["used"]["model_turns"],
        model_turns_limit=budget["limits"]["model_turns"],
        judge_used=bool(state.get("judgement")),
    )
    graphical_expected = (
        not args.json
        and os.environ.get("CODEX_USAGE_GUARD_DISABLE_VISUAL") != "1"
        and can_open_window()
    )
    hud = AnimatedHUD(hud_state, enabled=False if (args.json or graphical_expected) else None)
    hud.start()
    try:
        result = enforce_task(
            args.task_id,
            force_worker=args.force_worker,
            timeout_seconds=args.timeout,
        )
    finally:
        final_state = load_task(args.task_id)
        execution = final_state.get("execution") or {}
        worker_usage = execution.get("worker_usage") or {}
        tokens = worker_usage.get("tokens_total")
        hud_state.phase = "verify"
        hud.stop(
            final_status=execution.get("status"),
            tokens=tokens if isinstance(tokens, int) else None,
        )

    if args.json:
        _json(result)
    else:
        visual = final_state.get("visual") or {}
        if not visual.get("launched") and not hud.enabled:
            print(visual_snapshot(final_state))
    return 0 if result.get("status") in {"parent-match", "verified"} else 3


def cmd_finish(args: argparse.Namespace) -> int:
    state = finish_task(args.task_id, status=args.status)
    record_task_summary(
        args.task_id,
        status=args.status,
        counters=state.get("counters", {}),
    )
    _json(
        {
            "task_id": args.task_id,
            "status": args.status,
            "execution_mode": state.get("execution_mode", "current-session"),
            "budget": budget_status(state),
            "compression": aggregate(task_id=args.task_id),
            "usage": state.get("usage"),
            "verification": {
                "test": state.get("repo", {}).get("test_command"),
                "build": state.get("repo", {}).get("build_command"),
                "lint": state.get("repo", {}).get("lint_command"),
                "typecheck": state.get("repo", {}).get("typecheck_command"),
            },
        }
    )
    return 0


def cmd_compress(args: argparse.Namespace) -> int:
    original = _read_input(args.file)
    compacted = compress(original, args.type)
    if args.no_telemetry:
        before = estimate_tokens(original)
        after = estimate_tokens(compacted)
        event = {
            "estimated_tokens_before": before,
            "estimated_tokens_after": after,
            "estimated_tokens_avoided": max(0, before - after),
        }
    else:
        event = record_compression(original, compacted, kind=args.type, task_id=args.task_id)
    if args.json:
        _json({"text": compacted, "telemetry": event})
    else:
        print(compacted)
    return 0


def cmd_next(args: argparse.Namespace) -> int:
    state = load_task(args.task_id) if args.task_id else None
    repo_path = state.get("repo_root", args.repo) if state else args.repo
    profile = inspect_repo(repo_path)

    if state:
        plan = state.get("plan", {})
        kind = args.kind or str(plan.get("task_kind", "general"))
        retries = int(state.get("counters", {}).get("retries", 0))
        max_retries = int(plan.get("max_retries", args.max_retries))
        budget = budget_status(state)
        budget_exhausted = not budget["may_continue"]
        risk = int(plan.get("risk", 1))
    else:
        kind = args.kind or "general"
        retries = args.attempts
        max_retries = args.max_retries
        budget_exhausted = False
        risk = 1

    changed_files = args.changed_files if args.changed_files is not None else len(profile.changed_files)
    browser_available = shutil.which("browser-harness") is not None
    production_check_required = args.production_check_required or (kind == "deployment" and risk >= 5)
    action = predict_next_action(
        task_kind=kind,
        changed_files=changed_files,
        test_status=args.test_status,
        build_status=args.build_status,
        lint_status=args.lint_status,
        typecheck_status=args.typecheck_status,
        browser_status=args.browser_status,
        diff_reviewed=args.diff_reviewed,
        production_check_required=production_check_required,
        attempts=retries,
        max_retries=max_retries,
        tests_available=bool(profile.test_command),
        build_available=bool(profile.build_command),
        lint_available=bool(profile.lint_command),
        typecheck_available=bool(profile.typecheck_command),
        browser_available=browser_available,
        docs_only=profile.docs_only,
        sensitive_change=bool(profile.sensitive_files),
        budget_exhausted=budget_exhausted,
    )
    data = action.to_dict()
    data["recommended_commands"] = {
        "test": profile.test_command,
        "build": profile.build_command,
        "lint": profile.lint_command,
        "typecheck": profile.typecheck_command,
        "browser_harness": "browser-harness" if browser_available else None,
    }
    data["action_space"] = build_action_space(
        task_kind=kind,
        changed_files=changed_files,
        test_status=args.test_status,
        build_status=args.build_status,
        lint_status=args.lint_status,
        typecheck_status=args.typecheck_status,
        browser_status=args.browser_status,
        diff_reviewed=args.diff_reviewed,
        tests_available=bool(profile.test_command),
        build_available=bool(profile.build_command),
        lint_available=bool(profile.lint_command),
        typecheck_available=bool(profile.typecheck_command),
        browser_available=browser_available,
        docs_only=profile.docs_only,
        production_check_required=production_check_required,
    )
    if state:
        data["budget"] = budget_status(state)
    _json(data)
    return 0


def cmd_launch(args: argparse.Namespace) -> int:
    repo_root, task = resolve_launch_input(args.items, args.repo)
    if not task:
        if not sys.stdin.isatty():
            print("A task is required when input is non-interactive.", file=sys.stderr)
            return 2
        try:
            task = input("What should Codex do? ").strip()
        except (EOFError, KeyboardInterrupt):
            print("")
            return 130
        if not task:
            print("No task supplied.", file=sys.stderr)
            return 2

    if args.dry_run:
        _json(preview_launch(task, repo_root))
        return 0

    spec = prepare_launch(task, repo_root)
    limits = spec.budget.get("limits", {})
    print(f"Codex Usage Guard {__version__}")
    print(f"Project:   {spec.repo_root}")
    print(f"Task ID:   {spec.task_id}")
    print(f"Route:     {spec.preferred_model} / {spec.reasoning_effort}")
    print(f"Profile:   {spec.agent_profile}")
    print(
        "Budget:    "
        f"{limits.get('actions', '?')} actions / "
        f"{limits.get('model_turns', '?')} model turns / "
        f"{limits.get('retries', '?')} retries"
    )
    print("Launching Codex with the selected model before the first turn...")
    return run_codex(spec)


def cmd_stats(args: argparse.Namespace) -> int:
    _json(aggregate(task_id=args.task_id))
    return 0


def cmd_doctor(_: argparse.Namespace) -> int:
    python_ok = sys.version_info >= (3, 10)
    git_version = _command_version("git")
    codex_version = _command_version("codex")
    browser_harness_version = _command_version("browser-harness")
    visual_command = visualizer_command("__doctor__")
    visual_backend = None
    if visual_command:
        first = Path(visual_command[0]).name.lower()
        visual_backend = "tauri" if "usage-guard-visualizer" in first else "tkinter"
    checks = {
        "usage_guard_version": __version__,
        "python": sys.version.split()[0],
        "python_supported": python_ok,
        "git": git_version,
        "codex": codex_version,
        "browser_harness": browser_harness_version,
        "browser_use_cloud_configured": bool(os.environ.get("BROWSER_USE_API_KEY")),
        "visualizer_backend": visual_backend,
        "compiled_visualizer_available": visual_backend == "tauri",
        "graphical_visualizer_enabled": visualizer_enabled(),
        "graphical_visualizer_autostart": False,
        "ready": bool(python_ok and git_version and codex_version),
    }
    _json(checks)
    return 0 if checks["ready"] else 1


def cmd_version(_: argparse.Namespace) -> int:
    print(__version__)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="codex-usage-guard", description="Usage-aware control plane for Codex")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("plan", help="classify a task and emit a repo-aware usage budget")
    p.add_argument("--task", required=True)
    p.add_argument("--repo", default=".")
    p.set_defaults(func=cmd_plan)

    i = sub.add_parser("inspect", help="inspect repository signals without a model call")
    i.add_argument("--repo", default=".")
    i.set_defaults(func=cmd_inspect)

    s = sub.add_parser("start", help="start a persistent guarded task")
    s.add_argument("--task", required=True)
    s.add_argument("--repo", default=".")
    s.set_defaults(func=cmd_start)

    r = sub.add_parser("record", help="record one guarded action and enforce budgets")
    r.add_argument("--task-id", required=True)
    r.add_argument("--action", required=True)
    r.add_argument("--kind", choices=("deterministic", "model"), default="deterministic")
    r.add_argument("--outcome", choices=("info", "pass", "fail"), default="info")
    r.add_argument("--details")
    r.add_argument("--retry", action="store_true")
    r.set_defaults(func=cmd_record)

    cp = sub.add_parser("capsule", help="emit Hot/Warm/Cold context state for a task")
    cp.add_argument("--task-id", required=True)
    cp.set_defaults(func=cmd_capsule)

    b = sub.add_parser("budget", help="show remaining action/model/retry budget")
    b.add_argument("--task-id", required=True)
    b.set_defaults(func=cmd_budget)

    status = sub.add_parser("status", help="show route, budget, verification, and before/after Codex usage")
    status.add_argument("--task-id")
    status.add_argument("--repo", default=".")
    status.add_argument("--json", action="store_true", help="emit machine-readable JSON instead of the visual HUD")
    status.add_argument("--debug-routing", action="store_true", help="include advanced opt-in model-routing diagnostics")
    status.set_defaults(func=cmd_status)

    usage = sub.add_parser("usage", help="read current Codex token/rate-limit telemetry locally")
    usage.add_argument("--repo", default=".")
    usage.set_defaults(func=cmd_usage)

    ui_context = sub.add_parser("ui-context", help="inspect the repository's existing UI styling and component system")
    ui_context.add_argument("--repo", default=".")
    ui_context.set_defaults(func=cmd_ui_context)

    ui_brief = sub.add_parser("ui-brief", help="derive the visual ambition and design-quality gate for a UI task")
    ui_brief.add_argument("--task", required=True)
    ui_brief.add_argument("--repo", default=".")
    ui_brief.set_defaults(func=cmd_ui_brief)

    ui_audit = sub.add_parser("ui-audit", help="run a deterministic audit for common UI/accessibility quality regressions")
    ui_audit.add_argument("--repo", default=".")
    ui_audit.add_argument("--max-files", type=int, default=200)
    ui_audit.add_argument("--strict", action="store_true", help="exit non-zero when important/blocker findings remain")
    ui_audit.add_argument("--json", action="store_true", help="emit machine-readable findings")
    ui_audit.set_defaults(func=cmd_ui_audit)

    enforce = sub.add_parser("enforce", help="enforce the selected model/reasoning with a pinned Codex exec worker when needed")
    enforce.add_argument("--task-id", required=True)
    enforce.add_argument("--force-worker", action="store_true")
    enforce.add_argument("--timeout", type=int, default=1800)
    enforce.add_argument("--json", action="store_true", help="emit machine-readable JSON and disable animation")
    enforce.set_defaults(func=cmd_enforce)

    fn = sub.add_parser("finish", help="close a guarded task and write summary telemetry")
    fn.add_argument("--task-id", required=True)
    fn.add_argument("--status", choices=("completed", "blocked", "abandoned"), default="completed")
    fn.set_defaults(func=cmd_finish)

    c = sub.add_parser("compress", help="compress verbose tool output locally")
    c.add_argument("--type", choices=("test", "git", "log", "generic"), default="generic")
    c.add_argument("--file")
    c.add_argument("--task-id")
    c.add_argument("--json", action="store_true")
    c.add_argument("--no-telemetry", action="store_true")
    c.set_defaults(func=cmd_compress)

    n = sub.add_parser("next", help="predict the cheapest useful next action")
    n.add_argument("--task-id")
    n.add_argument("--repo", default=".")
    n.add_argument("--kind")
    n.add_argument("--changed-files", type=int)
    n.add_argument("--test-status", choices=("not-run", "pass", "fail", "not-needed"), default="not-run")
    n.add_argument("--build-status", choices=("not-run", "pass", "fail", "not-needed"), default="not-run")
    n.add_argument("--lint-status", choices=("not-run", "pass", "fail", "not-needed"), default="not-run")
    n.add_argument("--typecheck-status", choices=("not-run", "pass", "fail", "not-needed"), default="not-run")
    n.add_argument("--browser-status", choices=("not-run", "pass", "fail", "not-needed"), default="not-run")
    n.add_argument("--diff-reviewed", action="store_true")
    n.add_argument("--production-check-required", action="store_true")
    n.add_argument("--attempts", type=int, default=0)
    n.add_argument("--max-retries", type=int, default=2)
    n.set_defaults(func=cmd_next)

    launch = sub.add_parser("launch", help="classify locally, then launch Codex with the selected model and reasoning")
    launch.add_argument("items", nargs="*", help="task text; an explicit existing directory may be supplied first")
    launch.add_argument("--repo", default=".", help="project directory; defaults to the current directory")
    launch.add_argument("--dry-run", action="store_true", help="show the selected route without starting Codex or creating task state")
    launch.set_defaults(func=cmd_launch)

    st = sub.add_parser("stats", help="show local compression telemetry")
    st.add_argument("--task-id")
    st.set_defaults(func=cmd_stats)

    d = sub.add_parser("doctor", help="check versions and local prerequisites")
    d.set_defaults(func=cmd_doctor)

    v = sub.add_parser("version", help="print Codex Usage Guard version")
    v.set_defaults(func=cmd_version)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
