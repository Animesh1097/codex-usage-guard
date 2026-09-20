# Usage Guard v1 architecture

## Decision

v1 moves toward a **Rust deterministic core + Tauri visual companion**, while the Python implementation remains the compatibility runtime during migration.

The split is deliberate:

- **Core is authoritative and non-visual.**
- **Visualizer is read-only and non-critical.**
- If the visualizer crashes, is disabled, or cannot open, guarded work continues.
- Normal `$usage-guard` execution remains in the user's current Codex session.
- Model/reasoning changes remain opt-in only.

This follows the strongest pattern from the research: compiled developer tools reduce installation/runtime friction, while Tauri provides a modern web-rendered UI without requiring an Electron-sized bundled browser.

## Target repository layout

```text
crates/
  usage-guard-core/       deterministic policy/state/verification engine
apps/
  visualizer/
    web/                   HTML/CSS/JS visual layer
    src-tauri/             thin read-only desktop shell
guard/                     Python compatibility runtime during migration
fixtures/                  cross-runtime policy/eval fixtures
docs/
  architecture/
  benchmarks/
```

## Core boundary

The Rust core should ultimately own:

1. task/repository signals
2. complexity/risk policy
3. action/model-turn/retry budgets
4. task phases
5. deterministic next-action logic
6. task state schema + migrations
7. verification policy
8. output compression primitives
9. local usage accounting adapters
10. extension capability contracts

It must not own presentation.

## Visual companion boundary

The Tauri companion receives a **small read-only task snapshot**:

```text
taskId
objective
status
phase
activity
taskKind
actionsUsed / actionsLimit
turnsUsed / turnsLimit
tokenDelta
updatedAt
```

It intentionally does not receive Codex auth files, cookies, hidden credentials, or model-routing internals.

## Migration rule

No big-bang rewrite.

Each Rust subsystem must reach fixture parity with the Python implementation before Python delegates that subsystem to Rust. The Python path remains available until the Rust replacement has:

- unit tests
- fixture parity
- cross-platform CI
- failure fallback
- migration documentation

## Current alpha slice

Implemented in this branch:

- Rust policy/budget/next-action primitives
- shared policy fixtures
- Tauri v2 visual companion scaffold
- modern CSS/DOM workflow scene
- read-only state snapshot command
- Python launcher preference for a compiled visualizer when installed
- Tkinter fallback retained

The compiled visualizer is not yet shipped by the stable installer. Distribution is the next migration slice.
