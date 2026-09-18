from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from . import __version__
from .budget import budget_status
from .classifier import classify_task
from .compressor import compress, estimate_tokens
from .context import make_capsule
from .next_action import predict_next_action
from .repo import inspect_repo
from .state import finish_task, load_task, record_action, start_task
from .telemetry import aggregate, record_compression, record_task_summary


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
    _json(
        {
            "task_id": state["task_id"],
            "plan": state["plan"],
            "repo": state["repo"],
            "budget": budget_status(state),
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
            "budget": budget_status(state),
            "compression": aggregate(task_id=args.task_id),
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
    action = predict_next_action(
        task_kind=kind,
        changed_files=changed_files,
        test_status=args.test_status,
        build_status=args.build_status,
        lint_status=args.lint_status,
        typecheck_status=args.typecheck_status,
        diff_reviewed=args.diff_reviewed,
        production_check_required=args.production_check_required or (kind == "deployment" and risk >= 5),
        attempts=retries,
        max_retries=max_retries,
        tests_available=bool(profile.test_command),
        build_available=bool(profile.build_command),
        lint_available=bool(profile.lint_command),
        typecheck_available=bool(profile.typecheck_command),
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
    }
    if state:
        data["budget"] = budget_status(state)
    _json(data)
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    _json(aggregate(task_id=args.task_id))
    return 0


def cmd_doctor(_: argparse.Namespace) -> int:
    python_ok = sys.version_info >= (3, 10)
    git_version = _command_version("git")
    codex_version = _command_version("codex")
    checks = {
        "usage_guard_version": __version__,
        "python": sys.version.split()[0],
        "python_supported": python_ok,
        "git": git_version,
        "codex": codex_version,
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
    n.add_argument("--diff-reviewed", action="store_true")
    n.add_argument("--production-check-required", action="store_true")
    n.add_argument("--attempts", type=int, default=0)
    n.add_argument("--max-retries", type=int, default=2)
    n.set_defaults(func=cmd_next)

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
