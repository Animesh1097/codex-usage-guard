# Routing policy

Use the plan returned by `guard.cmd start`.

- `guard_fast`: small, obvious, low-risk work. Luna, low reasoning.
- `guard_worker`: normal implementation and debugging. Terra, medium/high reasoning.
- `guard_reasoner`: ambiguous, cross-system, or high-risk work. GPT-5.6, high reasoning.
- `guard_reviewer`: read-only independent review only when deterministic checks cannot establish correctness.

Rules:

1. Keep one worker by default.
2. A spawned agent receives the objective, state capsule, and only the minimum repository evidence required.
3. Do not forward the parent transcript.
4. Do not escalate because a task is merely long. Escalate when ambiguity, risk, or failed evidence requires it.
5. A retry must have a changed hypothesis or new evidence.
6. When the budget is exhausted, stop the loop and reassess instead of continuing automatically.
