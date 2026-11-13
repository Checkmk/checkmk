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
