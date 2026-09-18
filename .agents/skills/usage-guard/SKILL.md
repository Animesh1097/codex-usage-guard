---
name: usage-guard
description: Conserve Codex allowance while completing coding tasks. Use for implementation, debugging, refactoring, deployment checks, repository investigation, or any task where context size, repeated tool output, retries, model choice, reasoning effort, and unnecessary agent loops should be minimized.
---

# Codex Usage Guard

Treat the user's objective as the source of truth. Do not ask the user to choose a model, reasoning level, agent mode, or next step when the harness can decide.

## 1. Classify before spending

Run the bundled deterministic planner before broad repository exploration.

Windows PowerShell command:

    python "$HOME\.codex-usage-guard\scripts\guard_cli.py" plan --task "<USER_OBJECTIVE>" --repo .

POSIX command:

    python3 "$HOME/.codex-usage-guard/scripts/guard_cli.py" plan --task "<USER_OBJECTIVE>" --repo .

Use the returned agent_profile, reasoning_effort, context_budget_tokens, max_model_turns, max_retries, and predicted_steps as hard guidance. Prefer a single agent. Never fan out agents merely because parallelism is available.

If the requested custom agent profile is unavailable, continue with the current agent while preserving the same budget and reasoning policy.

## 2. Spend deterministic work before model work

Prefer, in order:

1. git status, targeted git diff, exact symbol/file search.
2. Existing deterministic tests, lint, type checks, and builds.
3. Small targeted file reads.
4. A model reasoning turn only when semantic judgment is actually required.

Do not reread unchanged files. Do not rescan the full repository after relevant files are known. Keep exact paths, code, error messages, stack frames, IDs, hashes, SQL, API routes, environment-variable names, and current user requirements lossless.

## 3. Compress noisy tool output locally

When a command may produce large output, compress before feeding it back into the reasoning loop.

Examples on Windows:

    npm test 2>&1 | python "$HOME\.codex-usage-guard\scripts\guard_cli.py" compress --type test
    git diff 2>&1 | python "$HOME\.codex-usage-guard\scripts\guard_cli.py" compress --type git

Use --type log for build/server logs. Never compress away the exact failing diagnostic needed for a fix.

## 4. Predict the next action instead of asking the user

After each meaningful state change, choose the cheapest useful next action. Use the local predictor when the decision is routine:

    python "$HOME\.codex-usage-guard\scripts\guard_cli.py" next --kind <KIND> --changed-files <N> --test-status <not-run|pass|fail> --build-status <not-run|pass|fail|not-needed> --lint-status <not-run|pass|fail|not-needed>

Recompute after new evidence. Do not blindly follow a stale long plan.

## 5. Bounded agent policy

- guard_fast: tiny/simple work, low reasoning.
- guard_worker: normal implementation/debugging.
- guard_reasoner: hard cross-system reasoning only.
- guard_reviewer: independent review only when deterministic checks cannot establish correctness.

A subagent must receive only task-specific context, never the entire parent transcript. Spawn at most one concurrent subagent unless the user explicitly requests parallel work.

## 6. Retry policy

A failed attempt must produce new evidence. Never repeat the same search/edit/test cycle without a changed hypothesis.

When the retry budget is exhausted:

1. Stop the loop.
2. Collect the exact failure evidence.
3. Reassess the hypothesis and scope.
4. Escalate model/reasoning once only if the task still requires it.

## 7. Definition of done

Before stopping, verify every explicit requirement, inspect the final diff, and run the smallest sufficient deterministic checks. For production/deployment tasks, verify the production state when access exists.

Stop when another model turn is unlikely to materially improve completion. Do not use remaining budget just because it exists.

## Reporting

Keep the user-facing report short: what changed, what was verified, unresolved risks if any, and the usage-guard strategy only when useful. Never claim that estimated context reduction equals the same percentage of Codex allowance saved.
