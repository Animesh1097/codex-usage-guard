from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from .classifier import classify_task
from .compressor import compress, estimate_tokens
from .next_action import predict_next_action
from .telemetry import aggregate, record_compression


def _json(data: object) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False))


def _read_input(file: str | None) -> str:
    if file:
        return Path(file).read_text(encoding="utf-8", errors="replace")
    return sys.stdin.read()


def cmd_plan(args: argparse.Namespace) -> int:
    _json(classify_task(args.task, args.repo).to_dict())
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
        event = record_compression(original, compacted, kind=args.type)
    if args.json:
        _json({"text": compacted, "telemetry": event})
    else:
        print(compacted)
    return 0


def cmd_next(args: argparse.Namespace) -> int:
    action = predict_next_action(
        task_kind=args.kind,
        changed_files=args.changed_files,
        test_status=args.test_status,
        build_status=args.build_status,
        lint_status=args.lint_status,
        diff_reviewed=args.diff_reviewed,
        production_check_required=args.production_check_required,
        attempts=args.attempts,
        max_retries=args.max_retries,
    )
    _json(action.to_dict())
    return 0


def cmd_stats(_: argparse.Namespace) -> int:
    _json(aggregate())
    return 0


def cmd_doctor(_: argparse.Namespace) -> int:
    checks = {
        "python": sys.executable,
        "git": shutil.which("git"),
        "codex": shutil.which("codex"),
    }
    checks["ready"] = bool(checks["python"] and checks["git"] and checks["codex"])
    _json(checks)
    return 0 if checks["ready"] else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="codex-usage-guard", description="Deterministic usage guard for Codex")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("plan", help="classify a task and emit a usage budget")
    p.add_argument("--task", required=True)
    p.add_argument("--repo", default=".")
    p.set_defaults(func=cmd_plan)

    c = sub.add_parser("compress", help="compress verbose tool output locally")
    c.add_argument("--type", choices=("test", "git", "log", "generic"), default="generic")
    c.add_argument("--file")
    c.add_argument("--json", action="store_true")
    c.add_argument("--no-telemetry", action="store_true")
    c.set_defaults(func=cmd_compress)

    n = sub.add_parser("next", help="predict the cheapest useful next action")
    n.add_argument("--kind", default="general")
    n.add_argument("--changed-files", type=int, default=0)
    n.add_argument("--test-status", choices=("not-run", "pass", "fail"), default="not-run")
    n.add_argument("--build-status", choices=("not-run", "pass", "fail", "not-needed"), default="not-run")
    n.add_argument("--lint-status", choices=("not-run", "pass", "fail", "not-needed"), default="not-run")
    n.add_argument("--diff-reviewed", action="store_true")
    n.add_argument("--production-check-required", action="store_true")
    n.add_argument("--attempts", type=int, default=0)
    n.add_argument("--max-retries", type=int, default=2)
    n.set_defaults(func=cmd_next)

    s = sub.add_parser("stats", help="show local compression telemetry")
    s.set_defaults(func=cmd_stats)

    d = sub.add_parser("doctor", help="check local prerequisites")
    d.set_defaults(func=cmd_doctor)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
