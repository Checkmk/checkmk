# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Unit tests for deriving install spec input prefixes from Bazel closures.

An install target's Bazel closure can contain workspace packages whose
sources there no deployer covers -- cmk-ui-library, which is compiled into
the cmk-frontend-vue dist, or the Vue code of cmk-profiling, whose wheel
deploys only its Python.  These tests pin how such packages are found
(``_compute_input_prefixes``) and how the sources behind the install
targets are queried and grouped.
"""

from pathlib import Path
from subprocess import CompletedProcess

import pytest

from cmk.dev_deploy.manifest import update
from cmk.dev_deploy.manifest.update import (
    _compute_input_prefixes,
    _extensions_by_prefix,
    _install_spec_extensions,
    _query_target_sources,
    _workspace_package,
)

_VUE_TARGET = "//packages/cmk-frontend-vue:frontend_vue_dist_pkg"
_FRONTEND_TARGET = "//packages/cmk-frontend:frontend_dist_pkg"
_NEB_TARGET = "//packages/neb:neb_shared_files"

# The vue dist closure, reduced to one representative path per kind of node.
_VUE_SOURCES = frozenset(
    {
        "packages/cmk-frontend-vue/src/App.vue",
        "packages/cmk-frontend-vue/node_modules/cmk-ui-library",  # rule label
        "packages/cmk-ui-library/components/StateTag.vue",
        "packages/cmk-ui-library/lib/utils.ts",
        "packages/cmk-ui-library/assets/icons/icon-back.svg",
        "packages/cmk-ui-library/package.json",
        "packages/cmk-frontend/src/main.js",  # install spec of its own
        "packages/cmk-profiling/frontend/App.vue",  # wheel package with Vue code
        "packages/cmk-profiling/cmk/profiling/gui/pages.py",
        "packages/cmk-profiling/cmk/profiling/gui/py.typed",
        "cmk/gui/openapi/spec/spec_generator/main.py",  # not a workspace package
        "non-free/packages/cmk-dcd/cmk/dcd/foo.py",  # wheel package
        "packages/cmk-no-wheel/cmk/no_wheel/foo.py",  # Python without a wheel
        "packages/cmk-licensing/cmk/licensing/foo.ts",  # config spec of the whole package
        "locale/de/LC_MESSAGES/multisite.po",  # config spec
    }
)
_WHEEL = frozenset({".py", ".typed"})
_DEPLOYED: list[tuple[str, frozenset[str] | None]] = [
    ("packages/cmk-frontend-vue/", frozenset({".vue"})),
    ("packages/cmk-frontend/", frozenset({".js"})),
    ("packages/neb/", frozenset({".cc"})),
    ("packages/livestatus/", frozenset({".h"})),
    ("cmk/", _WHEEL),
    ("packages/cmk-profiling/", _WHEEL),
    ("non-free/packages/cmk-dcd/", _WHEEL),
    ("packages/cmk-licensing/", None),
    ("locale/", None),
]


class TestWorkspacePackage:
    @pytest.mark.parametrize(
        "path,expected",
        [
            ("packages/cmk-ui-library/lib/utils.ts", "packages/cmk-ui-library"),
            ("non-free/packages/cmc/src/core.cc", "non-free/packages/cmc"),
            ("cmk/gui/views.py", None),
            ("omd/packages/asio/BUILD", None),
            ("packages/stray-file", None),
        ],
    )
    def test_workspace_package(self, path: str, expected: str | None) -> None:
        assert _workspace_package(path) == expected


class TestExtensionsByPrefix:
    def test_longest_prefix_wins(self) -> None:
        paths = ["packages/a/x.cc", "packages/a/sub/y.rs"]
        result = _extensions_by_prefix(paths, {"packages/a", "packages/a/sub"})
        assert result == {
            "packages/a": frozenset({".cc"}),
            "packages/a/sub": frozenset({".rs"}),
        }

    def test_prefix_must_match_a_directory(self) -> None:
        """``packages/a`` must not swallow ``packages/a-other``."""
        result = _extensions_by_prefix(["packages/a-other/x.cc"], {"packages/a"})
        assert result == {}

    def test_paths_without_extension_and_unmatched_paths_are_ignored(self) -> None:
        paths = ["packages/a/Makefile", "packages/a/node_modules/lib", "other/x.cc"]
        assert _extensions_by_prefix(paths, {"packages/a"}) == {}


class TestComputeInputPrefixes:
    def test_inputs_are_the_buildable_sources_no_spec_deploys(self) -> None:
        """cmk-ui-library comes in whole, cmk-profiling with its Vue code only.

        The spec's own package, packages whose specs deploy all of their
        sources here, config directories, and non-workspace paths all have a
        deployer already.
        """
        result = _compute_input_prefixes({_VUE_TARGET: _VUE_SOURCES}, _DEPLOYED)
        assert result == {
            _VUE_TARGET: {
                "packages/cmk-profiling/": frozenset({".vue"}),
                "packages/cmk-ui-library/": frozenset({".vue", ".ts", ".svg", ".json"}),
            }
        }

    def test_python_only_package_is_not_an_input(self) -> None:
        """A wheel-less Python package in the closure keeps its Python categorization.

        The vue dist reaches Python code through the OpenAPI spec generator;
        claiming it for the dist would turn .py edits into frontend builds.
        """
        sources = {_VUE_TARGET: frozenset({"packages/cmk-no-wheel/cmk/no_wheel/foo.py"})}
        assert _compute_input_prefixes(sources, _DEPLOYED) == {}

    def test_target_without_input_packages_is_absent(self) -> None:
        sources = {
            _NEB_TARGET: frozenset({"packages/neb/src/module.cc", "packages/livestatus/x.h"})
        }
        assert _compute_input_prefixes(sources, _DEPLOYED) == {}

    def test_shared_input_package_is_attributed_to_every_consumer(self) -> None:
        shared = frozenset({"packages/cmk-ui-library/lib/utils.ts"})
        result = _compute_input_prefixes({_VUE_TARGET: shared, _FRONTEND_TARGET: shared}, _DEPLOYED)
        assert result == {
            _VUE_TARGET: {"packages/cmk-ui-library/": frozenset({".ts"})},
            _FRONTEND_TARGET: {"packages/cmk-ui-library/": frozenset({".ts"})},
        }

    def test_prefixes_are_sorted(self) -> None:
        sources = {
            _VUE_TARGET: frozenset({"packages/zeta/x.vue", "packages/alpha/y.ts"}),
        }
        result = _compute_input_prefixes(sources, _DEPLOYED)
        assert list(result[_VUE_TARGET]) == ["packages/alpha/", "packages/zeta/"]


class TestInstallSpecExtensions:
    def test_merges_own_and_input_extensions(self) -> None:
        own = {
            "packages/cmk-frontend-vue": frozenset({".vue"}),
            "packages/neb": frozenset({".cc"}),
        }
        inputs = {
            _VUE_TARGET: {"packages/cmk-ui-library/": frozenset({".vue", ".svg"})},
            _FRONTEND_TARGET: {"packages/cmk-ui-library/": frozenset({".ts"})},
        }
        assert _install_spec_extensions(own, inputs) == {
            "packages/cmk-frontend-vue": frozenset({".vue"}),
            "packages/cmk-ui-library": frozenset({".vue", ".svg", ".ts"}),
            "packages/neb": frozenset({".cc"}),
        }

    def test_no_specs_no_extensions(self) -> None:
        assert _install_spec_extensions({}, {}) == {}


class TestQueryTargetSources:
    @staticmethod
    def _specs() -> list[dict[str, str]]:
        # Two specs sharing a target (the cmc helpers pattern) plus one more.
        return [
            {"package_target": _NEB_TARGET},
            {"package_target": _NEB_TARGET},
            {"package_target": _VUE_TARGET},
        ]

    def test_one_query_per_distinct_target(self, monkeypatch: pytest.MonkeyPatch) -> None:
        queries: list[str] = []

        def fake_query(args: list[str], _repo_root: Path) -> CompletedProcess[str]:
            queries.append(args[1])
            return CompletedProcess(args, 0, stdout="//packages/neb:src/module.cc\n", stderr="")

        monkeypatch.setattr(update, "_run_bazel_query", fake_query)
        _query_target_sources(self._specs(), Path("/repo"))

        assert queries == [
            f"labels(srcs, deps({_VUE_TARGET}))",
            f"labels(srcs, deps({_NEB_TARGET}))",
        ]

    def test_labels_become_repo_paths_without_externals(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        stdout = (
            "//packages/cmk-ui-library:components/StateTag.vue\n"
            "//packages/cmk-frontend-vue:node_modules/cmk-ui-library\n"
            "@npm//:node_modules/vue\n"
            "@@rules_pkg+//pkg:providers.bzl\n"
        )
        monkeypatch.setattr(
            update,
            "_run_bazel_query",
            lambda args, _repo_root: CompletedProcess(args, 0, stdout=stdout, stderr=""),
        )

        result = _query_target_sources([{"package_target": _VUE_TARGET}], Path("/repo"))

        assert result == {
            _VUE_TARGET: frozenset(
                {
                    "packages/cmk-ui-library/components/StateTag.vue",
                    "packages/cmk-frontend-vue/node_modules/cmk-ui-library",
                }
            )
        }

    def test_failed_query_leaves_target_out(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def fake_query(args: list[str], _repo_root: Path) -> CompletedProcess[str] | None:
            if _NEB_TARGET in args[1]:
                return None
            return CompletedProcess(
                args, 0, stdout="//packages/cmk-frontend-vue:x.vue\n", stderr=""
            )

        monkeypatch.setattr(update, "_run_bazel_query", fake_query)

        result = _query_target_sources(self._specs(), Path("/repo"))

        assert result == {_VUE_TARGET: frozenset({"packages/cmk-frontend-vue/x.vue"})}
