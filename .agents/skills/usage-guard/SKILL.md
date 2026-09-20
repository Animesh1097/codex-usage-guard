---
name: usage-guard
description: Reduce Codex usage on coding tasks with local routing, usage snapshots, bounded model turns, progressive craft references, compressed evidence, and the cheapest valid next action.
---

# Codex Usage Guard

The user should be able to stay inside Codex after the one-time install. Treat the user's objective as the source of truth. Do not ask them to choose a model, reasoning level, agent mode, verification command, or next step when the guard can decide.

## In-Codex commands

Interpret these without starting a new task:

- `$usage-guard status` -> run `guard.cmd status --repo .`
- `$usage-guard usage` -> run `guard.cmd usage --repo .`
- `$usage-guard budget` -> resolve the active task for this repo, then show its status/budget
- `$usage-guard stop` -> finish the active task as blocked or abandoned according to the user's intent

Keep the user-facing result compact. Never expose auth tokens, cookies, hidden session credentials, or raw rollout contents.

## Start a guarded task

If `CODEX_USAGE_GUARD_TASK_ID` is present, the pre-session launcher already created the task. Reuse that ID and do not call `start` again.

Otherwise on Windows:

    & "$HOME\.codex-usage-guard\guard.cmd" start --task "<USER_OBJECTIVE>" --repo .

Keep the returned `task_id`. The plan includes model/reasoning policy, budgets, verification commands, local usage baseline, and zero-to-two task-specific reference files.

Read only the reference files listed in `plan.skill_refs`. Do not load every craft guide.

Inside an already-running Codex session, the parent status-line model may not change. When the selected custom agent profile is available and its model differs from the parent, delegate the implementation to that one selected worker. Do not fan out. The parent remains coordinator only. If exact parent-session model switching is required, the optional `cguard` launcher remains available.

## Work loop

Before another model-heavy action:

    & "$HOME\.codex-usage-guard\guard.cmd" capsule --task-id <ID>

After a meaningful action:

    & "$HOME\.codex-usage-guard\guard.cmd" record --task-id <ID> --action "<ACTION>" --kind <deterministic|model> --outcome <info|pass|fail>

Ask for the cheapest valid next operation:

    & "$HOME\.codex-usage-guard\guard.cmd" next --task-id <ID> [verification status flags]

The response includes an indexed `action_space`. Treat it as the valid operation set for the current state. Do not invent an expensive extra step when a valid deterministic action is available.

If `record` rejects an action because a budget is exhausted, do not bypass it automatically. Reassess using exact evidence.

Use only verification commands reported by the guard or explicitly present in repository configuration/CI. Never invent npm, Python, Rust, Go, Java, build, lint, test, or typecheck commands.

Compress noisy output before it re-enters model context:

    <DETECTED_TEST_COMMAND> 2>&1 | & "$HOME\.codex-usage-guard\guard.cmd" compress --type test --task-id <ID>
    git diff 2>&1 | & "$HOME\.codex-usage-guard\guard.cmd" compress --type git --task-id <ID>

For UI work, if Browser Harness is already installed, prefer real-browser verification before declaring success. Browser Use Cloud is optional and must only be used when the user opted in and `BROWSER_USE_API_KEY` is already configured. Core Usage Guard must remain zero-extra-key.

## Finish

Verify explicit requirements and the final diff, then:

    & "$HOME\.codex-usage-guard\guard.cmd" finish --task-id <ID> --status completed

The finish response includes the local before/after usage snapshot when Codex exposes it. Report:

- what changed
- what was verified
- selected route
- task token delta when measured on the same thread
- 5-hour/weekly usage percentage delta when available
- unresolved risks

Token counts are local Codex telemetry. Rate-limit percentage deltas are coarse account meters and are not the same thing as exact task cost. Never claim an exact percentage of allowance saved without a controlled baseline comparison.

Read the bundled references only when the plan requests them:
- `references/routing.md`
- `references/verification.md`
- `references/context.md`
- `references/ui-ux.md`
- `references/system-design.md`
- `references/browser-verification.md`
