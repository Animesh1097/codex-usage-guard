# Codex Usage Guard

**Codex Usage Guard** is a local, zero-API-key control plane for OpenAI Codex. It is designed for one problem: **Codex allowance draining too quickly on long or repetitive coding sessions**.

It does not replace Codex and it does not run another LLM. It adds deterministic local policy around Codex so model strength, reasoning effort, context, retries, verification, and subagents are used only when justified.

> **v0.2 developer preview**. The project reports estimated context reduction, not guaranteed Codex allowance savings.

## What v0.2 does

- classifies the task before broad repository exploration
- inspects the real repository, changed files, diff size, manifests, scripts, and sensitive paths
- selects a bounded Codex agent profile and reasoning level
- keeps hard action, model-turn, and retry budgets
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

The default profiles follow current Codex subagent guidance:

| Workload | Profile | Model | Reasoning |
|---|---|---|---|
| tiny / obvious | `guard_fast` | `gpt-5.6-luna` | low |
| normal coding | `guard_worker` | `gpt-5.6-terra` | medium |
| harder bounded work | `guard_worker` | `gpt-5.6-terra` | high |
| ambiguous / high-risk | `guard_reasoner` | `gpt-5.6` | high |
| independent review | `guard_reviewer` | `gpt-5.6-terra` | high |

Astra is deliberately not selected automatically. The goal is usage conservation, not maximum reasoning on every task.

If a configured profile/model is unavailable, the Skill tells Codex to keep the same budget and continue with the current available model rather than failing the task.

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
7. runs `guard doctor`

Restart Codex after installation.

For users who prefer not to pipe a remote script into PowerShell, clone the repository first, inspect `install.ps1`, and run it locally.

## Use

### Recommended: explicit Skill invocation

    $usage-guard fix the seller form and verify the build

Codex can also activate the Skill implicitly when the task matches its description.

Codex CLI/IDE users can use `/skills` to inspect available Skills.

### Compatibility wrapper

Some Codex CLI builds/frontends have supported user prompt wrappers such as:

    /prompts:harness fix the seller form

This is a compatibility convenience, not the core integration. The supported design is the Codex Skill.

## How a guarded task works

    user objective
         |
         v
    local repo inspection
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
    persistent task state
         |
         +--> HOT: exact current evidence
         +--> WARM: compact completed/recent state
         +--> COLD: full local event history + hashes
         |
         v
    Codex worker
         |
         v
    local next-action predictor
         |
         +--> inspect
         +--> edit
         +--> targeted tests
         +--> typecheck
         +--> build
         +--> lint
         +--> diff review
         +--> production verification
         +--> stop
         |
         +----> repeat only while budget/evidence justify it

## Local control-plane commands

The Skill runs these automatically, but they are also useful for debugging the harness.

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
