# Dashboards

- A dashboard is a page of widgets placed on a layout.
- The dashboard page renders the Vue web component `cmk-dashboard` and passes
  it the page properties.
- The frontend talks to the backend through the internal REST API, in the
  endpoint family "Dashboards".

| Part                         | Path                                      |
| :--------------------------- | :---------------------------------------- |
| Backend, all editions        | `cmk/gui/dashboard`                       |
| Backend, commercial editions | `cmk/gui/nonfree/pro/dashboard`           |
| Frontend                     | `packages/cmk-frontend-vue/src/dashboard` |

- Backend paths in this README are relative to `cmk/gui/dashboard`, frontend
  paths to `packages/cmk-frontend-vue/src/dashboard`.
- Python code calls widgets _dashlets_.
- The commercial editions add the responsive layout and more widget types.
- Ultimate, Ultimate MT and Cloud add built-in dashboards of their own, in their
  packages under `cmk/gui/nonfree`.

Code:

- `page_show_dashboard.py`: the dashboard page
- `packages/cmk-frontend-vue/src/main.ts`: registers the web components

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

## Filters

- Dashboards use the same filters as views, from one registry.
- The frontend loads the filter definitions and filter groups through the REST
  API.

Code:

- `cmk/gui/visuals/filter`: the registry and its REST endpoints
- `packages/cmk-ui-library/components/filter`: the filter inputs

### Filter levels

- Dashboard filters are stored with the dashboard and apply to all its widgets.
- Runtime filters are set by the viewer and apply to all widgets too.
- Widget filters are stored with the widget and apply to it only.
- The frontend combines the three levels into each widget's _effective filter
  context_.
- A widget filter replaces a dashboard or runtime filter with the same ID.
- `host` and `hostregex` count as the same filter here, as do `service` and
  `serviceregex`.

Code:

- `components/DashboardComponent.vue`: the effective filter context of each
  widget

### Runtime filters

- Runtime filters live in the URL and are never stored.
- When a dashboard page loads, the filters in its URL become runtime filters.
- Applying runtime filters writes them back into the URL.
- In `merge` mode, a runtime filter replaces the dashboard filter with the same
  ID.
- In `override` mode, the runtime filters replace all dashboard filters.
- A dashboard can make runtime filters mandatory.
- Until the viewer has set all mandatory runtime filters, the widgets ask for
  them instead of loading data.

Code:

- `composables/useDashboardFilters.ts`: dashboard and runtime filters, and the
  URL

### Infos

- Each widget type declares the _infos_ it works on, such as `host` or
  `service`.
- Only the filters of these infos apply to the widget.
- A widget type can also require exactly one object of an info, for example a
  single host.
- If the effective filter context does not name that object, the widget shows a
  warning instead of data.
- In the frontend, these show up as `uses_infos` and `restricted_to_single`.

Code:

- `dashlet/base.py`: the defaults, which each widget type overrides

### Evaluation

- The browser sends the effective filter context with each compute request.
- The backend turns it into Livestatus filter headers.
- An embedded view gets the effective filter context in the URL of its page.
- A URL widget adds it to its URL only if its `include_context` option is set.

### Shared dashboards

- A shared dashboard has no runtime filters.
- Its page carries the filter IDs without their values.
- The IDs are enough to tell when a required filter is missing.
- For each compute request, the browser sends only the widget ID.
- The backend merges the stored dashboard and widget filters itself.
- There too, a widget filter replaces the dashboard filter with the same ID.
- Unlike in the frontend, `host` and `hostregex` count as different filters, as
  do `service` and `serviceregex`.

Code:

- `page_show_shared_dashboard.py`: removes the filter values
- `api/_widget_resolution.py`: merges the stored filters

### Making a widget type filterable

1. In the widget type's dashlet class, return the infos the widget works on
   from `infos()`.
2. If the widget needs exactly one object of an info, also return that info
   from `single_infos()`.
3. In the compute endpoint, get the widget with its effective filter context
   and infos from `resolve_widget`.
4. Turn them into Livestatus filter headers with `visuals.get_filter_headers`.
5. In the frontend, fetch the data with `useComputedWidget`.

- The steps work unchanged on a shared dashboard: `useComputedWidget` sends
  only the widget ID, and `resolve_widget` merges the stored filters.
- `useComputedWidget` fetches again when the filters change.

Code:

- `api/compute_stats.py`: steps 3 and 4 for the statistics widgets
- `components/DashboardContent/figures/DashboardContentStats.vue`: step 5 for
  the same widgets

### Changing how filters combine

- `composables/useDashboardFilters.ts` combines the dashboard and runtime
  filters for a logged-in user.
- `components/Wizard/components/FiltersRecap/utils.ts` adds the widget filters.
- On a shared dashboard, `api/_widget_resolution.py` combines the stored filters
  in the backend instead.
- Change the rule in the frontend and the backend together.

## Drill-down and drill-up

- A click on an element of a widget, such as a host in a list, can open a view
  or a dashboard filtered to that element.
- The page reached this way offers a way back to the page the click came from.

### Contextual links

- A widget's _contextual link_ decides where a click on one of its elements
  leads.
- Its mode is `none`, `default`, `inherited` or `custom`.
- `none` links nowhere.
- `default` links to the widget type's built-in target.
- `inherited` links to one view or dashboard and carries only what the clicked
  element identifies.
- `custom` offers one or more links, each to a view or dashboard with its own
  filters.
- A link can also carry the widget's effective filter context.
- A link can also carry the dashboard's time range.
- A link names its target, and each viewer opens the copy that name resolves to
  for them.
- The modes and filters a widget type offers follow from the type of its
  `contextual_link` field in the API model.

Code:

- `api/model/contextual_link.py`: the modes, the offered options and the
  validation

### The filters a link carries

- Each filter a link carries is valued from the clicked element, for example
  its site, host name or service state.
- Which filters a click can value depends on what was clicked: one host, one
  service, or an aggregate of hosts or services.
- A filter the element cannot value is dropped.
- If the link carries the effective filter context and that context has the
  filter, the filter travels from there and is not dropped.
- If the element lacks one key of a filter, only that key is dropped.
- A deferred filter is valued only when the link is opened.
- The URL tells the target page which filters were dropped and why.

Code:

- `api/model/context_filters.py`: the filters for each kind of click

### Link URLs

- With each element, the compute endpoint returns the encoded filter values for
  each of the widget's links.
- The browser builds the URL of the target page from them.
- A filter valued from the clicked element replaces the same filter from the
  effective filter context.

Code:

- `api/_contextual_link_encoding.py`: the encoded filter values of an element
- `lib/contextualLinkUrl.ts`: the URL of the target page

### Column links of embedded views

- Each column of an embedded view can link to a view or dashboard as well.
- The backend builds these URLs while it renders the view, from the row of the
  clicked cell.

Code:

- `view_drilldown.py`: the URLs of the column links

### Drill-up

- A drill-down URL carries the title of the page it left.
- The target page then shows a button back to that page in its header.
- The button shows only when a click on a page of the same site led here. A
  pasted, typed or bookmarked link shows none.
- The button goes back in the tab's history.
- If the drill-down opened a new tab, the button leads to the referring page of
  the same site instead.
- For a column link in an embedded view, the dashboard hands the view its own
  URL, so the way back leads to the dashboard.

Code:

- `cmk/gui/top_heading.py`: adds the button to the target page
- `packages/cmk-frontend-vue/src/page-header/drillUp.ts`: where the button
  leads

### Giving a widget type contextual links

1. Type the content model's `contextual_link` field with `ContextualLinkSpec`
   and the filters its clicks can value, or with
   `TargetlessContextualLinkSpec` if the type has no built-in target.
2. Pass the widget type's built-in link, or `no_built_in_link`, to
   `resolve_widget` in the compute endpoint.
3. Build the compute endpoint with `link_targets=True`.
4. Return the widget's links, and each element's link properties from
   `link_properties_for`.
5. In the frontend, wrap each clickable element in `ContextualLinkTrigger`.

Code:

- `api/compute_stats.py`: steps 2 to 4 for the statistics widgets
- `components/figures/CmkStatsFigure.vue`: step 5 for the same widgets

## Shared dashboards

- A share link opens one dashboard without a login.
- Everything on a shared dashboard is computed as the user who created the
  link.

### Share links

- A dashboard has at most one share link.
- A share link can have an expiry date and a comment, and can be disabled.
- The community edition limits how long a share link stays valid.
- Saving a dashboard disables its share link.
- A share link is also disabled when it no longer resolves to what it was
  created for, for example when its creator lost access to the dashboard.

Code:

- `token_util.py`: creating, changing and disabling the token
- `api/token_*.py`: the REST endpoints for share links

### Token pages

- The pages a share link opens are registered apart from the normal pages.
- They read the token from the `cmk-token` URL variable.

Code:

- `cmk/gui/token_auth`: the page registry and the token store

### The shared dashboard page

- The page renders the Vue web component `cmk-shared-dashboard`.
- It computes the widget titles beforehand and passes them in its page
  properties.
- It also discovers the graphs of the graph widgets beforehand.
- It removes all filter values from the dashboard it passes on, and keeps the
  filter IDs.
- It checks at intervals whether its token is still valid, and reloads when it
  is not.

Code:

- `page_show_shared_dashboard.py`: the page
- `DashboardSharedApp.vue`: the frontend app

### Widget requests

- A widget request sends only the widget ID, with the token in the
  `Authorization` header as `CMK-TOKEN`.
- The backend takes the widget from the stored dashboard.
- A request that sends a widget configuration together with a token is
  refused.
- Graph widgets fetch their data through a dashboard endpoint of their own that
  takes only the widget ID.
- An embedded view loads its page with only the widget ID and the token.
- Compute endpoints built with `widget_compute_endpoint` accept tokens unless
  they pass `shared_dashboards=False`.

Code:

- `composables/useWidgetSource.ts`: what a request sends
- `api/_widget_resolution.py`: how the backend resolves the widget

## Widgets

- Each widget type has a class in the backend, a content model in the REST API
  and a Vue component that renders it.

### Widget types

- The backend classes are registered in the dashlet registry.
- Each class declares the widget's infos and its size constraints for both
  layouts.
- The content models form one union, told apart by their `type`.
- The frontend picks the component for a content `type` in one place.

Code:

- `api/model/widget_content/`: the content models
- `components/DashboardContent/DashboardContent.vue`: picks the component

### Widget data

- A widget type that needs data from the backend gets it from a compute
  endpoint of the REST API.
- The browser sends the widget's content and its effective filter context, and
  gets back what to draw.
- The frontend fetches again when the content or the filters change, and on
  every refresh tick of the dashboard.
- Widget types whose compute endpoint takes a time range send the dashboard's
  time range with each request.
- Such a widget also fetches again when the dashboard's time range changes, if
  it follows that range.
- Graph widgets render their graphs in the browser and get them through the
  graph endpoints of the REST API.
- The backend computes the widget titles.

Code:

- `api/_compute_endpoint.py`: how compute endpoints are built
- `composables/useComputedWidget.ts`: the fetch in the frontend

### Embedded pages

- Some widgets show a page in an iframe instead of computed data.
- The URL widget shows any URL.
- It adds the effective filter context and the dashboard's time range to the
  URL if its options ask for them.
- The view widgets show a Checkmk view: a stored view by name, or a view
  defined in the dashboard.
- They load the embedded view page and pass it the effective filter context in
  the URL.
- On a shared dashboard, they load the token variant of that page instead.
- The sidebar element widget shows an element of the sidebar.
- The dashboard sends its time range to every embedded page as a message.
- In the embedded view page, the `cmk-dashboard-time-follower` component
  applies that time range and reloads the view on each refresh tick.

Code:

- `components/DashboardContent/DashboardContentIFrame.vue`: the iframe of every
  embedded page
- `page_view_widget.py`: the embedded view pages

### Adding a widget type

1. Add a widget type class under `dashlet/dashlets/`, or in the commercial
   package, and register it in the dashlet registry.
2. Add the content model under `api/model/widget_content/`, and add it to the
   content union and the list of content types in that package's
   `__init__.py`.
3. If the widget needs data from the backend, add a compute endpoint built with
   `widget_compute_endpoint`.
4. Register the endpoint in the package's `api/_registration.py`.
5. Add a component under `components/DashboardContent/` and pick it for the new
   `type` in `DashboardContent.vue`.
6. Fetch the data in the component with `useComputedWidget`, or with
   `useRangedComputedWidget` if the compute endpoint takes the dashboard's time
   range.

- The frontend's API types are generated from the internal REST API
  specification during the build, so the new content model needs no extra
  step.

Code:

- `api/compute_stats.py`: a compute endpoint
- `components/DashboardContent/figures/DashboardContentStats.vue`: its
  component
