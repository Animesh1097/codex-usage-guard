# Codex Usage Guard

**Codex Usage Guard** is a local, zero-API-key control plane for OpenAI Codex. It is designed for one problem: **Codex allowance draining too quickly on long or repetitive coding sessions**.

It does not replace Codex and it does not run another LLM. It adds deterministic local policy around Codex so model strength, reasoning effort, context, retries, verification, and subagents are used only when justified.

> **v0.5 developer preview**. Usage Guard now enforces its selected execution route from inside an already-open Codex session and verifies the worker route from local Codex thread metadata. It still does not claim guaranteed allowance savings.

## What v0.5 does

- makes **`$usage-guard` inside Codex the normal workflow** after one-time installation
- compares the current coordinator model/reasoning with the selected route
- when they differ, launches exactly one pinned `codex exec` worker with the selected `--model` and `model_reasoning_effort`
- verifies the worker's observed model and reasoning from Codex local thread metadata before calling the route successful
- fails closed instead of silently letting Luna execute work selected for Terra/GPT-5.6
- adds `$usage-guard status` / `$usage-guard usage` behavior with local before/current/after telemetry
- reads Codex's local state database and rollout token-count events read-only; it never reads or forwards auth tokens
- records total, input, cached-input, output, and reasoning-token deltas when the same Codex thread can be matched
- records 5-hour and weekly used-percentage deltas when Codex exposes rate-limit snapshots
- adds a small indexed next-action space inspired by fast browser-agent loops: only valid operations are offered
- loads UI/UX, system-design, and browser-verification guidance only when the task needs it
- optionally uses an already-installed Browser Harness for rendered UI verification
- keeps Browser Use Cloud optional; core Usage Guard still needs no extra API key
- retains the global **`cguard` launcher** for users who want the parent Codex model selected before the session starts
- launches Codex with an explicit project root, selected model, and reasoning effort before the first model turn
- classifies the task before broad repository exploration
- inspects the real repository, changed files, diff size, manifests, scripts, and sensitive paths
- selects a bounded Codex agent profile and reasoning level
- keeps state-enforced action, model-turn, and retry budgets
- stores persistent task state under `~/.codex-usage-guard-data`
- tracks SHA-256 hashes for changed files to detect re-reads and new changes
- builds compact **Hot / Warm / Cold** state capsules instead of relying on the full task history
- predicts the cheapest useful next action after each meaningful step
- discovers project-specific test, build, lint, and typecheck commands
- compresses noisy test, diff, and log output locally
- preserves nearby diff context instead of stripping every unchanged line
- defaults to a single worker and avoids multi-agent fan-out
- keeps task-aware compression telemetry
- stops/reassesses when model/retry budgets are exhausted

## Requirements

- an existing Codex installation
- an existing ChatGPT/Codex sign-in
- Git
- Python 3.10+

No `OPENAI_API_KEY`, Ollama, DeepSeek/Anthropic key, paid proxy, or vector database is required.

## Model routing

The default launcher routes are:

| Workload | Profile | Model | Reasoning |
|---|---|---|---|
| tiny / obvious | `guard_fast` | `gpt-5.6-luna` | low |
| normal coding | `guard_worker` | `gpt-5.6-terra` | medium |
| harder bounded work | `guard_worker` | `gpt-5.6-terra` | high |
| ambiguous / high-risk | `guard_reasoner` | `gpt-5.6` | high |
| independent review | `guard_reviewer` | `gpt-5.6-terra` | high |

Astra is deliberately not selected automatically. The goal is usage conservation, not maximum reasoning on every task.

The parent Codex TUI model may remain unchanged because a Skill cannot reliably replace that already-created parent thread. v0.5 handles this by treating the parent as a coordinator: when its model/reasoning differs from the selected route, Usage Guard runs one pinned Codex execution worker and verifies that worker's actual model/reasoning from local thread metadata. `cguard` remains available when you want the parent session itself to start on the selected route.

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

Usage Guard detects the repository, creates the local budget/state, captures a usage baseline, selects the route, then immediately enforces it. If the current Codex thread already matches the selected model and reasoning, it works in-place. If not, it launches one pinned `codex exec` worker using the selected route and verifies the worker's actual model/reasoning before accepting the execution.

At any time inside Codex:

    $usage-guard status
    $usage-guard usage

The status view includes the selected route, coordinator model/reasoning, verified effective execution model/reasoning, route-enforcement status, dedicated worker token usage when applicable, remaining action/model/retry budget, detected verification commands, relevant craft references, and before/current usage deltas.

A coordinator status line can therefore still show Luna while the actual task runs on a verified Terra/GPT-5.6 pinned worker. `$usage-guard status` is the source of truth for requested versus actual execution route.

When the task finishes, Usage Guard reports the measured token delta when available. If the task started in a new pre-session launcher and no same-thread baseline exists, it can fall back to an approximate global token delta; concurrent Codex sessions can make that fallback noisy.

### Route enforcement

For every new guarded task, the Skill runs:

    guard.cmd enforce --task-id <ID>

Possible outcomes:

- `parent-match`: coordinator model **and** reasoning already match the selected route; no nested worker is needed.
- `verified`: a pinned worker ran and its observed model/reasoning match the requested route.
- `model-mismatch`, `reasoning-mismatch`, `unverified`, `unverified-no-thread`, or `failed`: route enforcement failed. Usage Guard does not silently continue model-heavy work on the coordinator.
- `budget-blocked`: the model-turn/action budget prevents another worker.

The pinned worker uses the existing Codex/ChatGPT sign-in, `workspace-write` sandboxing, and non-interactive `approval_policy="never"` inside that sandbox. It never uses Codex's dangerous approval/sandbox bypass flag.

The worker is dedicated to one guarded task, so its local thread token total is also a useful per-task token measurement.

### Optional: pre-session parent-model routing

If you specifically want the Codex **parent session itself** to start on the selected model, use:

    cguard "fix the seller form and verify it"

This remains useful because a Skill running inside an already-open Codex session cannot reliably replace the parent TUI model by itself. Codex's native `/model` command can change model/reasoning manually; `cguard` applies the route before the first turn.

### Browser verification

Usage Guard does not require browser automation. For UI tasks it will detect an existing `browser-harness` installation and can use it as deterministic rendered verification.

Browser Use Cloud is optional. Usage Guard only considers it when the user has opted in and `BROWSER_USE_API_KEY` is already configured. No Browser Use key is required for the core guard.

## How a guarded task works

    $usage-guard + user objective
         |
         v
    local repo inspection + local usage baseline
         |
         +--> changed files / diff size
         +--> sensitive paths
         +--> test/build/lint/typecheck commands
         +--> project type / package manager
         |
         v
    task + risk classifier
         |
         +--> model profile
         +--> reasoning effort
         +--> context budget
         +--> action/model/retry limits
         |
         v
    route + progressive craft references
         |
         +--> UI/UX only when relevant
         +--> system design only when relevant
         +--> browser verification only when relevant
         |
         v
    compare current coordinator vs selected route
         |
         +--> exact match --> continue in parent
         |
         +--> mismatch --> one pinned codex exec worker
                          |
                          +--> --model <selected>
                          +--> model_reasoning_effort=<selected>
                          +--> verify observed model/reasoning from local thread state
                          +--> fail closed on mismatch/unverified route
         |
         v
    persistent task state + requested/actual execution route
         |
         +--> HOT: exact current evidence
         +--> WARM: compact completed/recent state
         +--> COLD: full local event history + hashes
         |
         v
    verified execution thread
         |
         v
    indexed local action space
         |
         +--> inspect
         +--> targeted tests
         +--> typecheck
         +--> build
         +--> lint
         +--> browser verify (when available/relevant)
         +--> diff review
         +--> production verify
         +--> DONE / BLOCKED
         |
         +----> repeat only while budget/evidence justify it

## Local control-plane commands

The Skill runs these automatically, but they are also useful for debugging the harness.

Preview a launch route without a model call:

    & "$HOME\.codex-usage-guard\guard.cmd" launch --dry-run --repo . "change the footer phone number"

Read current Codex usage telemetry without a model call:

    & "$HOME\.codex-usage-guard\guard.cmd" usage --repo .

Show the active task's requested route, coordinator route, effective execution route, budget, verification and usage delta:

    & "$HOME\.codex-usage-guard\guard.cmd" status --repo .

Enforce the selected route for an active task:

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
- selected strategy/model/reasoning
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

A same-thread token delta is the strongest measurement. When v0.5 uses a dedicated pinned worker, that worker thread is created for one guarded task, so its thread token total provides a particularly useful task-level measurement. A global-token fallback is marked approximate because another concurrent Codex session can contribute to it. The 5-hour/weekly percentage meters are coarse account counters and should not be presented as exact task cost.

## Task-specific craft references

The core Skill uses progressive disclosure: a task gets at most two extra craft references.

- `ui-ux.md`: visual hierarchy, states, accessibility, responsive behavior, anti-generic UI checks
- `system-design.md`: boundaries, data ownership, retries, migrations, security and tradeoffs
- `browser-verification.md`: real-browser evidence, small valid browser actions, independent DONE checks

See [THIRD_PARTY_RESEARCH.md](THIRD_PARTY_RESEARCH.md) for the public projects that informed these patterns and their licenses.

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
