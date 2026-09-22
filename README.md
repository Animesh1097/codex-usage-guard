# Codex Usage Guard

**Codex Usage Guard** is a local, zero-extra-API-key control plane for OpenAI Codex. Its purpose is to make coding sessions more efficient and more reliable through repository-aware planning, bounded work loops, compact context, deterministic verification, usage measurement, and task-specific craft guidance.

It does not replace Codex and it does not run another LLM by default. The normal workflow keeps the user's currently selected Codex model and reasoning mode unchanged unless the user explicitly opts into advanced model routing.

> **v1.0 alpha foundation.** The working Python runtime remains compatible while deterministic subsystems migrate behind tests to a Rust core. A Tauri visual companion is being introduced as a read-only, non-critical presentation layer. Usage Guard measures local usage telemetry but does not claim guaranteed allowance savings.

## What the v1 alpha adds

- keeps `$usage-guard` work in the **current Codex session by default**
- introduces `crates/usage-guard-core` for deterministic Rust policy/budget/next-action logic
- adds fixture-driven parity so Rust behavior can be checked before replacing Python subsystems
- introduces a Tauri v2 visual companion with a modern web-rendered workflow scene
- keeps the visual companion read-only and non-critical: core guard work must continue if the UI fails
- prefers a compiled visualizer automatically when one is installed, with the existing Python/Tkinter view as fallback
- does not automatically switch models, change reasoning effort, or spawn a pinned Codex worker
- leaves `cguard` / legacy route enforcement available only as explicit advanced opt-in tools
- keeps separate graphical pop-up visualization off by default
- visualizes the real workflow as **analyze → plan → work → verify → complete/failed**
- removes model names and model-routing signals from the normal visual UI
- uses task-kind color accents instead of model-family colors
- keeps a compact model-neutral terminal HUD as fallback
- strengthens the UI/UX acceptance loop with rendered checks across representative mobile/tablet/desktop widths
- detects the repository's existing styling system, component libraries, token files, and CSS variables before UI editing
- runs a deterministic zero-model `ui-audit` for common accessibility and generated-UI regressions
- uses progressive disclosure so only relevant UI/UX, system-design, or browser-verification references are loaded
- records local before/current/after usage telemetry without reading Codex authentication files
- keeps action, turn, and retry budgets
- builds compact Hot / Warm / Cold context capsules
- predicts the cheapest useful next action after each meaningful step
- discovers project-specific test, build, lint, and typecheck commands
- compresses noisy test, diff, and log output locally
- avoids multi-agent fan-out by default
- stops/reassesses when additional model work is no longer justified

## Quick start

See [docs/quickstart.md](docs/quickstart.md) for the shortest install → first-task → status workflow.

The v1 migration plan is in [ROADMAP.md](ROADMAP.md), and the architecture boundary is documented in [docs/architecture/v1-alpha.md](docs/architecture/v1-alpha.md).

## Requirements

- an existing Codex installation
- an existing ChatGPT/Codex sign-in
- Git
- Python 3.10+ for the compatibility runtime during the v1 migration

No `OPENAI_API_KEY`, Ollama, DeepSeek/Anthropic key, paid proxy, or vector database is required.

## Execution mode

The default execution mode is **current-session**.

When you run:

    $usage-guard <task>

Usage Guard preserves the model and reasoning mode you already chose in Codex. The classifier still estimates task complexity and risk, but it uses those signals for context budgets, verification depth, action limits, and craft references—not to override your model.

Advanced model routing is retained only for users who explicitly want it:

- `cguard "<task>"` starts a new Codex session using the legacy routing policy.
- `guard.cmd enforce --task-id <ID>` runs the legacy pinned-worker path.

Neither is invoked automatically by the normal Skill.

## Install on Windows

Open PowerShell:

    irm https://raw.githubusercontent.com/Animesh1097/codex-usage-guard/main/install.ps1 | iex

The installer:

1. verifies Git, Codex, and Python
2. verifies an existing install points to this repository
3. updates/clones `~/.codex-usage-guard`
4. installs the global Skill to `~/.agents/skills/usage-guard`
5. installs the custom Codex agents under `$CODEX_HOME/agents`
6. creates `guard.cmd`
7. installs a global `cguard.cmd` launcher under `~/.codex-usage-guard-bin`
8. adds that dedicated launcher directory to the user PATH
9. runs `guard doctor`

A new terminal may be needed before `cguard` is visible everywhere.

For users who prefer not to pipe a remote script into PowerShell, clone the repository first, inspect `install.ps1`, and run it locally.

## Use

### Recommended: stay inside Codex

After the one-time install, open Codex normally in your project and use:

    $usage-guard build a small CRM and verify it

Usage Guard inspects the repository, creates the bounded task state, captures a usage baseline, chooses relevant craft references, and continues **in the current Codex session**.

It does not automatically change your model or reasoning mode.

At any time:

    $usage-guard status
    $usage-guard usage

`$usage-guard status` shows the current task phase, budgets, usage, and verification state without model-routing noise.

### Task progress

Normal Usage Guard use stays inside Codex and does **not** automatically open a separate always-on-top window.

Use:

    $usage-guard status

for compact model-neutral progress based on the real task phases:

- **analyze**
- **plan**
- **work**
- **verify**
- **complete / failed**

The experimental graphical companion remains in the repository for optional testing, but it is opt-in only and is never required by the core guard.

To explicitly enable it for a session:

    CODEX_USAGE_GUARD_VISUAL=1

The older `CODEX_USAGE_GUARD_DISABLE_VISUAL=1` setting is still honored and overrides opt-in.

### UI/UX quality path

For UI-relevant work, Usage Guard first inspects the incumbent design system:

    guard.cmd ui-context --repo .

Before editing it now also derives a visual-quality bar:

    guard.cmd ui-brief --task "<objective>" --repo .

High-ambition prompts such as polished, premium, eye-catching, distinctive, memorable, high-end, or explicitly non-generic UI enter **design-grade mode**. That mode requires an explicit visual concept before coding and two rendered critique passes.

After editing it runs:

    guard.cmd ui-audit --repo . --strict --json

The deterministic audit checks source-code/accessibility hygiene and common generated-UI anti-patterns. It does **not** certify aesthetic quality.

When browser tooling is available, the changed flow should be rendered and checked at representative narrow mobile, compact/tablet, and desktop widths. Functional browser verification and aesthetic critique are treated as separate evidence. The final UI acceptance pass covers composition, hierarchy, typography, spacing, alignment, color/material coherence, states, clipping/overflow, responsiveness, focus behavior, and product-specific identity.

A passing build or source audit alone is not sufficient UI evidence.

## How a guarded task works

    $usage-guard + user objective
         |
         v
    local repo inspection + usage baseline
         |
         +--> changed files / diff size
         +--> sensitive paths
         +--> project type / scripts
         +--> verification commands
         |
         v
    complexity + risk analysis
         |
         +--> context budget
         +--> action / turn / retry limits
         +--> verification depth
         +--> task-specific craft references
         |
         v
    CURRENT CODEX SESSION
         |
         +--> no automatic model switch
         +--> no automatic reasoning-mode switch
         +--> no automatic pinned worker
         |
         v
    analyze -> plan -> work -> verify
         |
         +--> deterministic checks before more reasoning
         +--> UI audit / browser verification when relevant
         +--> compact Hot / Warm / Cold context
         |
         v
    final diff + requirement verification
         |
         +--> DONE
         +--> BLOCKED

## Local control-plane commands

The Skill runs these automatically, but they are also useful for debugging the harness.

Preview a launch route without a model call:

    & "$HOME\.codex-usage-guard\guard.cmd" launch --dry-run --repo . "change the footer phone number"

Read current Codex usage telemetry without a model call:

    & "$HOME\.codex-usage-guard\guard.cmd" usage --repo .

Show the active task's phase, budget, verification and usage delta:

    & "$HOME\.codex-usage-guard\guard.cmd" status --repo .

Advanced opt-in model routing only:

    & "$HOME\.codex-usage-guard\guard.cmd" enforce --task-id <ID>

Inspect a repository without a model call:

    & "$HOME\.codex-usage-guard\guard.cmd" inspect --repo .

Create a guarded task:

    & "$HOME\.codex-usage-guard\guard.cmd" start --task "fix the login bug" --repo .

Show the compact context capsule:

    & "$HOME\.codex-usage-guard\guard.cmd" capsule --task-id <ID>

Record a deterministic action:

    & "$HOME\.codex-usage-guard\guard.cmd" record --task-id <ID> --action "targeted tests" --kind deterministic --outcome pass

Record a model turn:

    & "$HOME\.codex-usage-guard\guard.cmd" record --task-id <ID> --action "implement fix" --kind model --outcome pass

Ask for the cheapest useful next action:

    & "$HOME\.codex-usage-guard\guard.cmd" next --task-id <ID> --test-status pass --typecheck-status pass

Show remaining budget:

    & "$HOME\.codex-usage-guard\guard.cmd" budget --task-id <ID>

Compress test output:

    npm test 2>&1 | & "$HOME\.codex-usage-guard\guard.cmd" compress --type test --task-id <ID>

Compress a diff while preserving nearby context:

    git diff 2>&1 | & "$HOME\.codex-usage-guard\guard.cmd" compress --type git --task-id <ID>

Finish:

    & "$HOME\.codex-usage-guard\guard.cmd" finish --task-id <ID> --status completed

Telemetry:

    & "$HOME\.codex-usage-guard\guard.cmd" stats
    & "$HOME\.codex-usage-guard\guard.cmd" stats --task-id <ID>

Health/version:

    & "$HOME\.codex-usage-guard\guard.cmd" doctor
    & "$HOME\.codex-usage-guard\guard.cmd" version

## Budget behavior

The guard separates three limits:

- **action budget**: total meaningful steps
- **model-turn budget**: additional Codex model work
- **retry budget**: repeated attempts after a failure

When the model-turn budget is exhausted, free deterministic checks can still run. The guard blocks more model turns without blocking tests, builds, lint, type checks, or diff review.

A retry is only justified when the hypothesis or evidence changed.

## Context temperatures

### Hot

Exact information required now:

- objective
- unresolved failures
- currently changed files
- sensitive changed files
- exact errors, code, paths, IDs, hashes, SQL, routes, and environment-variable names relevant to the active step

### Warm

Compact reusable state:

- completed actions
- recent evidence
- selected strategy and execution constraints
- available verification commands
- file-hash changes since the last capsule

### Cold

Kept locally instead of repeatedly occupying model context:

- full task event history
- stale logs
- superseded search output
- unchanged content
- old verbose command output

## Compression policy

Compression is deterministic and local.

- test/log output keeps failure lines and surrounding evidence
- Git diffs keep changed lines **plus nearby unchanged context**
- ANSI formatting is removed
- repeated identical lines are collapsed
- exact failure diagnostics are preferred over prose summaries

The compressor is not a secret scrubber. If an underlying command prints credentials, fix that leak at the source.

## Usage measurement

Usage Guard reads only local Codex telemetry:

- the newest compatible `~/.codex/state_N.sqlite` for thread token totals
- local rollout `token_count` events for input/cached-input/output/reasoning breakdowns and rate-limit snapshots

It never reads `~/.codex/auth.json` and never forwards Codex credentials.

A same-thread token delta is the strongest measurement. A global-token fallback is marked approximate because another concurrent Codex session can contribute to it. The 5-hour/weekly percentage meters are coarse account counters and should not be presented as exact task cost.

## Task-specific craft references

The core Skill uses progressive disclosure: a task gets at most two extra craft references.

- `ui-ux.md`: product-vs-brand context, hierarchy, layout, typography, color, surfaces, states, accessibility, motion, responsive stress testing, anti-generic checks, and a required polish loop
- `system-design.md`: boundaries, data ownership, retries, migrations, security and tradeoffs
- `browser-verification.md`: real-browser evidence, small valid browser actions, independent DONE checks

See [THIRD_PARTY_RESEARCH.md](THIRD_PARTY_RESEARCH.md) for the public projects that informed these patterns and their licenses. v0.7 specifically reviewed AI UX Playground's curated skill catalog plus Impeccable, Jakub Krehel's design skills, Taste Skill, and Vercel's Web Interface Guidelines. Usage Guard keeps its own compact original guidance instead of vendoring those skill packs.

## Offline benchmark

Run:

    python scripts/benchmark.py

This checks routing regression fixtures and verifies that a noisy test log is actually reduced.

It intentionally does **not** claim real Codex-plan savings. A public savings number should only be published after controlled real-world baseline-vs-guarded sessions.

## Development

Run everything locally:

    python -m compileall -q guard scripts tests
    python -m unittest discover -s tests -v
    python scripts/benchmark.py

GitHub Actions runs Python 3.11 and 3.13 on Windows and Ubuntu, CLI smoke tests, the offline benchmark, and PowerShell parser validation.

## Uninstall

    & "$HOME\.codex-usage-guard\uninstall.ps1"

Task state and telemetry are preserved by default.

To remove them too:

    & "$HOME\.codex-usage-guard\uninstall.ps1" -PurgeData

## Security

See [SECURITY.md](SECURITY.md). Codex Usage Guard is not a sandbox and does not replace Codex permission controls.

## Independence notice

Codex Usage Guard is an independent open-source project. It is not affiliated with, endorsed by, or sponsored by OpenAI. OpenAI, ChatGPT, and Codex are trademarks of their respective owners.

## License

MIT. See [LICENSE](LICENSE).

See [CHANGELOG.md](CHANGELOG.md) for version history.


## v1 migration status

The project is deliberately avoiding a big-bang rewrite.

Current alpha foundation:
- Rust workspace with deterministic policy, budget, and next-action primitives
- shared policy fixtures
- Tauri v2 visual companion scaffold
- read-only task snapshot bridge
- compiled-visualizer preference with Python fallback
- Rust/Tauri CI jobs
- benchmark methodology that forbids unsupported savings claims

Still on the compatibility runtime:
- repository inspection
- state persistence/migrations
- Codex local usage adapters
- output compression
- full installer/release packaging

See [ROADMAP.md](ROADMAP.md) for the migration gates.
