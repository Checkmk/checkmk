===================
Test classification
===================

This page defines the test levels, says where each kind of test lives and how
to run it. It is based on the internal wiki page "Test classification and
architecture". Read the :doc:`dev-testing` first.

Test levels
===========

=============  ===========================================  ==========================================  ================================================
Level          What it covers                               Allowed setup                               Location
=============  ===========================================  ==========================================  ================================================
Unit           One function, method or class of one         None. No helper processes, no test-only     The package's ``tests/`` directory
               package. Replace collaborators with          services.
               doubles only where needed.
Component      One package with its real package-level      In-process fixtures. No site.               The package's ``tests/`` directory
               collaborators wired together. May start
               the package's own processes, but nothing
               from another package.
Integration    The contract between two or more             Mocks, sockets, lightweight in-process      ``tests/integration/``,
               first-party packages, e.g. agent             setups. No site, no real monitored          ``non-free/tests/integration/``
               controller and agent receiver.               systems.
System         The whole system through its external        Running site(s), real monitored systems,    ``tests/system/<feature>/``, run via
               interfaces: GUI via Playwright, REST API     browser, HTTP client.                       ``tests/run_tests.sh test-system-<suite>``
               via HTTP client. Includes E2E and site
               tests.
=============  ===========================================  ==========================================  ================================================

Unit and component tests together are *package tests*. They differ in design,
but the build treats them alike: small, fast, close to the code.

Single-site and multi-site tests (formerly "integration" and "composition"
tests) are the same kind of system test. E2E tests are system tests that
almost always need a site.

Where tests live
================

* **Inside a package**, pick the simplest layout that fits:
  ``tests/test_<module>.py`` for a simple package, ``tests/unit/`` and
  ``tests/component/`` when the split helps. Code in ``cmk/`` that is not yet a
  package keeps its tests in ``tests/unit/``, mirroring the module path.
* **Package and integration tests mirror the source.** Write one test module
  per source module, grouped by package. When the code moves, its tests move
  with it.
* **System tests are organized by feature or workflow**, never by internal API
  and never by fixture: ``tests/system/redfish/``, not "everything that needs
  Playwright". The directories ``singlesite``, ``multisite``, ``gui``,
  ``gui_crawl``, ``update`` and ``plugins`` are transitional. Do not add new
  suites there; move tests out into feature directories when you can.
* **Integration tests that load everything an edition ships** (no site) come
  in three kinds, each in its own directory below ``tests/integration/``:

  * ``edition_scope/``: snapshots of what an edition contains ("is this
    feature in this edition"). One target per edition.
  * ``plugin_invariants/``: a property every single plug-in (or other shipped
    element) must have on its own. If it holds for all editions combined, it
    holds for each, so the tests run once against all editions (and once for
    community, which has no non-free code).
  * ``plugin_consistency/``: whether the shipped set is complete and its
    cross-references resolve (every section is consumed, a dashboard's metric
    exists). This depends on the edition, so the tests run per edition.

Other kinds of tests
====================

* **Static analysis** (lint, type checks, formatting, license headers) belongs
  in ``bazel lint`` wherever possible and runs before every commit.
* **Acceptance tests** check business or user requirements. They live in a
  directory with an ``acceptance/`` path segment. Do not change their expected
  outcome without explicit agreement from the stakeholders.
* **Performance tests** live in ``tests/performance/``. They need guaranteed
  resources, so CI selects them by tag.
* **Artifact tests** (``tests/packaging/``) check that a build contains the
  expected files.
* **Doctests** are documentation, not tests. They keep examples accurate.
  Never let a doctest be the only coverage of some logic.

Running tests
=============

Bazel manages package and integration tests and caches their results.

* Always run the tests of the packages you touched:
  ``bazel test //packages/<pkg>/...`` or ``bazel test //tests/unit/<path>/...``.
* When you touch a cross-package boundary, also run
  ``bazel test //tests/integration/... //non-free/tests/integration/...``, or
  the relevant subset.
* Rarely run system tests locally. They are slow and need a site, and CI runs
  them selected by Bazel tags. Run them locally when you work on a system test
  itself or debug a CI failure, and then only the tests that cover your
  change.

Editions
========

* **Package and integration tests are edition-agnostic.** Editions change
  whether a module is deployed, not how it behaves. Do not skip a package or
  integration test by edition: if the module exists, its tests run in every
  edition. If the edition really is an input to the logic, pass it as a plain
  test parameter.
* **System tests test features, not editions.** There are no "Pro tests", only
  "DCD tests". Every system suite runs once per edition and declares the
  feature it tests; the framework decides whether to run or skip it.
* **Artifact tests and edition scope tests are the edition-specific kinds.**
  They check that a build, or the code an edition loads, contains the expected
  files or features.

Free and non-free code
======================

Targets that depend on non-free libraries live below ``non-free/``. A system
test target that depends on both free and non-free code lives in
``non-free/tests/``. The legacy ``tests/`` tree still keeps such tests in
``nonfree/`` subdirectories, e.g. ``tests/unit/cmk/gui/nonfree/``. Follow the
placement of the neighboring tests.
