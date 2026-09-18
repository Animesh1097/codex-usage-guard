# Security Policy

Codex Usage Guard is a local developer tool that influences how Codex gathers context and chooses work. It is not a sandbox and must not be treated as a security boundary.

## What the project does

- reads local Git/repository metadata
- hashes changed files
- stores task state and telemetry under `~/.codex-usage-guard-data`
- installs a Codex Skill and custom agent profiles
- filters text output produced by tools

The guard does **not** execute the recommended project test/build/lint commands by itself. Codex remains responsible for tool execution under the user's existing Codex permission/sandbox settings.

## Reporting a vulnerability

Please use GitHub's private security reporting feature when available rather than opening a public issue with exploit details.

## Sensitive data

Do not place secrets in task descriptions or telemetry. Compression preserves exact error lines when possible, so secrets printed by an underlying command may remain in compressed output. Fix secret leakage at the command/application level rather than relying on the compressor to redact it.
