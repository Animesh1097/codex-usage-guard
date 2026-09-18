# Codex Usage Guard

**Codex Usage Guard** is an open-source, zero-API-key usage optimizer for OpenAI Codex. It is built for a specific problem: Codex allowance draining too quickly during long coding sessions.

It does **not** replace Codex and it does **not** run another LLM. It adds deterministic local policy around Codex so expensive reasoning, context, retries, and subagents are used only when justified.

> Status: **v0.1 developer preview**. Usage reduction must not silently destroy code-critical context.

## Core behavior

- Classify the task locally before broad repository exploration.
- Choose a usage tier and bounded reasoning policy.
- Keep a context budget per task.
- Default to one agent instead of automatic multi-agent fan-out.
- Compress noisy tests, diffs, and logs locally with no model call.
- Predict the cheapest useful next action after every meaningful state change.
- Cap retries and stop repeated search/edit/test loops that have no new evidence.
- Prefer tests, builds, lint, Git, and exact search before another reasoning turn.
- Keep exact code, paths, errors, stack frames, IDs, hashes, SQL, routes, environment variable names, and current requirements lossless.

## No extra model stack

Requirements:

- existing Codex installation
- existing ChatGPT/Codex sign-in
- Git
- Python 3.10+

No `OPENAI_API_KEY`, Ollama, DeepSeek/Anthropic key, paid proxy, or vector database is required.

## Model policy

| Workload | Profile | Model | Reasoning |
|---|---|---|---|
| tiny/simple | `guard_fast` | `gpt-5.6-luna` | low |
| normal coding | `guard_worker` | `gpt-5.6-terra` | medium |
| difficult/high-risk | `guard_reasoner` | `gpt-5.6-sol` | high |
| review only when needed | `guard_reviewer` | `gpt-5.6-luna` | medium |

Astra is deliberately **not selected automatically in v0.1**. If a configured model is unavailable, the Skill falls back to the current Codex agent while preserving the same usage policy.

## Install on Windows

Open PowerShell:

    irm https://raw.githubusercontent.com/Animesh1097/codex-usage-guard/main/install.ps1 | iex

The installer clones this project to `~/.codex-usage-guard`, installs the global Skill and agent profiles, installs the optional custom-prompt wrapper, and creates a stable local `guard.cmd` launcher.

Restart Codex after installation.

## Use

Reliable Skill invocation:

    $usage-guard fix the seller form and verify the build

Codex can also automatically select the Skill when the task matches its description.

Where user custom prompts are supported:

    /prompts:harness fix the seller form and verify the build

Custom prompt support has changed across Codex releases/frontends, so `$usage-guard` is the stable fallback. The project does not claim arbitrary first-class `/harness` commands are universally supported today.

## Architecture

    User objective
         |
         v
    local classifier  -> complexity / risk / task type
         |             -> context / retry budget
         |             -> agent profile / reasoning policy
         |             -> predicted next actions
         v
       Codex
         |
         +-> one selected worker profile
         +-> narrow search and targeted reads
         +-> deterministic tests/build/lint first
         +-> local output compression
         +-> bounded model/reasoning turns
         v
    local next-action predictor
         |
         +-> inspect? edit? test? build? diff review? stop?
         v
    verified completion

## Local guard commands on Windows

Classify a task:

    & "$HOME\.codex-usage-guard\guard.cmd" plan --task "fix the login bug" --repo .

Compress noisy test output:

    npm test 2>&1 | & "$HOME\.codex-usage-guard\guard.cmd" compress --type test

Compress a large diff:

    git diff 2>&1 | & "$HOME\.codex-usage-guard\guard.cmd" compress --type git

Predict the next action:

    & "$HOME\.codex-usage-guard\guard.cmd" next --kind debugging --changed-files 2 --test-status pass

Show local compression telemetry:

    & "$HOME\.codex-usage-guard\guard.cmd" stats

## Usage-first rules

1. **No multi-agent by default.** Extra agents must justify additional usage.
2. **Deterministic evidence before reasoning.** Tests, Git, lint, build output, and exact searches come first.
3. **Re-plan after evidence.** Do not blindly follow a stale long plan.
4. **Bound retries.** A retry needs a changed hypothesis or new evidence.
5. **Diff-first and targeted reads.** Avoid repeatedly loading unchanged files.
6. **Stop deliberately.** Do not spend remaining budget after requirements are verified.

## Development

Run tests:

    python -m unittest discover -s tests -v

V0.1 has no runtime Python dependencies. GitHub Actions runs the test suite on Windows and Ubuntu with Python 3.11 and 3.13, and parses the PowerShell installer scripts on Windows.

## Important limitation

Codex plan/credit usage is not determined only by token count. Model choice, reasoning, tool use, task complexity, and execution can all affect usage. Telemetry reports **estimated context reduction**, not a guaranteed percentage increase in Codex allowance.

## Independence notice

Codex Usage Guard is an independent open-source project. It is not affiliated with, endorsed by, or sponsored by OpenAI. OpenAI, ChatGPT, and Codex are trademarks of their respective owners.

## License

MIT. See [LICENSE](LICENSE).
