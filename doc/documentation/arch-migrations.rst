================================
Ongoing architectural migrations
================================

This page lists the architectural migrations that are currently ongoing in the Checkmk codebase.
It is meant to give guidance in code areas that are mit-migration, to help developers not familiar with the code area to understand how they are expected to extend or change the mechanism in question.
So when you touch an area that is mid-migration, follow the *new* mechanism — do not add to the legacy one.

In this document, "owner" refers to a person, team or component you can turn to for additional information.
**This is not a document to distribute work.**

Each migration is labeled with one of these phases:

* **conceptualized** — the change is planned and documented, but implementation has not started
* **starting** — the new mechanism exists, but adoption has barely begun
* **in progress** — both mechanisms are in active use, migration is ongoing
* **mostly done** — the new mechanism is the default, legacy remnants are being removed

Last reviewed: July 2026.

If you own one of these migrations, please keep its section up to date and remove it once the migration is complete.
If you come across this document and find it outdated or incomplete, feel free to take action.
If in doubt, reach out to Moritz Kiemer.

Check plugin API: legacy checks to ``agent_based.v2``
=====================================================

:Phase: mostly done
:Owner: Respective plugin components / Lead: General "Plugins" component
:Old: dict-based legacy check plugins in ``cmk/legacy_checks/``
:New: ``cmk.agent_based.v2`` plugins in ``cmk/plugins/<family>/agent_based/``
:References: ``doc/treasures/migration_helpers/legacy_checks/instruction.md`` (migration recipe and tooling)

The legacy check API is untyped and predates the structured ``Service``/``Result``/``Metric`` model, making plugins hard to test and validate.
A few hundred legacy checks remain; they are converted with a semi-automated two-commit process.

This migration is meant to be finished by the end of Q3/2026.

Bakery plugin API: ``bakery_api.v1`` to ``cmk.bakery``
======================================================

:Phase: in progress
:Owner: Component "Agent Bakery"
:Old: bakery plugins written against ``cmk.base.plugins.bakery.bakery_api.v1`` (the import location advertised up to and including Checkmk 2.5)
:New: plugins against the ``cmk.bakery`` API shipped in the ``cmk-plugin-apis`` package, living under ``cmk/plugins/<family>/bakery/`` and collected by discovery
:References: ``packages/cmk-plugin-apis/cmk/bakery/``; Werk #18600

The old bakery API lives in the ``cmk.base`` tree and is tied to the monolith, and its import location no longer matches the current edition naming.
The current API is a proper plugin-API package, and bakery plugins move next to the family that owns them (around 30 families are already there).
The old API is being replaced by ``cmk.bakery.v2_unstable`` and is intended to be removed with Checkmk 2.7 (see Werk #18600).

This migration is meant to be finished before the 3.0 release.

REST API framework: Marshmallow to versioned Pydantic endpoints
===============================================================

:Phase: in progress
:Owner: Component "Rest API Framework"
:Old: ``@Endpoint`` + Marshmallow schemas in ``cmk/gui/openapi/endpoints/``
:New: ``VersionedEndpoint`` + Pydantic v2 models in ``cmk/gui/openapi/api_endpoints/``
:References: ``cmk/gui/openapi/api_endpoints/README.md``; deprecation notice in ``cmk/gui/openapi/README.md``

The new framework derives request/response schemas from type annotations, so endpoint models are statically type checked, and it supports multiple API versions per endpoint (``v1``, ``unstable``, ``internal``).
The legacy framework is deprecated and will be removed once all endpoint families are migrated.

Rulesets and GUI forms: ValueSpec to FormSpec
=============================================

:Phase: in progress
:Owner: Component "UI Setup"
:Old: ``cmk.gui.valuespec`` with server-side form rendering
:New: ``cmk.rulesets.v1`` form specs, rendered by the Vue frontend via ``cmk/gui/form_specs/``
:References: ``packages/cmk-plugin-apis/cmk/rulesets/`` and ``cmk/gui/form_specs/``

ValueSpecs mix data model, validation and HTML rendering in one class, which ties every form to the legacy server-side GUI.
FormSpecs are declarative and frontend-agnostic, so forms can be rendered by the new Vue frontend, and ruleset definitions become part of the stable plugin API.

Plugin registration: registries to discovery
============================================

:Phase: in progress
:Owner: Respective component owners. Potentially driven by architectural requirements.
:Old: plugins push themselves into mutable registry singletons at import time
:New: plugins are inert module-level objects under ``cmk/plugins/<family>/<group>/``, collected by namespace scanning
:References: ``packages/cmk-plugin-apis/cmk/discover_plugins/README.md`` (also lists half-migrated domains: modes, automations, post-rename-site plugins)

Registries are import-order-dependent global state with silent failure modes.
Discovery returns an immutable mapping with explicit errors, and backend and plugin code share only a small per-domain API package.

Frontend: Python-rendered pages to Vue 3
========================================

:Phase: in progress
:Owner: Team Bug (Lead Moritz Kirschner)
:Old: server-side HTML generation via ``cmk.gui.htmllib`` plus the legacy ``packages/cmk-frontend`` scripts
:New: Vue 3 + TypeScript components in ``packages/cmk-frontend-vue``, with backend/frontend types kept in sync via ``packages/cmk-shared-typing``
:References: ``packages/cmk-frontend-vue/README.md`` and :doc:`arch-comp-gui-vue`

Server-side HTML generation with inline JavaScript is hard to type check,
test and reuse. New UI is built as Vue components against a shared typed
contract; current focus areas are FormSpec rendering and the new monitoring
pages ("mon-pages").

View painters: v0 to v1
=======================

:Phase: in progress
:Owner: Component "UI Monitoring"
:Old: ``cmk.gui.painter.v0`` painters (``abc.ABC`` subclasses that emit HTML directly)
:New: ``cmk.gui.painter.v1`` painters (frozen, generic dataclasses with separate HTML/CSV/JSON formatters)
:References: ``cmk/gui/painter/v1/painter_lib.py`` and the ``PainterAdapter`` bridge in ``cmk/gui/painter/v0/base.py``

The v0 painter base class couples data lookup and HTML rendering and is untyped over the row data it formats.
The v1 painters are declarative dataclasses parametrized over their data type, with dedicated formatters per output format, so the same painter can render HTML, CSV and JSON without ad-hoc string handling.
v1 painters are wrapped by ``PainterAdapter`` in ``cmk/gui/painter/v0/base.py`` so they run in code that still expects the v0 interface.

GUI: global proxies to explicit dependencies
============================================

:Phase: in progress
:Owner: Component "UI Framework"
:Old: request-local global proxies reached for anywhere in the call stack (``active_config``, and the other ``request_local_attr`` proxies such as ``html``, ``response``, ``theme``, ``user_errors``)
:New: the objects a mode or page needs are passed in explicitly, the way REST API v1 endpoints receive an ``ApiContext``
:References: ``cmk/gui/ctx_stack.py`` (``request_local_attr``); ``cmk/gui/config.py`` (``active_config``); ``ApiContext`` in ``cmk/gui/openapi/framework/`` as the target pattern

The GUI relies on request-local proxies (defined via ``request_local_attr`` in ``cmk/gui/ctx_stack.py``) that any function can import and dereference, so the real dependencies of a mode or page are invisible and hard to test in isolation.
The migration replaces this implicit global state with explicit dependency passing:

* Eliminate use of the global proxies as much as possible (``git grep request_local_attr``).
* Pass everything a mode or page needs into it explicitly, as the REST API v1 endpoints already do via ``ApiContext``.
* Eliminate ``active_config`` in particular (around 200 call sites under ``cmk/gui``): thread through only the parts of the configuration actually needed — derived, narrowly typed objects rather than the whole ``Config``.

GUI: centralize the ``FolderTree`` computation
==============================================

:Phase: starting
:Owner: Lars Michelsen
:Old: ``folder_tree()`` builds a ``FolderTree`` from ``active_config`` on first use and memoizes it on the request-global ``g.folder_tree``
:New: the ``FolderTree`` is computed once, high up in the call stack, and passed down explicitly as a parameter
:References: ``cmk/gui/watolib/hosts_and_folders.py`` (``folder_tree()``, ``make_folder_tree``, ``FolderTree``)

``folder_tree()`` is a request-global accessor (around 170 call sites) that hides both a dependency on ``active_config`` and shared mutable state on ``g``, which is exactly the implicit-global-state pattern the proxy migration above is removing.
Computing the ``FolderTree`` once at a well-defined point and passing it down as an argument lets ``folder_tree()`` and ``g.folder_tree`` be removed, and makes the folder data a mode or page depends on explicit and testable.

GUI: ``WatoMode`` lifecycle as an explicit sequence of calls
============================================================

:Phase: starting
:Owner: Component "UI Setup"
:Old: ``WatoMode`` parses request variables in ``__init__`` (``_from_vars``), then ``page_menu``, ``action`` and ``page`` are dispatched as independent methods that each receive only ``config``
:New: ``from_vars``, ``page_menu``, ``action`` and ``page`` form an explicit sequence, so state computed in one step can be handed to the next
:References: ``cmk/gui/watolib/mode/_base.py`` (``WatoMode``)

Because a ``WatoMode`` does its request parsing in the constructor and its remaining phases are separate method calls with no shared, passed-through state, there is no clean way to compute something once (for example a ``FolderTree``) and use it across ``page_menu``, ``action`` and ``page`` without falling back to request globals.
Turning the lifecycle into an explicit sequence of calls lets each step receive the objects the previous step produced, which is a prerequisite for passing dependencies like ``FolderTree`` in explicitly rather than reaching for ``g``.

GUI: dissolve ``cmk/gui/plugins``
=================================

:Phase: in progress
:Owner: Respective component owners
:Old: GUI plugins and shared plugin utilities under ``cmk/gui/plugins/`` (``bi``, ``dashboard``, ``sidebar``, ``views``, ``visuals``, ``wato``, ``legacy_bakery_rulesets``), plus ``cmk.gui.plugins.*`` namespaces kept as compatibility shims
:New: plugins live next to the feature that owns them and are collected by discovery; shared code moves to a proper module rather than a ``plugins`` namespace
:References: ``cmk/gui/plugins/``; see also the *Plugin registration: registries to discovery* and *ValueSpec to FormSpec* migrations

``cmk/gui/plugins/`` is a historical catch-all: it mixes actual plugins with shared GUI internals, and the ``cmk.gui.plugins.*`` import paths are still referenced from several hundred modules — many only as compatibility namespaces that were kept when code moved elsewhere.
Two threads run here:

* Migrate our own remaining plugins out of ``cmk/gui/plugins/`` to their owning feature and the discovery mechanism.
* Decide whether the old ``cmk.gui.plugins.*`` namespaces kept for compatibility can be dropped, and remove them where they can.

Tests: fixture-based suites to feature- and scope-based classification
======================================================================

:Phase: starting
:Owner: Moritz Kiemer
:Old: top-level ``tests/`` suites grouped by the fixture they happen to use (``tests/integration``, ``tests/composition``, ``tests/gui_e2e``, ``tests/integration_redfish``, ...)
:New: tests classified by *scope* (static analysis, package, integration, system level) and, within the system level, organized by *feature* rather than fixture
:References: ``tests/system/README-test-suite-organization.md``; `Test classification and architecture <https://wiki.lan.checkmk.net/spaces/DEV/pages/209453301/Test+classification+and+architecture>`_

The historical suites are named after the machinery a test needs — ``composition`` is "everything that needs a remote site", ``gui_e2e`` is "everything that needs Playwright" — which scatters a single feature across several suites and lumps unrelated features together.
The target layout classifies every test by scope and groups system level tests by the feature under test (``redfish``, ``otel``, ``piggyback``, ``agent bakery``, ...):

* Package tests (unit + component) live in the owning package's own ``tests/`` directory and are fully Bazel-managed.
* Cross-package tests without a running site live under ``tests/integration/``.
* System level tests (the former ``integration``/``composition``/``gui_e2e`` suites) move under ``tests/system/<feature>/``, are parametrized over the site edition, and declare the feature they exercise rather than carrying edition-specific skips.

The first steps are visible under ``tests/system/`` (for example ``tests/system/redfish/``, moved out of ``tests/integration_redfish/``); most suites still follow the old fixture-based grouping.

Tooling: Make to Bazel
===========================

:Phase: mostly done
:Owner: Team CI
:Old: Makefiles and ad-hoc scripts; direct ``pytest``/``ruff``/``mypy`` calls
:New: Bazel as the primary build system for builds, unit tests, linting, formatting and type checking
:References: ``BAZEL.md`` in the repository root

Bazel provides hermetic, cacheable and parallel builds with a uniform, edition-aware interface across all languages in the repository.
Integration, composition and GUI end-to-end tests as well as parts of the OMD packaging still run via Make.

Centralized ``bin/BUILD`` to self-contained CLI entry points
============================================================

:Phase: starting
:Owner: Moritz Kiemer.
:Old: shipped ``bin/`` entry points aggregated centrally in ``bin/BUILD`` via ``//bin:pkg_tar``, even when the source lives under ``cmk/``
:New: ``bin/`` in the repo does not exist. Each package declares its shipped own entry points via the ``entry_points`` argument to the ``py_wheel`` rule.
:References: 35b24d32b5e4559a999e3dfba489e289477d94d5

Next step here is migrate the remaining elements in ``bin/``.

Monolith decomposition: dissolve global ``BaseConfig`` and ``ConfigCache``
==========================================================================

:Phase: in progress (long-running)
:Owner: Moritz Kiemer
:Old: one large intertwined ``ConfigCache`` class
:New: Feature components only parse the part of the config they actually need.
:References:

The ``ConfigCache`` is a monolithic god class that ties together various different concerns.
It also introduces dependencies in the wrong direction: Feature business logic should expose the configuration objects required to run it.

Monolith decomposition: ``cmk.*`` to packages
==============================================

:Phase: in progress (long-running)
:Owner: Lars Michelsen
:Old: one large intertwined ``cmk.*`` Python codebase
:New: packages under ``packages/`` and ``non-free/packages/`` with their own build, tests and dependency declarations
:References:

Extracting components into packages makes their dependencies explicit and enforceable, so they can be built, tested and reused independently of the monolith.
Several dozen packages exist already (``cmk-ccc``, ``cmk-crypto``, ``cmk-werks``, ``cmk-livestatus-client``, ...), and more code moves there.
Some code is moved to packages while still depending on the monolith.
This is an accepted intermediate step to clarify affiliation.
The declared goal is to disentangle these dependencies to get clear packages with a well-defined surface.

Packaging: non-free code out of the free module hierarchy
=========================================================

:Phase: in progress
:Owner: Lars Michelsen
:Old: non-free code interleaved into the free Python hierarchy as ``nonfree`` sub-packages (``cmk/gui/nonfree/``, ``cmk/base/nonfree/``, ``cmk/editions/nonfree/``, ``cmk/update_config/nonfree/``, ...)
:New: non-free code separated out and moved below the top-level ``non-free/`` directory
:References: `CMK-32538 <https://jira.lan.tribe29.com/browse/CMK-32538>`_

Scattering ``nonfree`` sub-packages throughout the free ``cmk.*`` tree makes the licensing boundary invisible in the filesystem: whether a module may ship in the community edition depends on its name, not its location.
Consolidating non-free code below the top-level ``non-free/`` directory (which already hosts ``non-free/packages/``) makes the boundary structural and enforceable, and aligns with the move to standalone packages above.

Data model: drop multi-tenancy-specific data models
===================================================

:Phase: conceptualized
:Owner: Component "Managed services edition"
:Old: separate multi-tenancy-specific data models for the ``ultimatemt`` edition (``cmk/gui/nonfree/ultimatemt/``, ``cmk/base/nonfree/ultimatemt/``)
:New: a single data model without multi-tenancy-specific variants
:References: `concept document <https://docs.google.com/document/d/1Xku72nuVToFo9vsJR2q1fQ5EdA2eUzAA6NIWjKk0pFw/edit?tab=t.0>`_

Multi-tenancy (the ``ultimatemt`` edition) currently carries its own data models, which duplicates concepts and forces edition-specific branching.
The concept for unifying these onto a single data model is documented but implementation has not started.
