# Contributing

Usage Guard is moving toward a compiled core with a non-critical visual companion.

## Principles

- preserve current-session Codex execution by default
- deterministic checks before additional model work
- no credential scraping or hidden auth forwarding
- no mandatory paid API/service dependency
- visual failures must never stop the core guard
- claims about token/allowance savings require reproducible benchmark evidence
- keep task-specific guidance progressively disclosed

## Before opening a PR

Run:

```bash
python -m unittest discover -s tests -v
python scripts/benchmark.py
cargo test -p usage-guard-core
```

If you touched the Tauri visualizer, also run a platform-appropriate Cargo check/build for `apps/visualizer/src-tauri`.

Keep changes focused and include tests for behavior changes.
