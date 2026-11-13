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
