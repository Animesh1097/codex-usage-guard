from __future__ import annotations

from typing import Any


def build_action_space(
    *,
    task_kind: str,
    changed_files: int,
    test_status: str,
    build_status: str,
    lint_status: str,
    typecheck_status: str,
    browser_status: str,
    diff_reviewed: bool,
    tests_available: bool,
    build_available: bool,
    lint_available: bool,
    typecheck_available: bool,
    browser_available: bool,
    docs_only: bool,
    production_check_required: bool,
) -> list[dict[str, Any]]:
    """Return only actions that are valid in the current state.

    The list is deliberately small and state-derived. It is an indexed action
    space, not a free-form plan, so the model sees fewer irrelevant choices.
    """
    actions: list[tuple[str, str, bool]] = []

    if changed_files <= 0:
        actions.append(("INSPECT", "inspect the minimum relevant code before editing", True))
    else:
        if test_status == "fail":
            actions.append(("INSPECT_TEST_FAILURE", "diagnose the exact failing test", True))
        elif tests_available and test_status == "not-run" and not docs_only:
            actions.append(("TEST", "run the detected targeted test command", True))

        if typecheck_status == "fail":
            actions.append(("INSPECT_TYPECHECK_FAILURE", "diagnose the exact type error", True))
        elif typecheck_available and typecheck_status == "not-run" and not docs_only:
            actions.append(("TYPECHECK", "run the detected typecheck command", True))

        if build_status == "fail":
            actions.append(("INSPECT_BUILD_FAILURE", "diagnose the exact build error", True))
        elif (
            build_available
            and build_status == "not-run"
            and not docs_only
            and task_kind in {"deployment", "ui", "refactor", "database", "security"}
        ):
            actions.append(("BUILD", "run the detected build command", True))

        if lint_status == "fail":
            actions.append(("INSPECT_LINT_FAILURE", "diagnose concrete lint diagnostics", True))
        elif lint_available and lint_status == "not-run" and not docs_only and changed_files >= 4:
            actions.append(("LINT", "run the detected lint command", True))

        if browser_available and task_kind == "ui" and browser_status == "not-run":
            actions.append(("BROWSER_VERIFY", "verify the rendered UI in a real browser", True))

        if not diff_reviewed:
            actions.append(("DIFF_REVIEW", "review final scope and accidental edits", True))

    verification_pending = any(
        status in {"not-run", "fail"}
        for status in (
            test_status if tests_available and not docs_only else "not-needed",
            typecheck_status if typecheck_available and not docs_only else "not-needed",
            build_status
            if build_available and not docs_only and task_kind in {"deployment", "ui", "refactor", "database", "security"}
            else "not-needed",
            browser_status if browser_available and task_kind == "ui" else "not-needed",
        )
    )
    if changed_files > 0 and diff_reviewed and not verification_pending and not production_check_required:
        actions.append(("DONE", "requirements have independent verification and the diff is reviewed", True))

    if production_check_required and changed_files > 0:
        actions.append(("PRODUCTION_VERIFY", "verify the changed production path", True))

    actions.append(("BLOCKED", "stop with exact unresolved evidence when progress is not justified", True))

    return [
        {"index": index, "operation": op, "reason": reason, "deterministic": deterministic}
        for index, (op, reason, deterministic) in enumerate(actions, start=1)
    ]
