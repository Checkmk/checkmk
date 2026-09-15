# Work in progress!

We're currently in the process of reorganizing the test suites.
The full target architecture is described [here](https://wiki.lan.checkmk.net/spaces/DEV/pages/209453301/Test+classification+and+architecture).

# Desired test suite organization in a nutshell

Organize tests by **feature, not by fixture**.

- Bad: `gui_e2e` (everything using Playwright), `composition` (everything needing a remote site), ...
- Good: `redfish`, `otel`, `piggyback`, `agent_bakery`, ...

Classify by **scope**: package tests (one package, in that package's `tests/`) →
integration tests (several packages, no site, `tests/integration/`) → system
tests (running site/browser/HTTP, `tests/system/<feature>/`).

# Transitional buckets

`singlesite`, `multisite`, `gui`, `gui_crawl`, `update` and `plugins` are exactly
the fixture-named grouping described as bad above. They are holding areas: the
suites were moved here unchanged so that all system tests live under one roof
first. They are to be dissolved into feature directories over time — do not add
new suites in that shape, and prefer moving a test out into its feature
directory over growing these further.

# Pytest setup

`tests/system/conftest.py` registers the setup every system suite needs: the
package under test (`--cmk-edition`, edition skips, crash reports), the session
timeout, sharding, CI selection and failure diagnostics. Each of those is a
plugin module in `tests/testlib/system/pytest_helpers/` (or in
`tests/testlib/pytest_helpers/` when it does not need a site), so a suite outside
`tests/system/` (packaging, performance, ...) can register the subset it needs
from its own conftest via `tests.testlib.pytest_helpers.register`.

Setup for one feature lives in that feature's conftest. When moving a test out
of a transitional bucket, move the fixtures it needs along with it, or into a
plugin module if a second suite needs them too.

Options are only known when their conftest is an _initial_ one, i.e. on the path
of a directory or file given on the command line. `pytest tests/system/gui
--local-run` works, `pytest tests/system --local-run` does not: run one suite at
a time, as run_tests.sh does.
