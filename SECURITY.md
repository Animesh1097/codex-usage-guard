# Security Policy

Codex Usage Guard is a local developer tool that influences how Codex gathers context and chooses work. It is not a sandbox and must not be treated as a security boundary.

## What the project does

- reads local Git/repository metadata
- hashes changed files
- stores task state and telemetry under `~/.codex-usage-guard-data`
- installs a Codex Skill and custom agent profiles
- filters text output produced by tools
- keeps normal `$usage-guard` work in the user's current Codex session
- can launch one pinned `codex exec` worker only when the user explicitly opts into the advanced routing path

Normal Usage Guard operation does not change the user's model or reasoning mode.

For the optional advanced pinned-worker path, Codex's `workspace-write` sandbox and non-interactive `approval_policy="never"` are used. Usage Guard never enables Codex's dangerous approval/sandbox bypass flag. Commands that require permissions outside the worker sandbox should fail rather than silently bypass the sandbox.

The guard does not read or copy Codex authentication files or hidden session credentials. The optional pinned worker relies on the existing Codex installation and sign-in. Parent `CODEX_THREAD_ID` and `CODEX_USAGE_GUARD_*` environment values are removed before an advanced worker is launched so worker routing is not confused with the coordinator task context.

## Reporting a vulnerability

Please use GitHub's private security reporting feature when available rather than opening a public issue with exploit details.

## Sensitive data

Do not place secrets in task descriptions or telemetry. Compression preserves exact error lines when possible, so secrets printed by an underlying command may remain in compressed output. Fix secret leakage at the command/application level rather than relying on the compressor to redact it.
