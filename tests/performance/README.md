# Performance tests

How to add a performance test, what it measures, what ends up in the performance database and
where it shows up in the graphs.

> **On the 2.5.0 branch** only the site suite exists. There are no component suites, no
> `tests/performance/testlib/`, no Bazel targets below `tests/performance/` and no
> `tests/run_tests.sh`: CI runs the site suite with `make -C tests test-performance`. The parts
> about component suites describe the master branch.

- [Where does my test go?](#where-does-my-test-go)
- [Adding a scenario to the site suite](#adding-a-scenario-to-the-site-suite)
- [Adding a component suite](#adding-a-component-suite)
- [Measuring: runtime and resources](#measuring-runtime-and-resources)
- [What ends up in the database](#what-ends-up-in-the-database)
- [Baseline checks](#baseline-checks)
- [Graphs](#graphs)
- [Running the tests locally](#running-the-tests-locally)
- [Checklist](#checklist)

## Where does my test go?

Ask one question: **does the thing I measure need a running site?**

- **Yes** (activation, REST calls, the core, the GUI in a browser, DCD, ...): add a scenario to
  the **site suite** in `tests/performance/system/<feature>/`. `perftest.sh` runs it with
  pytest on real sites; CI: `make -C tests test-performance`.
- **No** (a library, a query engine, a GUI page rendered in-process against fakes, ...): write
  a **component suite** in `tests/performance/component/<feature>/`. Bazel runs it as part of
  `//tests/performance:bazel_performance`; CI: `tests/run_tests.sh test-performance-all`. A
  package can keep its suite in `<package>/tests/performance/`, as the data backend does.

Measuring in-process is cheaper and less noisy. Measuring on a site covers the installed
product. If the site's number is what matters, measure on the site.

Both write the same result files. `perftest_upload.sh` uploads them through
`reporting/perftest_run.py`, which names the run's job. The site suite goes into the
`performance` database and a failed baseline check only warns. The component suites go into
`performance_component` (the data backend into `performance_data_backend`) and a failed check
fails the job.

Helpers for all suites go to `tests/performance/testlib/`, helpers for the site scenarios only
to `tests/performance/system/perftest.py`. `sysmon.py` and `benchmark_json.py` stay at the top
level, as packages use them too.

## Adding a scenario to the site suite

A scenario is a package with three files:

```
tests/performance/system/rules/
├── __init__.py   empty
├── scenario.py   the work being measured
└── test_rules.py the test: fixtures, benchmark, resource tracking
```

**`scenario.py`**: plain functions that take the shared `PerformanceTest` first. Like a test
module, it shows the values of a failing assertion.

```python
from tests.performance.system.perftest import PerformanceTest


def scenario_create_and_delete_rules(perftest: PerformanceTest) -> None:
    """Scenario: Bulk rule creation

    Create 100 rules on the central site, activate, delete them, activate."""
    ...
```

**`test_rules.py`**: one test per measured scenario.

```python
from functools import partial

import pytest
from pytest_benchmark.fixture import BenchmarkFixture

from tests.performance.system.perftest import PerformanceTest
from tests.performance.system.rules import scenario


@pytest.mark.usefixtures("track_system_resources")
def test_performance_rules(perftest: PerformanceTest, benchmark: BenchmarkFixture) -> None:
    """Bulk rule creation"""
    benchmark.pedantic(  # type: ignore[no-untyped-call]
        partial(scenario.scenario_create_and_delete_rules, perftest),
        rounds=perftest.rounds,
        iterations=perftest.iterations,
    )
```

That is all: `perftest.sh` runs everything under `system/`.

The fixtures:

- `perftest`: a `PerformanceTest` on one site; `perftest_dist`: on a central site with two
  remote sites.
- `single_site`, `central_site`, `remote_site`, `remote_site_2`: the sites, created once per
  session.
- `track_system_resources`: samples the machine's resources during the test (see
  [below](#measuring-runtime-and-resources)).
- `benchmark`: pytest-benchmark's timer.

`PerformanceTest` (`system/perftest.py`) holds the sites, the command-line knobs (`rounds`,
`iterations`, `object_count`, ...) and helpers shared by several scenarios, e.g. bulk host
creation or a logged-in browser page.

### Naming

- Name GUI page tests `test_performance_ui_*`, which the graphs show apart, and other tests
  `test_*`, as usual.
- **Renaming a test starts a new history**, unless you rename its scenario in the database
  too. The upload finds the scenario by the test's name, with its parameter id (e.g.
  `test_performance_ui_response[login]`) and any dot in it as a hyphen. In each database the
  suite uploads to:

  ```sql
  UPDATE scenarios SET scenario_name = '<new>' WHERE scenario_name = '<old>';
  ```

- The docstring is stored as the scenario's description.

## Adding a component suite

1. Write the tests with the `benchmark` fixture.
2. Add a `track_system_resources` fixture to the suite's `conftest.py`, or nothing gets
   uploaded:

   ```python
   from tests.performance.sysmon import track_resources


   @pytest.fixture(name="track_system_resources")
   def _track_system_resources(request: pytest.FixtureRequest) -> Iterator[None]:
       with track_resources(request.node.name):
           yield
   ```

3. Add a `py_cmk_test` target; copy `tests/performance/component/monitoring_views/BUILD`
   (a package: the `performance` target in `non-free/packages/cmk-data-backend/BUILD`). The
   suite is named after the `BUILD` file's directory, without a `cmk-` prefix. The name picks
   its result folder `results/performance-<suite>/` and its database, so it must be unique.
   What matters:

   ```python
   py_cmk_test(
       name = "performance",
       size = "large",
       args = ["<path to the tests>", "-p", "tests.performance.benchmark_json"],
       tags = [
           "exclusive",  # a timing measurement wants the machine to itself
           "external",  # never serve a cached result for a measurement
           "manual",  # run on request, not on every build
       ],
       visibility = ["//tests/performance:__pkg__"],
       deps = [
           "//tests/performance:benchmark_json",
           "//tests/performance:sysmon",
           requirement("pytest_benchmark"),
           ...
       ],
   )
   ```

   The `benchmark_json` plugin writes `benchmark.json` into the test outputs, with the
   docstrings as descriptions. A suite in `tests/performance/component/` also lists its
   `__init__.py` in `srcs` and depends on `//tests/performance:component_pkg`, or its imports
   fail.

4. Add the target to `bazel_performance` in `tests/performance/BUILD`. CI then runs and uploads
   it.
5. For a database of its own, add a case to `database()` in `reporting/perftest_run.py` and
   have the database created first. Its tables must belong to the `performance` user, or the
   upload fails with "permission denied".

## Measuring: runtime and resources

A test measures two things:

- **Runtime**, by the `benchmark` fixture. Only the function you pass is timed, not its
  `setup`, `teardown` or warmup rounds. It runs `rounds` times; with `iterations` above 1, each
  round calls it that often and is divided by it (a `setup` needs `iterations=1`). Checks and
  graphs use the `mean`.
- **Resources**: CPU, memory and disk I/O of the whole machine, sampled once per second by
  `track_resources` in `sysmon.py` into `<name>.resources.json`.

The upload finds a scenario by its `.resources.json` file. **A benchmark without resource
samples of the same name is not uploaded.**

### The `track_system_resources` fixture

```python
@pytest.mark.usefixtures("track_system_resources")
def test_performance_hosts(perftest: PerformanceTest, benchmark: BenchmarkFixture) -> None:
```

The default, and the easiest. It samples the whole test, including the benchmark's (optional)
setup and warmup, but not the fixtures set up before it. The samples are named after the test,
so runtime and resources make one scenario. To leave out the setup and warmup, use
`track_resources` instead.

### The `track_resources` context manager

```python
from tests.performance.sysmon import track_resources

with track_resources(test_name):  # the test passes request.node.name
    perftest.central_site.stop()
    perftest.central_site.start()
```

- **With the test's name**, instead of the fixture: it samples only the block, without the
  setup around it. Inside the function `benchmark` times, it tracks every round and
  iteration: each writes a numbered file, and the upload reads them as one scenario. Do not
  combine it with the fixture, or the fixture's samples count as well.
- **With another name** (e.g. `setup_single_site`): a scenario with resource samples only. It
  is stored, but has no runtime and, without a `test_` name, no check and no default graph. Do
  not give it a `test_` name: the check would report it missing every night.

### About the samples

- They cover the whole machine: on a site test, the site, the test runner and a browser.
  `get_process_group_usage(<site user>)` in `sysmon.py` sums one user's processes, but is not
  uploaded.
- A sample takes about 0.2 seconds, so samples come at most that often. A block of a few
  seconds gets only a few samples: lower `sampling_interval`, or measure more cycles.

## What ends up in the database

The schema is in `reporting/database/initdb_performance.sql`:

```
jobs ──< tests >── scenarios
          │
          ├──< benchmarks   runtime statistics
          └──< metrics      resource samples
```

- `jobs`: one per run. `job_name` is `<branch version>-<date>.<edition>` for a daily build,
  e.g. `3.0.0-2026.11.17.pro`, plus `_<ref>` for a custom git ref. Also the version tested,
  start and end, and the machine.
- `scenarios`: one per test name, across all jobs, with the docstring as description.
- `tests`: one per scenario in a job, with its first and last sample.
- `benchmarks`: every number pytest-benchmark reports (`mean`, `median`, `stddev`, ...) and
  each round's time.
- `metrics`: the resource samples (`cpu_info.*`, `memory_info.*`, `disk_io_counters.*`).

Worth knowing:

- **Scenarios are shared** by all branches and editions in a database: two tests with the same
  name would clash.
- **One job per day and edition.** Each upload replaces its scenarios in the day's job: a rerun
  overwrites the earlier results, and the component suites share the job.
- **A run of a custom git ref** (the Jenkins parameter `CUSTOM_GIT_REF`) gets a job and a
  results folder of its own, `<job>_<ref>`, e.g. `3.0.0-2026.11.18.pro_a34da07c041c`. It is
  checked against the default runs, but never counts in their baselines. Underscores in the
  release part become hyphens, so an underscore always starts a suffix.
- A manual upload without `--append-db` or `--update-db` stores a further run of the day as
  `<job>_2`, `<job>_3`, ...
- **CI only.** The scripts upload only when `CI` is set; a local run writes to the disk.

Setting up the database server: [`reporting/database/README.md`](reporting/database/README.md).

## Baseline checks

After the upload, `perftest_plot.py --validate-baselines` compares the run three times: with
the 4 days before today (weekly), and with the 4 days before the same day 30 and 365 days ago
(monthly, yearly). A check fails if today exceeds the average of those jobs by more than:

- **runtime** (benchmark `mean`): +10 %
- **CPU** (mean `cpu_info.cpu_percent`): +15 %
- **memory** (mean `memory_info.virtual_memory_percent`): +10 %

Only `test_*` scenarios are checked; a new one only once it has a few days of history. A
scenario or a whole run missing today is reported, but does not fail. Noisy scenarios are
skipped in `validate_performance_baselines()` in `reporting/performance_baselines.py`.

## Graphs

The dashboards are in Metabase; their SQL is in
[`reporting/database/graphs/`](reporting/database/graphs/README.md). A `test_*` scenario
appears in:

- the **history** graphs of runtime, CPU and memory: average per job over 6 months, for one
  release; GUI tests in their own (`test_performance_ui_*`).
- the **drilldown**: one scenario against fixed reference lines for 3.0.0, 2.5.0 and 2.4.0. A
  new release branch needs one more column in the three drilldown queries.
- the **per-scenario snapshot**: the last 3 jobs of a release.
- the **spread**: one box per scenario, for a release's newest job or its last 30 days.

Runtime graphs need a benchmark, CPU and memory graphs resource samples. The release filter is
taken from the job name (`3.0.0` from `3.0.0-2026.11.17.pro`). The drilldown baselines and the
spreads leave out reruns (`_2`, ...); the drilldown baselines also leave out custom runs.

`perftest_plot.py` also draws PNG graphs per scenario into the result folder.

## Running the tests locally

**Site suite.** Needs an installed Checkmk version and sudo:

```bash
make -C tests test-performance        # everything
scripts/run-uvenv tests/performance/perftest.sh -k "test_performance_hosts and not restart" --rounds=2
```

`perftest.sh` passes its arguments to pytest. The results land in
`results/performance/<version>.<edition>/`, which each run empties first.

**Component suites.** They are tagged `manual`, so name the target:

```bash
bazel test //tests/performance/component/monitoring_views
bazel test //non-free/packages/cmk-data-backend:performance
tests/run_tests.sh test-performance-all                  # all registered suites + collection
```

The results are in the target's `bazel-testlogs/.../test.outputs/`.

**Graphs from local results**, from the repository root, without a database:

```bash
scripts/run-uvenv python3 -m tests.performance.reporting.perftest_plot \
    --root-dir=results/performance --skip-database-reads --skip-database-writes \
    <branch version>-<date>.<edition>
```

## Checklist

- [ ] The test is in `tests/performance/system/<feature>/` (site) or
      `tests/performance/component/<feature>/` (component, or in its package).
- [ ] Its name and the docstring describe what is measured.
- [ ] `benchmark` times only the work, not its setup.
- [ ] Resources are tracked: by the fixture, or by `track_resources` to leave out the
      benchmark's setup and warmup.
- [ ] Component suite: `py_cmk_test` with `-p tests.performance.benchmark_json`, in
      `bazel_performance`, under a unique directory name.
- [ ] A local run wrote a `benchmark.json` entry and a `.resources.json` of the same name.
