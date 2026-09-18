# Verification policy

Prefer the cheapest deterministic evidence that can prove the requirement.

Order of preference:

1. exact search / git status / targeted diff
2. targeted tests
3. type checking
4. build
5. lint when broad or sensitive changes justify it
6. production verification when the task explicitly changes production behavior
7. model review only when the checks above cannot establish correctness

Do not run every available check mechanically. Use the repository profile and the next-action predictor.

Before completion:

- every explicit user requirement is either verified or marked unresolved
- failing diagnostics are resolved or reported
- the final diff has been reviewed for accidental scope
- production/deployment tasks are verified against the live state when access exists
- no extra model turn is used only to restate deterministic results
