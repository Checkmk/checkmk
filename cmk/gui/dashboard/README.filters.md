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
