# Graph accessibility aspects for E2E testing

This catalogues the accessibility (a11y) aspects relevant to testing the graph
surfaces, and flags which ones need explicit support from the foundation later
(i.e. once the graph component exposes a stable selector/hook contract).

The new graph is a two-layer composite: axes, grid and labels are **SVG** and the
legend is **DOM** (both readable by assistive tech and by tests), while the data
curves are drawn to a **canvas**. So most a11y information lives in the DOM/SVG;
only the curve geometry is opaque and must be covered by an accessible
name/summary on the canvas.

## Aspects

| #   | Aspect                           | What to verify                                                                                                                                               | Needs foundation support later?                                                                           |
| --- | -------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------- |
| 1   | Text alternative for the canvas  | The canvas curves expose an accessible name/description (`aria-label` / `role="img"` or a text summary) so the plotted data is not opaque to screen readers. | **Yes** — the canvas has no accessible name today; depends on the component adding one.                   |
| 2   | Data summary in the DOM          | Key values (min/avg/max/last) are real text in the legend, and axis labels are SVG `<text>` — not only painted on the canvas.                                | **Available (new engine)** — the legend renders the stats and axis labels are SVG; assert directly.       |
| 3   | Keyboard operability of controls | Controls (legend show/hide, consolidation function, time-range, zoom/pin) are reachable and operable by keyboard, not mouse-only.                            | **Partly available** — legend controls are real `<button>`s; time-range/zoom controls need the component. |
| 4   | Focus management in containers   | When a graph appears in a popup, slide-in, or designer preview, focus moves into and is trapped/returned correctly.                                          | Partial — container focus handling is shared; graph-specific focus order needs the component.             |
| 5   | Color contrast & non-color cues  | Curves/legend meet contrast expectations and series are distinguishable without relying on color alone.                                                      | **Yes** — needs the component's rendered styling/markup to inspect.                                       |
| 6   | Reduced motion                   | Any graph animation respects `prefers-reduced-motion`.                                                                                                       | **Yes** — depends on the component honoring the media query.                                              |
| 7   | Error/empty/loading states       | Broken-graph, no-data, and loading states are announced (e.g. `role="alert"` / `aria-live`), not silent.                                                     | **Yes** — ties to the data-request control skeletons in `interactions.py`.                                |
| 8   | Embedded-context labelling       | In dashboard widgets, the graph's accessible name disambiguates it from sibling widgets.                                                                     | Partial — widget labelling exists; confirm per-graph naming.                                              |
| 9   | Theme parity (light & dark)      | The graph renders in both light and dark themes, keeping the existing color palettes and adequate contrast (R1.2 requires both themes are preserved).        | **Yes** — depends on the component's theming; render in each theme and compare.                           |

## Notes

- Items marked **Yes** cannot be finalized until the new graph component exposes
  a stable selector/hook contract; they are the a11y counterparts of the
  `inspect_rendered_output` / `assert_old_engine_unused` skeletons in
  `pom/graphing/interactions.py`.
- Items marked **Available / Partly available** can be exercised against the new
  SVG/DOM markup now (legend, axis labels); the canvas-only parts wait on the
  component.
- Writing the a11y assertions themselves is out of scope for this foundation.
- Skipped skeletons for these aspects live in
  `tests/system/gui/test_graph_accessibility.py` (CMK-35973): aspects 1, 3-8 each have a
  skeleton there. Aspect 2 is covered by `LT-01`; aspect 9 (theme parity) has no test -
  its skeletons were dropped along with `test_graph_rendering_engine.py`.
