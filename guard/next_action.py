from __future__ import annotations

from .models import NextAction


def predict_next_action(
    *,
    task_kind: str,
    changed_files: int,
    test_status: str = "not-run",
    build_status: str = "not-run",
    lint_status: str = "not-run",
    typecheck_status: str = "not-run",
    diff_reviewed: bool = False,
    production_check_required: bool = False,
    attempts: int = 0,
    max_retries: int = 2,
    tests_available: bool = True,
    build_available: bool = False,
    lint_available: bool = False,
    typecheck_available: bool = False,
    docs_only: bool = False,
    sensitive_change: bool = False,
    budget_exhausted: bool = False,
) -> NextAction:
    if budget_exhausted:
        return NextAction(
            "reassess_or_escalate",
            "action/model budget is exhausted; collect exact evidence and change strategy before another Codex turn",
        )

    if attempts >= max_retries and max_retries >= 0:
        return NextAction(
            "reassess_or_escalate",
            "retry budget exhausted; collect exact failure evidence before another model turn",
        )

    if changed_files <= 0:
        return NextAction("inspect_relevant_code", "no change has been made yet")

    if test_status == "fail":
        return NextAction("inspect_test_failure", "tests are failing; diagnose exact failure before editing again")
    if typecheck_status == "fail":
        return NextAction("inspect_typecheck_failure", "type checking failed; use the exact diagnostic before another edit")
    if build_status == "fail":
        return NextAction("inspect_build_failure", "build is failing; use the exact compiler/build error")
    if lint_status == "fail":
        return NextAction("inspect_lint_failure", "lint is failing; resolve concrete diagnostics")

    if docs_only:
        if not diff_reviewed:
            return NextAction("review_git_diff", "documentation-only change needs scope review, not a model-heavy verification loop")
        return NextAction("stop", "documentation change is reviewed and has no unresolved deterministic failure", stop=True)

    if tests_available and test_status == "not-run":
        return NextAction("run_targeted_tests", "deterministic verification is cheaper than another reasoning turn")

    if typecheck_available and typecheck_status == "not-run":
        return NextAction("run_typecheck", "type checking is a low-cost deterministic check for changed code")

    build_kinds = {"deployment", "ui", "refactor", "database", "security"}
    if build_available and build_status == "not-run" and (task_kind in build_kinds or sensitive_change):
        return NextAction("run_build", "cross-file/runtime risk should compile before model review")

    if lint_available and lint_status == "not-run" and (changed_files >= 4 or sensitive_change):
        return NextAction("run_lint", "lint is a low-cost verification step for a broad or sensitive change")

    if not diff_reviewed:
        return NextAction("review_git_diff", "verify scope and accidental edits before spending more model usage")

    if production_check_required:
        return NextAction("verify_production", "task explicitly affects production/deployment")

    return NextAction("stop", "requirements have sufficient deterministic verification and no unresolved failure", stop=True)
