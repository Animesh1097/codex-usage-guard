# UI/UX quality policy

Load this only for interface work. The goal is not "make it prettier"; the goal is a coherent, intentional, production-ready interface that fits the product and survives real use.

## 1. Establish the design context before editing

First determine which register applies:

- **Product UI**: dashboard, CRM, admin, settings, forms, internal tools. Prioritize clarity, density, states, speed, and predictable interaction.
- **Brand / marketing UI**: landing page, campaign, portfolio, launch page. Prioritize narrative hierarchy, identity, composition, and memorable visual direction.

Then inspect the existing project before inventing anything:

- styling system and design tokens
- component library
- typography and icon family
- spacing and radius conventions
- color roles
- existing responsive behavior
- representative page/component

Preserve a coherent existing system when one exists. Do not introduce a second styling philosophy just to complete one task.

For a new or visually weak surface, write one short internal direction before coding: **who uses this, what is the primary action, and what should the interface feel like?** Use that to make choices instead of defaulting to generic SaaS patterns.

## 2. Shape hierarchy before decoration

Design the reading and action order first.

- The primary action should be obvious without competing CTAs.
- Group related content with spacing before reaching for borders or cards.
- Use shared alignment edges; stray edges create visual noise.
- Inter-group spacing should be visibly larger than spacing inside a group.
- Use progressive disclosure when secondary controls would overload the first view.
- Avoid turning every block into a card. Never nest cards simply to create hierarchy.
- Prefer composition, whitespace, scale, and typography over decorative containers.

For an existing project, improve in place. Do not rewrite the whole screen when targeted structural changes solve the problem.

## 3. Typography must carry hierarchy

Treat typography as interface structure, not decoration.

- Keep readable body text to a comfortable measure; long paragraphs should not span the whole viewport.
- Use a restrained type scale with clear role differences between display, section heading, body, label, and metadata.
- Use medium/semi-bold weights for hierarchy instead of only regular vs bold.
- Use tabular figures for tables, prices, counts, timers, or aligned numeric data.
- Balance large headings and use natural wrapping; avoid orphaned one-word final lines where possible.
- Do not over-tighten display tracking.
- Inputs must remain readable on mobile and at zoomed text sizes.
- Reuse the project's established font system unless redesign is explicitly requested.

## 4. Color must have meaning

Use color as a system of roles, not as decoration.

- Reuse established semantic tokens first.
- If a new system is required, define roles such as background, surface, text, muted text, border, primary action, destructive, warning, and success.
- Keep primary-action color scarce enough that it still means "act here."
- Verify text/background contrast, including muted text, placeholders, disabled states, and tinted surfaces.
- Avoid arbitrary multi-accent palettes.
- Avoid default purple/blue gradients, gradient text, or glass effects unless the product identity genuinely calls for them.
- Do not convert an existing stable color system to a different color notation merely because another notation is fashionable.

## 5. Surfaces and controls should feel engineered

Small geometry decisions compound.

- Controls must look interactive and static content must not accidentally look clickable.
- Use border, shadow, background, and elevation intentionally; do not stack all of them by reflex.
- Keep radii consistent with the system. Large soft radii on every card/section quickly become generic.
- Align icons optically when geometric centering looks wrong.
- Use one coherent icon family and compatible stroke weight.
- Keep touch/click targets comfortably large even when the visible glyph is small.
- Use a semantic z-index scale instead of arbitrary giant values.

## 6. Every important state must exist

For any changed interactive element, check the states that apply:

- default
- hover
- focus-visible
- active/pressed
- disabled
- loading
- empty
- validation
- error
- success
- partial data / long content
- permission or unavailable state

A beautiful happy path with missing states is unfinished product UI.

## 7. Accessibility is part of the design

Use platform semantics first.

- Use real buttons for actions and real links for navigation.
- Provide explicit form labels and useful error associations.
- Keep keyboard navigation and a visible focus indicator.
- Do not rely on color alone to communicate state.
- Give images meaningful alt text, or empty alt text when decorative.
- Prefer native behavior before custom ARIA.
- Check zoom/reflow and narrow viewports.
- Respect reduced-motion preferences.

## 8. Motion must explain, not decorate

Motion should reinforce cause/effect, hierarchy, or continuity.

- Prefer interruptible transitions for interactive state changes.
- Animate transform/opacity or other compositor-friendly properties when possible.
- Avoid global `transition: all`.
- Avoid bounce/elastic motion unless the product language specifically earns it.
- Do not make content depend on an entrance animation to become visible.
- Provide a reduced-motion path.
- Repeating the same reveal animation on every section is not a motion system.

## 9. Responsive behavior is a redesign, not a shrink

Stress the layout rather than simply reducing widths.

Check at minimum:

- wide desktop
- ordinary laptop
- narrow mobile
- long labels/content
- empty states
- overflowing tables/lists
- fixed/sticky elements
- menus, popovers, and modals
- keyboard focus and touch targets

On narrow screens, reprioritize and stack deliberately. Do not merely compress the desktop composition.

## 10. Anti-generic pass

Before calling the interface finished, actively look for generated-UI reflexes:

- identical card grids
- cards inside cards
- excessive soft shadows
- oversized rounded rectangles everywhere
- gradient text
- decorative grid/stripe backgrounds
- tiny uppercase tracked labels on every section
- giant hero metrics used as filler
- several competing accent colors
- every section using the same structure
- decorative motion with no information value
- generic copy that describes the interface instead of helping the user act

If the screen could plausibly belong to any SaaS product after swapping the logo, it needs another design pass.

## 11. Required quality loop

For UI work, do not stop after implementation.

1. **Inspect** the existing design system and relevant screen.
2. **Shape** hierarchy, primary action, and responsive behavior.
3. **Implement** the smallest complete change.
4. **Run deterministic UI audit** on changed UI files.
5. **Run project verification** (tests/typecheck/build when detected).
6. **Render in a browser** when browser tooling is available.
7. **Critique the rendered result**, not just the source code: hierarchy, alignment, spacing, wrapping, contrast, interaction states, and mobile behavior.
8. **Polish once** based on concrete defects found.
9. **Review the final diff** and stop.

Do not call a UI task complete merely because the code compiles or the build passes.
