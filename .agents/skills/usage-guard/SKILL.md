---
name: usage-guard
description: Conserve Codex allowance while completing coding tasks. Use for implementation, debugging, refactoring, deployment checks, or repository investigation when context, retries, reasoning effort, model choice, and unnecessary agent loops should be minimized.
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

Compress noisy command output locally before it re-enters context:

    npm test 2>&1 | & "$HOME\.codex-usage-guard\guard.cmd" compress --type test --task-id <ID>
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
