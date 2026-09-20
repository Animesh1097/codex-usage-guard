# Changelog

## 0.7.0

- substantially strengthen the UI/UX quality policy for product and brand surfaces
- add deterministic UI context detection for existing styling systems, component libraries, token files, and CSS variables
- add a zero-model `ui-audit` quality gate for common accessibility and generated-UI regressions
- audit changed UI files first so existing unrelated design debt does not block focused tasks
- detect issues such as non-semantic click targets, missing image alt text, removed focus rings, gradient text, decorative stripes, arbitrary z-indexes, transition-all, bounce motion, oversized radii, and repeated eyebrow-label patterns
- inject compact existing-design context into pinned UI workers before they edit
- require UI workers to run the deterministic audit after editing
- broaden UI skill routing so responsive/design/polish tasks still receive UI guidance even when classified as debugging
- require an inspect -> shape -> implement -> audit -> render -> critique -> polish -> diff-review loop for UI tasks
- add AI UX Playground, Impeccable, Jakub Krehel's design skills, Taste Skill, and Vercel Web Interface Guidelines to third-party research/attribution
- validate `pyproject.toml` in CI and repair the malformed v0.6 version string


## 0.6.0

- add a compact zero-dependency Guard HUD for guarded-task progress
- animate the HUD in terminals that support live redraw
- fall back to one small visual snapshot when live animation is unavailable
- show route flow visually instead of dumping JSON by default for status/enforcement
- visualize coordinator -> requested model routing, reasoning level, action budget, model-turn budget, worker token total, and route outcome
- reserve a visual judgement stage for the planned adaptive task judge
- keep `--json` on status/enforce for machine-readable Skill control
- preserve the v0.5 pinned-worker route enforcement and verification behavior


## 0.5.0

- enforce the selected model and reasoning from inside an already-open Codex session
- add a single pinned `codex exec` worker when the coordinator model/reasoning does not match the route
- verify the worker's actual model and reasoning from Codex local thread metadata
- fail closed on model mismatch, reasoning mismatch, unavailable/unverifiable worker routes, or exhausted model budget
- never silently continue model-heavy work on Luna when Terra/GPT-5.6 was selected
- keep the parent Codex thread as a lightweight coordinator when a pinned worker executes the task
- record dedicated worker thread id, observed route, final message, and worker token usage
- use workspace-write sandboxing and never use the dangerous approval/sandbox bypass flag
- pass only the task-selected UI/UX/system/browser craft references to the worker
- show requested, coordinator, and effective execution models separately in `$usage-guard status`
- retain `cguard` for users who want the parent session itself started on the selected route


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
