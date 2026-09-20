# Changelog

## 0.4.0

- make the in-Codex `$usage-guard` Skill the normal post-install workflow
- add local `status` and `usage` commands with before/current/after Codex telemetry
- track same-thread input, cached-input, output, reasoning, and total token deltas when available
- add approximate global-token fallback for pre-session launches
- include 5-hour and weekly rate-limit percentage deltas when present in local rollout telemetry
- never read or forward Codex auth tokens
- add task-aware UI/UX, system-design, and browser-verification references with progressive disclosure
- add a small indexed next-action space inspired by structured fast-agent loops
- optionally use an existing Browser Harness for UI verification
- keep Browser Use Cloud optional and core Usage Guard zero-extra-key
- retain `cguard` as the optional parent-model pre-session launcher
- add third-party research and attribution notes


## 0.3.0

- global `cguard` launcher for Windows
- local task classification before Codex starts
- explicit Codex `--cd` project root at launch
- automatic launch-time model selection with `--model`
- automatic launch-time reasoning selection with `model_reasoning_effort`
- pre-created guarded task state reused by the Skill instead of duplicated
- dry-run route preview that does not start Codex or create task state
- direct Skill mode documented as secondary when parent-model switching matters

## 0.2.1

- detect standard-library Python `unittest` suites
- prevent invented verification commands in the Skill
- ignore the generated local Windows `guard.cmd` launcher

## 0.2.0

- repo-aware task/risk classification
- persistent guarded task state
- hard action, model-turn, and retry budgets
- Hot/Warm/Cold context capsules
- changed-file SHA-256 tracking
- project-aware test/build/lint/typecheck discovery
- safer diff compression with nearby context
- task-aware telemetry
- smarter next-action prediction
- corrected high-capability Codex routing to `gpt-5.6`
- smaller Skill using progressive disclosure
- hardened Windows installer and non-destructive uninstall defaults

## 0.1.0

Initial developer preview.
