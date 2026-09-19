---
name: usage-guard
description: Reduce Codex usage on coding tasks by budgeting model turns, compressing tool output, tracking task state, and choosing the cheapest useful next action.
---

# Codex Usage Guard

Treat the user's objective as the source of truth. Do not ask the user to choose a model, reasoning level, agent mode, or next step when the guard can decide.

## Start every guarded task

On Windows:

    & "$HOME\.codex-usage-guard\guard.cmd" start --task "<USER_OBJECTIVE>" --repo .

Keep the returned `task_id`. The response contains the repo-aware plan, model profile, reasoning effort, hard action/model/retry budgets, and deterministic verification commands.

Route the implementation to the selected custom agent profile when available. Give it only the objective, budget, compact state capsule, and minimum relevant repository evidence. If the selected profile/model is unavailable, keep the current Codex model but preserve the guard policy.

## Work loop

Before another model-heavy action:

    & "$HOME\.codex-usage-guard\guard.cmd" capsule --task-id <ID>

After a meaningful action, record it:

    & "$HOME\.codex-usage-guard\guard.cmd" record --task-id <ID> --action "<ACTION>" --kind <deterministic|model> --outcome <info|pass|fail>

Ask the local predictor for the cheapest useful next step:

    & "$HOME\.codex-usage-guard\guard.cmd" next --task-id <ID> [verification status flags]

If `record` rejects an action because a budget is exhausted, do not bypass it automatically. Reassess the hypothesis and only escalate when new evidence justifies another Codex turn.

Use only verification commands reported by the guard's repo inspection or commands explicitly present in the repository configuration/CI. Never invent npm, Python, Rust, Go, Java, build, lint, or test commands. If no verification command is detected, inspect the minimum relevant project configuration before choosing one.

Compress noisy command output locally before it re-enters context. Replace <DETECTED_TEST_COMMAND> with the actual command discovered for this repository:

    <DETECTED_TEST_COMMAND> 2>&1 | & "$HOME\.codex-usage-guard\guard.cmd" compress --type test --task-id <ID>
    git diff 2>&1 | & "$HOME\.codex-usage-guard\guard.cmd" compress --type git --task-id <ID>

## Finish

Verify requirements and final diff, then:

    & "$HOME\.codex-usage-guard\guard.cmd" finish --task-id <ID> --status completed

Keep the user-facing report short: what changed, what was verified, and unresolved risks.

Read the reference files only when needed:
- `references/routing.md` for escalation and subagent rules.
- `references/verification.md` for choosing checks.
- `references/context.md` for Hot/Warm/Cold context handling.

Never claim estimated context reduction equals the same percentage of Codex allowance saved.
