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


## Visual verification matrix

For UI tasks where appearance is part of the requirement, verify the changed flow at representative widths rather than only one browser size:

- narrow mobile: approximately 360-390 px
- tablet / compact desktop: approximately 768-1024 px when relevant
- desktop: approximately 1280-1440 px

Do not mechanically screenshot every page. Verify only the changed flow and the states that could realistically break.

For each relevant viewport, look for:
- horizontal overflow
- clipped or overlapping text
- broken sticky/fixed elements
- menus/popovers leaving the viewport
- awkward line wrapping
- inconsistent spacing/alignment
- weak visual hierarchy
- missing loading/empty/error/validation states
- inaccessible focus behavior
- controls that become too small or ambiguous

If screenshots are available, use them for geometry and visual judgement. Use DOM/accessibility state for semantics and interaction correctness. Neither one alone proves the full UI is correct.


## Design-grade visual review

When `ui-brief` reports `visual_ambition: design-grade`, browser verification has two independent responsibilities:

1. **Functional evidence** — interaction, persistence, validation, focus, responsive mechanics.
2. **Aesthetic evidence** — composition, hierarchy, typography, color/material coherence, density, identity, and finish.

Do not collapse those into one "browser flow passed" statement.

For the aesthetic pass, capture or inspect at least:
- the primary desktop viewport;
- the primary narrow-mobile viewport;
- one state that exposes real product density (table/list/board/detail rather than only an empty screen).

On the first rendered pass, identify the three largest visual weaknesses. Correct those before spending time on minor polish. Re-render and critique again.

A deterministic source audit passing means **code hygiene passed**. It does not mean **visual quality passed**.
