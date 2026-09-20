---
name: usage-guard
description: Reduce Codex usage on coding tasks with current-session execution, local usage snapshots, bounded turns, progressive craft references, compressed evidence, deterministic UI quality checks, and the cheapest valid next action.
---

# Codex Usage Guard

The default workflow stays in the user's current Codex session. Do **not** change models, change reasoning effort, spawn a pinned worker, or launch a new Codex session unless the user explicitly asks for model routing.

The guard's job is to improve task quality and efficiency through repository-aware planning, context control, deterministic checks, task-specific craft guidance, usage measurement, and stop conditions.

## In-Codex commands

Interpret these without starting a new task:

- `$usage-guard status` -> run `guard.cmd status --repo .`
- `$usage-guard usage` -> run `guard.cmd usage --repo .`
- `$usage-guard budget` -> resolve the active task for this repo and show its budget
- `$usage-guard stop` -> finish the active task as blocked or abandoned according to user intent

Do not surface model-routing information in normal status output.

## Start a guarded task

If `CODEX_USAGE_GUARD_TASK_ID` is present, reuse that task ID and do not create a duplicate.

Otherwise on Windows:

    & "$HOME\.codex-usage-guard\guard.cmd" start --task "<USER_OBJECTIVE>" --repo .

The start command now:
- keeps execution in the current Codex session
- detects the repository and verification commands
- creates action / turn / retry budgets
- captures a local usage baseline
- chooses zero-to-two task-specific craft references
- launches the graphical task visualizer when a desktop GUI is available

Do **not** run `enforce` in the normal workflow.

Read only the reference files listed in `plan.skill_refs`.

## Work loop

Before another model-heavy step:

    & "$HOME\.codex-usage-guard\guard.cmd" capsule --task-id <ID>

After each meaningful step:

    & "$HOME\.codex-usage-guard\guard.cmd" record --task-id <ID> --action "<ACTION>" --kind <deterministic|model> --outcome <info|pass|fail>

Use real action names such as:
- inspect relevant code
- plan implementation
- update seller form
- run targeted tests
- run build
- browser verify
- review diff

Those actions also drive the live visualizer through analyze → plan → work → verify.

Ask for the cheapest justified next operation:

    & "$HOME\.codex-usage-guard\guard.cmd" next --task-id <ID> [verification status flags]

Treat the returned `action_space` as the valid next-operation set. Prefer deterministic evidence over another reasoning turn.

If the model-turn budget is exhausted, continue only with deterministic checks that remain allowed.

## UI / UX tasks

For UI-relevant tasks, load `references/ui-ux.md` and, when selected, `references/browser-verification.md`.

Before editing, inspect the incumbent UI system **and** derive the visual-quality bar:

    & "$HOME\.codex-usage-guard\guard.cmd" ui-context --repo .
    & "$HOME\.codex-usage-guard\guard.cmd" ui-brief --task "<USER_OBJECTIVE>" --repo .

If `ui-brief` returns `visual_ambition: design-grade`, do not begin implementation until the visual concept, composition rule, typography roles, color/material roles, density rhythm, and one signature product-specific detail are explicit.

After editing:

    & "$HOME\.codex-usage-guard\guard.cmd" ui-audit --repo . --strict --json

The deterministic audit is **source-code hygiene only**. It can detect implementation/accessibility anti-patterns, but it cannot certify that the rendered UI is beautiful, distinctive, or visually resolved.

The expected UI loop is:

1. inspect the incumbent design system
2. derive `ui-brief` and set the production vs design-grade bar
3. shape visual concept, hierarchy, composition, typography, and primary action
4. implement the smallest complete change
5. run deterministic UI audit
6. run detected project checks
7. render the changed flow in a browser when available
8. critique composition, hierarchy, typography, spacing, color/material coherence, controls/states, responsiveness, product identity, clipping, and accessibility
9. fix the largest visual defects first
10. for design-grade work, re-render and perform a **second aesthetic critique pass**
11. review the final diff

A passing build or passing `ui-audit` is not enough proof for UI work. If rendered browser/screenshot evidence is unavailable, explicitly report that aesthetic quality was not visually verified.

## Live visualizer

The graphical visualizer is a progress metaphor, not a fake percentage meter.

Its phases correspond to actual task state:
- analyze
- plan
- work
- verify
- complete / failed

It does not display or imply model switching.

If graphical rendering is unavailable, Usage Guard falls back to the compact model-neutral terminal HUD.

## Compression

Compress noisy output before returning it to model context:

    <DETECTED_TEST_COMMAND> 2>&1 | & "$HOME\.codex-usage-guard\guard.cmd" compress --type test --task-id <ID>
    git diff 2>&1 | & "$HOME\.codex-usage-guard\guard.cmd" compress --type git --task-id <ID>

Use only verification commands reported by the guard or explicitly present in repository configuration / CI. Never invent project commands.

## Finish

After explicit requirements and the final diff are verified:

    & "$HOME\.codex-usage-guard\guard.cmd" finish --task-id <ID> --status completed

Final user-facing output should stay focused on:
- what changed
- what was verified
- unresolved issues
- measured token/usage delta when available

Do not mention model selection or routing unless the user explicitly asks for it.

## Advanced opt-in model routing

Model routing remains available only as an advanced opt-in compatibility feature:

- `cguard "<task>"` can launch a new Codex session with an explicit route.
- `guard.cmd enforce --task-id <ID>` can run the legacy pinned-worker path.

Never invoke either automatically from `$usage-guard`.

References are loaded only when selected:
- `references/routing.md`
- `references/verification.md`
- `references/context.md`
- `references/ui-ux.md`
- `references/system-design.md`
- `references/browser-verification.md`
