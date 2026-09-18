# Context policy

The guard uses three context temperatures.

## Hot

Keep exact and immediately model-visible:

- current objective
- unresolved failures
- current changed files
- sensitive changed files
- exact code/error/path/stack/ID/hash/SQL/API/env-var details needed for the active step

## Warm

Keep compact state:

- completed actions
- recent evidence
- selected strategy/model/reasoning
- available deterministic verification commands
- file hashes and what changed since the previous snapshot

## Cold

Keep locally, not repeatedly in model context:

- full task event history
- stale logs
- superseded search output
- unchanged file content
- previous verbose test/build output

Use `guard.cmd capsule --task-id <ID>` to rebuild the compact state. Do not reread unchanged files unless the current hypothesis requires exact content.
