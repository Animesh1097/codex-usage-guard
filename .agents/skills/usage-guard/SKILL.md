---
name: usage-guard
description: Reduce Codex usage on coding tasks with enforced model routing, local usage snapshots, bounded model turns, progressive craft references, compressed evidence, and the cheapest valid next action.
---

# Codex Usage Guard

The user should be able to stay inside Codex after the one-time install. Treat the user's objective as the source of truth. Do not ask them to choose a model, reasoning level, agent mode, verification command, or next step when the guard can decide.

## In-Codex commands

Interpret these without starting a new task:

- `$usage-guard status` -> run `guard.cmd status --repo .` and show the compact visual HUD by default
- `$usage-guard usage` -> run `guard.cmd usage --repo .`
- `$usage-guard budget` -> resolve the active task for this repo, then show its status/budget
- `$usage-guard stop` -> finish the active task as blocked or abandoned according to the user's intent

Keep the user-facing result compact. Never expose auth tokens, cookies, hidden session credentials, or raw rollout contents.

## Start and enforce a guarded task

If `CODEX_USAGE_GUARD_TASK_ID` is present, the pre-session launcher already created the task. Reuse that ID and do not call `start` again.

Otherwise on Windows:

    & "$HOME\.codex-usage-guard\guard.cmd" start --task "<USER_OBJECTIVE>" --repo .

Keep the returned `task_id`. The plan includes model/reasoning policy, budgets, verification commands, local usage baseline, and zero-to-two task-specific reference files.

Immediately enforce the route. This command shows the compact animated Guard HUD when the terminal supports live redraw:

    & "$HOME\.codex-usage-guard\guard.cmd" enforce --task-id <ID>

After enforcement, read the machine result without replacing the user-facing HUD:

    & "$HOME\.codex-usage-guard\guard.cmd" status --task-id <ID> --json

Interpret the enforcement/status result strictly:

- `parent-match`: the current Codex thread already matches both selected model and reasoning. Continue in this thread.
- `verified`: a single pinned `codex exec` worker ran the objective using the selected model/reasoning and Codex local thread telemetry verified both. Do not re-implement the task in the coordinator. Continue only with justified deterministic verification, diff review, or unresolved follow-up.
- `failed`, `model-mismatch`, `reasoning-mismatch`, `unverified`, or `unverified-no-thread`: do not silently continue model-heavy implementation on the coordinator. Report the routing failure with the requested and observed route. Deterministic inspection is allowed.
- `budget-blocked`: do not bypass the guard.

The coordinator status line may still show its original model when a pinned worker was used. That is expected. The Guard HUD is the default human-facing progress view; `status --json` is the machine-readable source of truth for requested model, coordinator model, verified execution model, and route status.

Never claim the selected model was used unless enforcement is `parent-match` or `verified`.

Read only the reference files listed in `plan.skill_refs`. Do not load every craft guide.

## Pinned worker safety

The pinned worker:

- uses the existing Codex/ChatGPT sign-in
- runs one `codex exec` thread only
- pins `--model` and `model_reasoning_effort`
- uses `workspace-write` sandboxing
- uses non-interactive `approval_policy="never"` inside that sandbox
- never uses the dangerous sandbox/approval bypass flag
- does not spawn subagents
- preserves unrelated user changes
- records its worker thread id, observed model/reasoning, final message, and worker token usage

If the requested model is unavailable, fail closed. Do not silently substitute Luna or another model.

## Work loop

When the parent thread is the verified execution thread, or after a verified pinned worker has finished, prefer deterministic evidence before any additional model work.

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

Report:

- what changed
- what was verified
- requested route
- route-enforcement status
- actual execution model/reasoning when verified
- dedicated worker token usage when a pinned worker was used
- same-thread or account-meter deltas when available
- unresolved risks

Token counts are local Codex telemetry. Rate-limit percentage deltas are coarse account meters and are not the same thing as exact task cost. Never claim an exact percentage of allowance saved without a controlled baseline comparison.

Read the bundled references only when the plan requests them:
- `references/routing.md`
- `references/verification.md`
- `references/context.md`
- `references/ui-ux.md`
- `references/system-design.md`
- `references/browser-verification.md`
