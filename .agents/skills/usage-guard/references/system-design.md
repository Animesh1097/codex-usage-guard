# System design policy

Load this only for architecture, backend, data-model, migration, security, or cross-system work.

## Define the boundary

Write down only what matters for the requested change:

- actors and entry points
- data ownership
- read/write path
- trust boundaries
- external dependencies
- failure and retry semantics
- persistence and migration impact

Do not redesign the whole system when a local change is sufficient.

## Decision order

1. Preserve existing architecture unless it blocks the requirement.
2. Prefer one clear source of truth.
3. Minimize new services, queues, abstractions, and dependencies.
4. Make idempotency and retry behavior explicit for side effects.
5. Treat schema changes as compatibility changes: rollout, backfill, rollback.
6. Treat authentication, authorization, billing, secrets, and production data as high risk.
7. State important tradeoffs rather than hiding them behind patterns.

## Verification

Use the cheapest evidence that proves the design is implemented correctly:

- schema or contract tests
- focused unit/integration tests
- type checks
- build
- migration dry-run or validation
- production verification only when the task actually changes production

A design diagram or prose plan is not verification.
