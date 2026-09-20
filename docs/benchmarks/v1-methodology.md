# v1 benchmark methodology

Usage Guard must not claim savings from token estimates alone.

## A/B protocol

For each benchmark task:

1. start from the same repository commit
2. create two clean worktrees or clones
3. run baseline Codex and guarded Codex close together
4. avoid unrelated Codex activity during both runs
5. capture the same acceptance requirements
6. repeat with run order reversed when practical

## Measure

Record:

- task completion against explicit requirements
- test/build/lint/typecheck/browser verification results
- elapsed wall time
- changed-file count and diff stat
- retries / failed verification loops
- model turns
- same-thread input / cached-input / output / reasoning / total token deltas when available
- coarse 5-hour / weekly meter movement, clearly labeled as account-level and approximate
- user-visible regressions or unresolved risks

## Do not claim

Do not convert context estimates into exact Codex allowance savings.
Do not treat a global token delta as task-specific when concurrent Codex sessions were active.
Do not call one successful run statistically meaningful.

## Release gate

A v1 performance claim should require:

- at least 10 representative tasks
- at least two repetitions per condition
- correctness parity or better
- published raw benchmark fixtures/results
- median and spread, not only best-case numbers
