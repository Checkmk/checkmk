## Layouts

- Every dashboard uses one of two layouts: anchored or responsive.
- The responsive layout exists only in the commercial editions.
- In the dashboard model, the layout type is `relative_grid` for anchored and
  `responsive_grid` for responsive.

### Anchored

- Widgets sit on a grid of cells that covers the whole dashboard.
- The cells have a fixed size, so the size of the dashboard decides how many
  there are.
- Each widget is anchored to one corner of the dashboard, and its position
  counts cells from that corner.
- When the window size changes, a widget keeps its distance to its corner.
- On a dashboard too small for its widgets, a widget can lie partly or wholly
  outside the dashboard.
- Width and height are each a number of cells, `auto` or `max`.
- `max` stretches the widget to the opposite edge of the dashboard.
- `auto` lets the widget grow into the free space next to it.

Code:

- `components/RelativeGrid/utils.ts`: corner anchoring and stretching

### Responsive

- The dashboard is a grid of columns with a fixed row height.
- Breakpoints map the width of the dashboard to a number of columns.
- Each widget has its own position and size for every breakpoint.
- Widgets snap to the columns and move up to close gaps.

Code:

- `components/ResponsiveGrid/ResponsiveGrid.vue`: the grid
- `api/model/constants.py`: the breakpoints

### One split through the whole stack

- Each layout has its own grid component in the frontend.
- Each layout has its own group of REST endpoints for creating, loading, saving
  and cloning a dashboard.
- Deleting a dashboard, the dashboard metadata and constants, and the widget
  content do not depend on the layout and are shared.

Code:

- `components/DashboardComponent.vue`: picks the grid for the dashboard's layout
- `api/` and `cmk/gui/nonfree/pro/dashboard/api/`: the anchored and the
  responsive endpoint groups

### Cloning into the responsive layout

- Cloning across layouts works in one direction only: from anchored to
  responsive.
- A responsive dashboard can only be cloned as a responsive one.
- For the anchored to responsive clone, the browser works out the responsive
  positions from the anchored dashboard as it is currently rendered.
- The clone action of the responsive endpoints then stores the copy with those
  positions.

Code:

- `dashboardMigration.ts`: computes the positions
- `cmk/gui/nonfree/pro/dashboard/api/clone_from_relative_dashboard.py`: stores
  the copy

### Widget size constraints

- Each widget type has an initial and a minimum size for each layout.
- The backend defines them, and both grids use them while editing.

Code:

- `dashlet/base.py`: the defaults, which each widget type overrides
