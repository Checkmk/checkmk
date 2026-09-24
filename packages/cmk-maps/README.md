# cmk-maps

The Checkmk Maps feature, with its Python vertical kept self-contained in a
single package (the Vue SPA lives in `cmk-frontend-vue`, see below):

- `cmk.maps.backend` — the FastAPI daemon (served by gunicorn/uvicorn inside the
  OMD site behind the site Apache) that resolves maps and streams live host/
  service states. `cmk.maps.shared` is the pure GUI↔daemon domain layer
  (no framework deps) that the GUI is allowed to import.
- `cmk.maps.gui` — the GUI integration: permissions, settings pages, the package's
  own `ConfigDomainMaps` config domain and the session-authenticated AJAX
  endpoints backing the SPA.
- `cmk.maps.rest_api` — the versioned REST API endpoints for maps.

The Vue **SPA** is not in this package: it lives in `cmk-frontend-vue`
(`packages/cmk-frontend-vue/src/maps`), is built into that shared bundle and
mounted as the `cmk-maps` web component (reusing cmk-frontend-vue's design
system and form engine directly). There is no separate frontend artifact here.

## Responsibilities (daemon)

- **Maps & states** — resolves map configuration and streams live host/
  service states from Livestatus (per-map SSE broadcast).
- **Images** — serves built-in icons and uploaded map images.
- **Connections** — provides the data-source connections used by maps.
- **Metrics** — ships the raw data only: `perf_data`/`check_command` ride the
  state stream, RRD history comes from the `metric-history` endpoint. Display
  semantics (Perf-O-Meter, units, titles, graph groups) are resolved GUI-side
  by the `maps_metric_info` endpoint (`cmk.maps.rest_api.internal`, backed by
  `cmk.maps.gui`); the daemon imports no `cmk.gui` code (see
  `module_layers.toml`).

## Authentication

The daemon performs no login, session or password handling of its own. Every
request is authenticated by a signed ticket minted by `cmk.maps.gui` and
verified in `cmk.maps.backend.core.auth` using the site-internal secret. The
GUI↔daemon ticket contract is pinned by
`tests/unit/cmk/gui/maps/test_ticket_contract.py`.

## Built-in icons

`cmk/maps/gui/builtin_icons` is the outline subset of [Tabler
Icons](https://tabler.io/icons) 3.45.0, vendored unchanged under the MIT
license (`cmk/maps/gui/builtin_icons/LICENSE`, shipped with the icons) and
listed in `omd/dependency_management/manual_dependency_manifest.yml`.

## Packaging

The package ships as one wheel (`:wheel`, bundling `backend`, `gui`, `rest_api`
and the shared layer) plus an OMD skel tar (`:omd_skel_tar`, init.d/apache/
logrotate/gunicorn config) wired into all five editions in `omd/BUILD` —
community, pro, ultimate, ultimatemt and cloud. Unlike NagVis (excluded from
cloud), Maps ships in the cloud edition too.

## Development

Build and test via Bazel:

```
bazel build //packages/cmk-maps:wheel
bazel test //packages/cmk-maps/tests/unit:unit
```
