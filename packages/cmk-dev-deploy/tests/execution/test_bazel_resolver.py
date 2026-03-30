# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Unit tests for cmk.dev_deploy.bazel_resolver (file-to-target mapping)."""

from __future__ import annotations

from pathlib import Path

import pytest

from cmk.dev_deploy.execution.bazel_resolver import (
    _get_bazel_queryable_files,
    _get_build_file_packages,
    _parse_target,
    resolve_bazel_targets,
)
from cmk.dev_deploy.types import (
    BazelTargetKind,
    BazelTargetSet,
    ChangeCategory,
    ChangeSet,
    InstallSpec,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_COMMIT = "a" * 40


def _make_changeset(**category_files: tuple[str, ...]) -> ChangeSet:
    """Build a ChangeSet from keyword arguments mapping category names to file tuples.

    Example:
        _make_changeset(RUST=("packages/check-cert/src/main.rs",))
    """
    categories = {ChangeCategory[cat]: files for cat, files in category_files.items()}
    all_files = tuple(sorted(f for files in categories.values() for f in files))
    return ChangeSet(build_commit=_COMMIT, files=all_files, categories=categories)


def _make_install_spec(package: str, package_target: str) -> InstallSpec:
    """Create a minimal InstallSpec for testing."""
    return InstallSpec(
        package=package,
        package_target=package_target,
        output_basename="dummy",
        install_dest="bin/dummy",
        mode=0o755,
        post_install=(),
        edition_constraint=None,
        needs_version_flag=False,
        needs_faked_artifacts=False,
        use_copytree=False,
    )


# ---------------------------------------------------------------------------
# _get_bazel_queryable_files tests
# ---------------------------------------------------------------------------


class TestGetBazelQueryableFiles:
    """Tests for filtering files to Bazel-queryable categories."""

    def test_extracts_rust_files(self) -> None:
        cs = _make_changeset(RUST=("packages/check-cert/src/main.rs",))
        result = _get_bazel_queryable_files(cs)
        assert result == ["packages/check-cert/src/main.rs"]

    def test_extracts_cpp_files(self) -> None:
        cs = _make_changeset(CPP=("packages/neb/src/NebCore.cc",))
        result = _get_bazel_queryable_files(cs)
        assert result == ["packages/neb/src/NebCore.cc"]

    def test_extracts_vue_and_frontend(self) -> None:
        cs = _make_changeset(
            VUE=("packages/cmk-frontend-vue/src/App.vue",),
            FRONTEND=("packages/cmk-frontend/src/main.js",),
        )
        result = _get_bazel_queryable_files(cs)
        assert len(result) == 2
        assert "packages/cmk-frontend-vue/src/App.vue" in result
        assert "packages/cmk-frontend/src/main.js" in result

    def test_excludes_python_files(self) -> None:
        cs = _make_changeset(
            PYTHON=("cmk/gui/views.py",),
            RUST=("packages/check-cert/src/main.rs",),
        )
        result = _get_bazel_queryable_files(cs)
        assert "cmk/gui/views.py" not in result
        assert result == ["packages/check-cert/src/main.rs"]

    def test_excludes_test_config_data_other(self) -> None:
        cs = _make_changeset(
            TEST=("tests/unit/test_foo.py",),
            CONFIG=("agents/plugins/agent_x",),
            DATA=("locale/de/messages.po",),
            OTHER=("README.md",),
        )
        result = _get_bazel_queryable_files(cs)
        assert result == []

    def test_empty_categories_returns_empty(self) -> None:
        cs = ChangeSet(build_commit=_COMMIT, files=(), categories={})
        result = _get_bazel_queryable_files(cs)
        assert result == []

    def test_result_is_sorted(self) -> None:
        cs = _make_changeset(
            RUST=(
                "packages/mk-sql/src/main.rs",
                "packages/check-cert/src/main.rs",
            ),
        )
        result = _get_bazel_queryable_files(cs)
        assert result == sorted(result)


# ---------------------------------------------------------------------------
# _get_build_file_packages tests
# ---------------------------------------------------------------------------


class TestGetBuildFilePackages:
    """Tests for BUILD file change detection."""

    def test_module_bazel_returns_global(self) -> None:
        cs = _make_changeset(BUILD=("MODULE.bazel",))
        result = _get_build_file_packages(cs)
        assert result == ["//..."]

    def test_bazel_dir_returns_global(self) -> None:
        cs = _make_changeset(BUILD=("bazel/deps.bzl",))
        result = _get_build_file_packages(cs)
        assert result == ["//..."]

    def test_package_build_file(self) -> None:
        cs = _make_changeset(BUILD=("packages/check-cert/BUILD",))
        result = _get_build_file_packages(cs)
        assert result == ["//packages/check-cert/..."]

    def test_package_build_bazel_file(self) -> None:
        cs = _make_changeset(BUILD=("packages/neb/BUILD.bazel",))
        result = _get_build_file_packages(cs)
        assert result == ["//packages/neb/..."]

    def test_no_build_category_returns_empty(self) -> None:
        cs = _make_changeset(PYTHON=("cmk/foo.py",))
        result = _get_build_file_packages(cs)
        assert result == []

    def test_multiple_packages(self) -> None:
        cs = _make_changeset(
            BUILD=(
                "packages/check-cert/BUILD",
                "packages/neb/BUILD.bazel",
            )
        )
        result = _get_build_file_packages(cs)
        assert sorted(result) == [
            "//packages/check-cert/...",
            "//packages/neb/...",
        ]

    def test_global_overrides_packages(self) -> None:
        """MODULE.bazel change returns //... even with specific BUILD files."""
        cs = _make_changeset(
            BUILD=(
                "MODULE.bazel",
                "packages/check-cert/BUILD",
            )
        )
        result = _get_build_file_packages(cs)
        assert result == ["//..."]


# ---------------------------------------------------------------------------
# _parse_target tests
# ---------------------------------------------------------------------------


class TestParseTarget:
    """Tests for parsing bazel query output into BazelTarget."""

    def test_rust_binary(self) -> None:
        t = _parse_target("rust_binary", "//packages/check-cert:check-cert")
        assert t.kind == BazelTargetKind.RUST_BINARY
        assert t.label == "//packages/check-cert:check-cert"
        assert t.package == "packages/check-cert"

    def test_cc_library(self) -> None:
        t = _parse_target("cc_library", "//packages/neb:neb_base")
        assert t.kind == BazelTargetKind.CC_LIBRARY
        assert t.package == "packages/neb"

    def test_unknown_kind_maps_to_other(self) -> None:
        t = _parse_target("unknown_rule_xyz", "//foo:bar")
        assert t.kind == BazelTargetKind.OTHER

    def test_nested_package_path(self) -> None:
        t = _parse_target("cc_library", "//non-free/packages/cmc:cmc_base")
        assert t.package == "non-free/packages/cmc"


# ---------------------------------------------------------------------------
# resolve_bazel_targets tests
# ---------------------------------------------------------------------------


class TestResolveBazelTargets:
    """Tests for resolve_bazel_targets with manifest-based resolution."""

    def test_python_only_returns_empty(self, tmp_path: Path) -> None:
        """Python-only changeset needs no Bazel resolution."""
        cs = _make_changeset(PYTHON=("cmk/gui/views.py",))
        result = resolve_bazel_targets(cs, tmp_path)
        assert result.is_empty is True
        assert result.files_queried == 0
        assert result.from_cache is False
        assert result.query_time_ms == 0

    def test_rust_files_returns_targets(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Rust files are resolved via manifest prefix matching."""
        monkeypatch.setattr(
            "cmk.dev_deploy.execution.bazel_resolver.get_install_specs",
            lambda: (_make_install_spec("packages/check-cert", "//omd/packages/check-cert:pkg"),),
        )

        cs = _make_changeset(RUST=("packages/check-cert/src/main.rs",))
        result = resolve_bazel_targets(cs, tmp_path)

        assert not result.is_empty
        assert result.files_queried == 1
        assert "packages/check-cert" in result.targets[0].package

    def test_manifest_resolution_needs_no_subprocess(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Manifest-based resolution doesn't call subprocess at all."""
        monkeypatch.setattr(
            "cmk.dev_deploy.execution.bazel_resolver.get_install_specs",
            lambda: (_make_install_spec("packages/neb", "//packages/neb:neb_shared_files"),),
        )

        cs = _make_changeset(CPP=("packages/neb/src/NebCore.cc",))
        result = resolve_bazel_targets(cs, tmp_path)

        assert not result.is_empty
        assert "packages/neb" in result.targets[0].package

    def test_build_file_changes_add_package_targets(self, tmp_path: Path) -> None:
        """BUILD file changes add package-level targets without resolution."""
        cs = _make_changeset(BUILD=("packages/check-cert/BUILD",))
        result = resolve_bazel_targets(cs, tmp_path)

        assert not result.is_empty
        assert result.files_queried == 0  # no files sent to resolution
        assert "//packages/check-cert/..." in result.labels

    def test_mixed_bazel_and_build_files(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Both queryable files and BUILD changes produce merged results."""
        monkeypatch.setattr(
            "cmk.dev_deploy.execution.bazel_resolver.get_install_specs",
            lambda: (_make_install_spec("packages/check-cert", "//omd/packages/check-cert:pkg"),),
        )

        cs = _make_changeset(
            RUST=("packages/check-cert/src/main.rs",),
            BUILD=("packages/neb/BUILD",),
        )
        result = resolve_bazel_targets(cs, tmp_path)

        labels = result.labels
        assert any("packages/check-cert" in lbl for lbl in labels)
        assert "//packages/neb/..." in labels

    def test_empty_changeset_returns_empty(self, tmp_path: Path) -> None:
        cs = ChangeSet(build_commit=_COMMIT, files=(), categories={})
        result = resolve_bazel_targets(cs, tmp_path)
        assert result.is_empty is True
        assert result == BazelTargetSet(
            targets=(),
            files_queried=0,
            files_resolved=0,
            from_cache=False,
            query_time_ms=0,
        )
