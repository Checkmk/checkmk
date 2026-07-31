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
