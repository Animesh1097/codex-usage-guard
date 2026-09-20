# Third-party research and attribution

Codex Usage Guard is independently implemented. The v0.4 design was informed by public projects and documentation; their source code is not vendored unless explicitly stated.

## OpenAI Codex

- Repository: https://github.com/openai/codex
- Relevant ideas: native model/reasoning selection, local thread state, token/rate-limit telemetry, skills, and deterministic tool workflows.
- No Codex source code is copied into this repository.

## Browser Use

- Browser Use: https://github.com/browser-use/browser-use — MIT
- Browser Harness: https://github.com/browser-use/browser-harness — MIT
- Jev Ultrafast: https://github.com/browser-use/jev-ultrafast — MIT
- BrowserCode: https://github.com/browser-use/browsercode — MIT

Ideas adapted: real-browser verification, structured page observations, small valid action spaces, independent completion checks, and optional cloud-browser infrastructure. No Browser Use code is vendored.

## Agent skill ecosystems

- wshobson/agents: https://github.com/wshobson/agents — MIT
- mblode/agent-skills: https://github.com/mblode/agent-skills — MIT
- arvindand/agent-skills: https://github.com/arvindand/agent-skills — MIT
- anthropics/skills: https://github.com/anthropics/skills — repository-specific license terms

Ideas adapted: progressive disclosure, narrow skill activation, UI/accessibility review checklists, design-system awareness, and separating product/visual/verification concerns. Usage Guard's reference files are original condensed guidance; Anthropic skill text is not vendored.

## UI quality research

- AI UX Playground skill catalog: https://aiuxplayground.com/skills/
- Impeccable: https://github.com/pbakaus/impeccable — Apache-2.0
- Jakub Krehel design skills: https://github.com/jakubkrehel/skills — MIT
- Taste Skill: https://github.com/Leonxlnx/taste-skill — MIT
- Vercel Web Interface Guidelines: https://github.com/vercel-labs/web-interface-guidelines — MIT

Ideas adapted: preserve the incumbent design system, distinguish product UI from brand/marketing surfaces, shape hierarchy before decoration, audit layout/typography/color/accessibility as separate concerns, use explicit anti-generic checks, verify rendered states, improve existing projects in place, and keep deterministic source checks separate from visual judgement.

Usage Guard does not vendor these skills. Its UI reference and detector rules are independently written, intentionally smaller, and loaded only for UI-relevant tasks.

## Usage telemetry research

- qianhaoq/codex-usage: https://github.com/qianhaoq/codex-usage — MIT
- mryll/codexbar: https://github.com/mryll/codexbar — MIT

Ideas adapted: read-only inspection of Codex's local state database and rollout telemetry. Usage Guard never reads or forwards Codex auth tokens and never calls private usage endpoints.
