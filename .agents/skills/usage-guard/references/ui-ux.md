# UI/UX craft policy

Load this only for interface work.

## Before editing

1. Identify the screen's primary job and the user's main action.
2. Reuse the repository's existing tokens, components, spacing, and typography before inventing new ones.
3. Pick one coherent visual direction. Do not produce generic card grids, arbitrary gradients, or decorative chrome that does not support the task.
4. Preserve existing brand constraints unless the task explicitly asks for a redesign.

## Build requirements

- Use semantic elements and explicit form labels.
- Implement applicable hover, focus, active, disabled, loading, empty, validation, success, and error states.
- Keep keyboard navigation and visible focus.
- Respect reduced motion.
- Check long content, narrow widths, and touch targets.
- Prefer composition, hierarchy, spacing, typography, and contrast over extra decoration.
- Avoid repeating the same visual treatment on every section or card.
- Keep copy concise and task-oriented.

## Verification

For UI changes, source inspection alone is not enough when a browser is available.

1. Build or run the relevant app using repository-defined commands.
2. Exercise the changed path at desktop and narrow viewport sizes.
3. Check overflow, overlap, clipping, focus, validation, loading/error states, and the primary action.
4. Compare the rendered result to the user's screenshot or stated requirement when one exists.
5. Record concrete visual defects before another edit.

Do not call a UI task complete merely because the build passes.
