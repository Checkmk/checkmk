# Metabase performance graph queries

The `.sql` files in this folder are the **source queries for the Metabase
performance dashboards**. Each query is pasted into a Metabase question that
renders a graph (or, for a couple of them, populates a dashboard filter). The
files are kept here so the queries are version-controlled and reviewable
alongside the rest of the performance test suite; Metabase itself remains the
place where they are executed and visualised.

## Data model

The queries read from the performance results database (see the parent
[`README.md`](../README.md) for how it is created):

| Table        | Purpose                                                                                                                     |
| ------------ | --------------------------------------------------------------------------------------------------------------------------- |
| `jobs`       | One row per CI performance run. `job_name` is prefixed with the release (`3.0.0-…`); `start_timestamp` records when it ran. |
| `tests`      | Individual tests belonging to a job.                                                                                        |
| `scenarios`  | The performance scenario a test belongs to (the `test_*` function name).                                                    |
| `metrics`    | Sampled system-resource values per test, e.g. `cpu_info.cpu_percent`, `memory_info.virtual_memory_percent`.                 |
| `benchmarks` | Timing measurements per test; `metric_name = 'mean'` is the mean runtime in seconds.                                        |

## Metabase template variables

Some queries use Metabase's `{{ … }}` template syntax:

- `{{product_release}}` — text variable holding a release prefix (e.g. `3.0.0`),
  matched against `job_name` with `LIKE CONCAT({{product_release}}, '-%')`.
- `{{scenario_name}}` — a field filter that Metabase expands into a boolean
  condition selecting one scenario (used by the drilldown queries).

## The queries

**Filter queries** (populate dashboard dropdowns):

- `product_releases.sql` — distinct release prefixes, newest first → `{{product_release}}`.
- `scenario_names.sql` — the selectable performance scenarios → `{{scenario_name}}`.

**History graphs** — trend over the last 6 months for the selected release,
split into backend and UI (`test_performance_ui_*`) variants:

- `cpu_history.sql` / `cpu_history_ui.sql` — average CPU usage.
- `memory_history.sql` / `memory_history_ui.sql` — average memory usage.
- `runtime_history.sql` / `runtime_history_ui.sql` — average test runtime.

**Drilldown graphs** — a single release and scenario, overlaid with fixed
reference baselines for releases `3.0.0` / `2.5.0` / `2.4.0` / `2.3.0`:

- `cpu_history_drilldown.sql`, `memory_history_drilldown.sql`,
  `runtime_history_drilldown.sql`.

**Per-scenario snapshots** — the 3 most recent jobs of the selected release,
broken down by scenario:

- `scenario_cpu_usage.sql`, `scenario_memory_usage.sql`,
  `scenario_mean_runtime.sql`.

Each file also carries a short header comment describing what it produces.
