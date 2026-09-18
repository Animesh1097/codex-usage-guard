from __future__ import annotations

from .models import NextAction


def predict_next_action(
    *,
    task_kind: str,
    changed_files: int,
    test_status: str = "not-run",
    build_status: str = "not-run",
    lint_status: str = "not-run",
    diff_reviewed: bool = False,
    production_check_required: bool = False,
    attempts: int = 0,
    max_retries: int = 2,
) -> NextAction:
    if attempts > max_retries:
        return NextAction(
            "reassess_or_escalate",
            "retry budget exhausted; collect exact failure evidence before another model turn",
        )

    if changed_files <= 0:
        return NextAction("inspect_relevant_code", "no change has been made yet")

    if test_status == "fail":
        return NextAction("inspect_test_failure", "tests are failing; diagnose exact failure before editing again")
    if build_status == "fail":
        return NextAction("inspect_build_failure", "build is failing; use the exact compiler/build error")
    if lint_status == "fail":
        return NextAction("inspect_lint_failure", "lint is failing; resolve concrete diagnostics")

    if test_status == "not-run":
        return NextAction("run_targeted_tests", "deterministic verification is cheaper than another reasoning turn")

    build_kinds = {"deployment", "ui", "refactor", "database", "security"}
    if task_kind in build_kinds and build_status == "not-run":
        return NextAction("run_build", "changed code has cross-file/runtime risk and should compile before model review")

    if changed_files >= 4 and lint_status == "not-run":
        return NextAction("run_lint", "multiple files changed; lint is a low-cost verification step")

    if not diff_reviewed:
        return NextAction("review_git_diff", "verify scope and accidental edits before spending more model usage")

    if production_check_required:
        return NextAction("verify_production", "task explicitly affects production/deployment")

    return NextAction("stop", "requirements have deterministic verification and no unresolved failure", stop=True)
