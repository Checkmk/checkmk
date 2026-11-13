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
