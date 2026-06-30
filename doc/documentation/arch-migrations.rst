================================
Ongoing architectural migrations
================================

This page lists the architectural migrations that are currently ongoing in the Checkmk codebase.
It is aimed at developers: when you touch an area that is mid-migration, follow the *new* mechanism — do not add to the legacy one.

Each migration is labeled with one of these phases:

* **starting** — the new mechanism exists, but adoption has barely begun
* **in progress** — both mechanisms are in active use, migration is ongoing
* **mostly done** — the new mechanism is the default, legacy remnants are being removed

Last reviewed: June 2026.

If you own one of these migrations, please keep its section up to date and remove it once the migration is complete.
If you come across this document and find it outdated or incomplete, feel free to take action.
If in doubt, reach out to Moritz Kiemer.

Check plugin API: legacy checks to ``agent_based.v2``
=====================================================

:Phase: mostly done
:Old: dict-based legacy check plugins in ``cmk/legacy_checks/``
:New: ``cmk.agent_based.v2`` plugins in ``cmk/plugins/<family>/agent_based/``

The legacy check API is untyped and predates the structured ``Service``/``Result``/``Metric`` model, making plugins hard to test and validate.
A few hundred legacy checks remain; they are converted with a semi-automated two-commit process.

See ``doc/treasures/migration_helpers/legacy_checks/instruction.md`` for the migration recipe and tooling.

REST API framework: Marshmallow to versioned Pydantic endpoints
===============================================================

:Phase: in progress
:Old: ``@Endpoint`` + Marshmallow schemas in ``cmk/gui/openapi/endpoints/``
:New: ``VersionedEndpoint`` + Pydantic v2 models in ``cmk/gui/openapi/api_endpoints/``

The new framework derives request/response schemas from type annotations, so endpoint models are statically type checked, and it supports multiple API versions per endpoint (``v1``, ``unstable``, ``internal``).
The legacy framework is deprecated and will be removed once all endpoint families are migrated.

See ``cmk/gui/openapi/api_endpoints/README.md``; the deprecation notice is in ``cmk/gui/openapi/README.md``.

Rulesets and GUI forms: ValueSpec to FormSpec
=============================================

:Phase: in progress
:Old: ``cmk.gui.valuespec`` with server-side form rendering
:New: ``cmk.rulesets.v1`` form specs, rendered by the Vue frontend via ``cmk/gui/form_specs/``

ValueSpecs mix data model, validation and HTML rendering in one class, which ties every form to the legacy server-side GUI.
FormSpecs are declarative and frontend-agnostic, so forms can be rendered by the new Vue frontend, and ruleset definitions become part of the stable plugin API.

See ``packages/cmk-plugin-apis/cmk/rulesets/`` and ``cmk/gui/form_specs/``.

Plugin registration: registries to discovery
============================================

:Phase: in progress
:Old: plugins push themselves into mutable registry singletons at import time
:New: plugins are inert module-level objects under ``cmk/plugins/<family>/<group>/``, collected by namespace scanning

Registries are import-order-dependent global state with silent failure modes.
Discovery returns an immutable mapping with explicit errors, and backend and plugin code share only a small per-domain API package.

See ``packages/cmk-plugin-apis/cmk/discover_plugins/README.md``, which also lists half-migrated domains (modes, automations, post-rename-site plugins).

Frontend: Python-rendered pages to Vue 3
========================================

:Phase: in progress
:Old: server-side HTML generation via ``cmk.gui.htmllib`` plus the legacy ``packages/cmk-frontend`` scripts
:New: Vue 3 + TypeScript components in ``packages/cmk-frontend-vue``, with backend/frontend types kept in sync via ``packages/cmk-shared-typing``

Server-side HTML generation with inline JavaScript is hard to type check,
test and reuse. New UI is built as Vue components against a shared typed
contract; current focus areas are FormSpec rendering and the new monitoring
pages ("mon-pages").

See ``packages/cmk-frontend-vue/README.md`` and :doc:`arch-comp-gui-vue`.

View painters: v0 to v1
=======================

:Phase: in progress
:Old: ``cmk.gui.painter.v0`` painters (``abc.ABC`` subclasses that emit HTML directly)
:New: ``cmk.gui.painter.v1`` painters (frozen, generic dataclasses with separate HTML/CSV/JSON formatters)

The v0 painter base class couples data lookup and HTML rendering and is untyped over the row data it formats.
The v1 painters are declarative dataclasses parametrized over their data type, with dedicated formatters per output format, so the same painter can render HTML, CSV and JSON without ad-hoc string handling.
v1 painters are wrapped by ``PainterAdapter`` in ``cmk/gui/painter/v0/base.py`` so they run in code that still expects the v0 interface.

See ``cmk/gui/painter/v1/painter_lib.py`` and the ``PainterAdapter`` bridge in ``cmk/gui/painter/v0/base.py``.

Build system: Make to Bazel
===========================

:Phase: mostly done
:Old: Makefiles and ad-hoc scripts; direct ``pytest``/``ruff``/``mypy`` calls
:New: Bazel as the primary build system for builds, unit tests, linting, formatting and type checking

Bazel provides hermetic, cacheable and parallel builds with a uniform, edition-aware interface across all languages in the repository.
Integration, composition and GUI end-to-end tests as well as parts of the OMD packaging still run via Make.

See ``BAZEL.md`` in the repository root.

Packaging: centralized ``bin/BUILD`` to self-contained CLI entry points
=======================================================================

:Phase: starting
:Old: shipped ``bin/`` entry points aggregated centrally in ``bin/BUILD`` via ``//bin:pkg_tar``, even when the source lives under ``cmk/``
:New: each owning package ships its own entry point and wires it directly into ``omd/BUILD``'s ``deps_packages_base``

Routing every shipped CLI through ``bin/BUILD`` makes it a cross-cutting hub that must know about files owned by many other components, and it forces those components to re-export their sources via ``exports_files``.
For example, ``cmk-pwstore`` (source ``//cmk/utils:password_store/cli.py``) and ``cmk-product-usage`` (source ``//cmk/product_usage:cli.py``) both define their ``pkg_files`` in ``bin/BUILD`` while their code lives under ``cmk/``.

Example for the new pattern: ``cmk/post_rename_site`` (``//cmk/post_rename_site:post-rename-site-pkg``) and ``cmk/update_config`` (``//cmk/update_config:cmk-update-config-pkg``).
In the new pattern the owning package defines its own ``pkg_files`` target (named ``<binary-name>-pkg``) with ``prefix = "bin"``, ``mode = "0755"``, a ``renames`` mapping the source to the final binary name, and ``visibility = ["//omd:__pkg__"]``.
That target is listed directly in ``omd/BUILD``'s ``deps_packages_base`` ``pkg_tar``, so ``bin/BUILD`` is not touched and no ``exports_files`` is needed.

When adding a *new* shipped CLI entry point, use the self-contained pattern.

Monolith decomposition: dissolve global ``BaseConfig`` and ``ConfigCache``
=========================================================================

:Phase: in progress (long-running)
:Old: one large intertwined ``ConfigCache`` class
:New: Feature components only parse the part of the config they actually need.

The ``ConfigCache`` is a monolithic god class that ties together various different concerns.
It also introduces dependencies in the wrong direction: Feature business logic should expose the configuration objects required to run it.

Monolith decomposition: ``cmk.*`` to packages
========================================================

:Phase: in progress (long-running)
:Old: one large intertwined ``cmk.*`` Python codebase
:New: packages under ``packages/`` and ``non-free/packages/`` with their own build, tests and dependency declarations

Extracting components into packages makes their dependencies explicit and enforceable, so they can be built, tested and reused independently of the monolith.
Several dozen packages exist already (``cmk-ccc``, ``cmk-crypto``, ``cmk-werks``, ``cmk-livestatus-client``, ...), and more code moves there.
Some code is moved to packages while still depending on the monolith.
This is an accepted intermediate step to clarify affiliation.
The declared goal is to disentangle these dependencies to get clear packages with a well-defined surface.
