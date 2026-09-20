# Changelog

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
