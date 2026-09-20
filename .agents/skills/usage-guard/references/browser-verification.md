# Browser verification policy

Use a real browser only when rendered behavior matters.

## Preferred order

1. Existing project E2E/browser test tooling.
2. Installed local Browser Harness for live DOM/browser checks.
3. Browser Use Cloud only when the user has explicitly opted in and a Browser Use API key is already configured.

Usage Guard itself must remain usable with no extra API key.

## Efficient browser loop

Use a small, indexed action space instead of free-form browsing:

- NAVIGATE
- CLICK observed target
- TYPE into observed target
- SELECT observed option
- SCROLL
- WAIT for a specific state
- VERIFY
- DONE
- BLOCKED

Only expose operations valid for the current page state. Prefer structured DOM/accessibility state over screenshots for routine steps. Use screenshots when visual geometry, alignment, clipping, or appearance is the requirement.

After every action, re-observe only the state needed for the next decision. Avoid sending whole pages, offscreen text, or repeated screenshots into model context.

## Safety and correctness

- Never turn model text into arbitrary selectors, shell commands, or executable browser JavaScript without validation.
- Re-resolve the target from the current page before acting.
- Verify the outcome independently before DONE.
- For authenticated personal work, prefer the user's local browser profile.
- Do not send credentials, cookies, session tokens, or hidden auth material into prompts or telemetry.

Browser Use Cloud is optional infrastructure, not a dependency of the core guard.
