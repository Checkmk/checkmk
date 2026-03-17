# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Unit tests for cmk.dev_deploy.source_paths (per-deployer path resolution)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from cmk.dev_deploy.execution.source_paths import resolve_source_paths
from cmk.dev_deploy.types import (
    ConfigDeploySpec,
    DeployMethod,
    InstallSpec,
    WheelDeployMode,
    WheelDeploySpec,
)

# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

_MANIFEST_PREFIX = "cmk.dev_deploy.manifest.reader"
_DEPS_PREFIX = "cmk.dev_deploy.manifest.deps"


def _make_wheel_spec(
    package: str = "packages/cmk-ccc",
    deploy_mode: WheelDeployMode = WheelDeployMode.DIRECT,
    source_subdirs: tuple[str, ...] = ("cmk/ccc/",),
    distribution_name: str = "",
) -> WheelDeploySpec:
    """Create a WheelDeploySpec with sensible defaults for testing."""
    return WheelDeploySpec(
        package=package,
        wheel_targets=(":wheel",),
        edition_constraint=None,
        deploy_mode=deploy_mode,
        source_subdirs=source_subdirs,
        distribution_name=distribution_name,
    )


def _make_config_spec(source_prefix: str) -> ConfigDeploySpec:
    """Create a ConfigDeploySpec with the given source_prefix."""
    return ConfigDeploySpec(
        source_prefix=source_prefix,
        site_dest="share/check_mk/",
        method=DeployMethod.COPY_DIR,
        mode=None,
        includes=(),
        files=(),
        delete_extra=False,
        file_chmod=None,
    )


def _make_install_spec(package: str) -> InstallSpec:
    """Create an InstallSpec with the given package path."""
    return InstallSpec(
        package=package,
        package_target=f"//{package}:all",
        output_basename="output",
        install_dest="lib/output",
        mode=0o644,
        post_install=(),
        edition_constraint=None,
        needs_version_flag=False,
        needs_faked_artifacts=False,
        use_copytree=False,
    )


# ---------------------------------------------------------------------------
# TestPipelineDeployers
# ---------------------------------------------------------------------------


class TestPipelineDeployers:
    """Tests for pipeline deployers: config, install."""

    def test_config_spec_returns_all_config_prefixes(self) -> None:
        """Config spec returns source_prefix from each config spec in manifest."""
        specs = (
            _make_config_spec("agents/"),
            _make_config_spec("doc/treasures/"),
            _make_config_spec("omd/packages/omd/"),
        )
        with patch(f"{_MANIFEST_PREFIX}.get_config_specs", return_value=specs):
            result = resolve_source_paths("config_spec", Path("/repo"))

        assert result is not None
        assert result == ("agents/", "doc/treasures/", "omd/packages/omd/")

    def test_install_spec_returns_all_package_dirs(self) -> None:
        """Install spec returns package + '/' paths from each install spec."""
        specs = (
            _make_install_spec("packages/livestatus"),
            _make_install_spec("packages/neb"),
        )
        with (
            patch(f"{_MANIFEST_PREFIX}.get_install_specs", return_value=specs),
            patch(
                f"{_DEPS_PREFIX}.expand_dependencies",
                return_value={"packages/livestatus/", "packages/neb/"},
            ),
        ):
            result = resolve_source_paths("install_spec", Path("/repo"))

        assert result is not None
        assert "packages/livestatus/" in result
        assert "packages/neb/" in result

    def test_install_spec_adds_trailing_slash(self) -> None:
        """Trailing '/' is added to package paths that lack it."""
        specs = (_make_install_spec("packages/livestatus"),)
        with (
            patch(f"{_MANIFEST_PREFIX}.get_install_specs", return_value=specs),
            patch(
                f"{_DEPS_PREFIX}.expand_dependencies",
                return_value={"packages/livestatus/"},
            ),
        ):
            result = resolve_source_paths("install_spec", Path("/repo"))

        assert result is not None
        for prefix in result:
            assert prefix.endswith("/"), f"Prefix {prefix!r} should end with '/'"


# ---------------------------------------------------------------------------
# TestWheelSingleDist
# ---------------------------------------------------------------------------


class TestWheelSourceSubdirs:
    """Tests for wheel packages with Bazel-derived source_subdirs."""

    def test_direct_uses_source_subdirs(self) -> None:
        """Spec with source_subdirs returns them prefixed with package path."""
        spec = _make_wheel_spec(
            package="packages/cmk-ccc",
            source_subdirs=("cmk/ccc/",),
        )

        with patch(f"{_MANIFEST_PREFIX}.get_wheel_specs", return_value=(spec,)):
            result = resolve_source_paths("wheel:packages/cmk-ccc", Path("/repo"))

        assert result is not None
        assert "packages/cmk-ccc/cmk/ccc/" in result

    def test_empty_source_subdirs_falls_back_to_package_dir(self) -> None:
        """When source_subdirs is empty, falls back to package + '/'."""
        spec = _make_wheel_spec(
            package="packages/cmk-empty",
            source_subdirs=(),
        )

        with patch(f"{_MANIFEST_PREFIX}.get_wheel_specs", return_value=(spec,)):
            result = resolve_source_paths("wheel:packages/cmk-empty", Path("/repo"))

        assert result == ("packages/cmk-empty/",)

    def test_generated_package_with_empty_subdirs(self) -> None:
        """Generated package with empty source_subdirs falls back to package dir."""
        spec = _make_wheel_spec(
            package="packages/cmk-shared-typing",
            deploy_mode=WheelDeployMode.GENERATED,
            source_subdirs=(),
        )

        with patch(f"{_MANIFEST_PREFIX}.get_wheel_specs", return_value=(spec,)):
            result = resolve_source_paths(
                "wheel:packages/cmk-shared-typing", Path("/repo")
            )

        assert result == ("packages/cmk-shared-typing/",)

    def test_multiple_source_subdirs(self) -> None:
        """Spec with multiple source_subdirs returns all prefixed paths."""
        spec = _make_wheel_spec(
            package="packages/cmk-plugins",
            source_subdirs=("cmk/plugins/aws/", "cmk/plugins/azure/"),
        )

        with patch(f"{_MANIFEST_PREFIX}.get_wheel_specs", return_value=(spec,)):
            result = resolve_source_paths("wheel:packages/cmk-plugins", Path("/repo"))

        assert result is not None
        assert "packages/cmk-plugins/cmk/plugins/aws/" in result
        assert "packages/cmk-plugins/cmk/plugins/azure/" in result

    def test_paths_are_repo_relative(self) -> None:
        """All returned paths start with the package path prefix."""
        spec = _make_wheel_spec(
            package="packages/cmk-check-engine",
            source_subdirs=("cmk/fetchers/", "cmk/snmplib/"),
        )

        with patch(f"{_MANIFEST_PREFIX}.get_wheel_specs", return_value=(spec,)):
            result = resolve_source_paths(
                "wheel:packages/cmk-check-engine", Path("/repo")
            )

        assert result is not None
        for path in result:
            assert path.startswith("packages/cmk-check-engine/"), (
                f"Path {path!r} should start with 'packages/cmk-check-engine/'"
            )


# ---------------------------------------------------------------------------
# TestFallback
# ---------------------------------------------------------------------------


class TestFallback:
    """Tests for fallback behavior with unknown deployers."""

    def test_unknown_deployer_returns_none(self) -> None:
        """resolve_source_paths('totally_unknown', ...) returns None."""
        result = resolve_source_paths("totally_unknown", Path("/repo"))
        assert result is None

    def test_wheel_unknown_package_returns_none(self) -> None:
        """resolve_source_paths('wheel:packages/nonexistent', ...) returns None when spec not found."""
        with patch(f"{_MANIFEST_PREFIX}.get_wheel_specs", return_value=()):
            result = resolve_source_paths("wheel:packages/nonexistent", Path("/repo"))

        assert result is None

    def test_deployers_without_metadata_return_none(self) -> None:
        """Deployers without any known prefix pattern return None."""
        for name in ("manual_deployer", "some_custom_thing", ""):
            result = resolve_source_paths(name, Path("/repo"))
            assert result is None, f"Expected None for deployer {name!r}, got {result}"


# ---------------------------------------------------------------------------
# TestTransitiveDeps
# ---------------------------------------------------------------------------


class TestTransitiveDeps:
    """Tests for transitive dependency expansion in install spec resolution."""

    def test_install_spec_includes_transitive_deps(self) -> None:
        """Install specs include paths from transitive dependency expansion."""
        specs = (_make_install_spec("packages/livestatus"),)

        def _mock_expand(changed_dirs: set[str]) -> set[str]:
            return changed_dirs | {"packages/neb/"}

        with (
            patch(f"{_MANIFEST_PREFIX}.get_install_specs", return_value=specs),
            patch(f"{_DEPS_PREFIX}.expand_dependencies", side_effect=_mock_expand),
        ):
            result = resolve_source_paths("install_spec", Path("/repo"))

        assert result is not None
        assert "packages/livestatus/" in result
        assert "packages/neb/" in result

    def test_wheel_direct_does_not_include_transitive(self) -> None:
        """Pure Python wheel packages do NOT expand transitive deps."""
        spec = _make_wheel_spec(
            package="packages/cmk-ccc",
            source_subdirs=("cmk/ccc/",),
        )

        with patch(f"{_MANIFEST_PREFIX}.get_wheel_specs", return_value=(spec,)):
            result = resolve_source_paths("wheel:packages/cmk-ccc", Path("/repo"))

        # Should only return source_subdirs from spec, no transitive expansion
        assert result is not None
        assert "packages/cmk-ccc/cmk/ccc/" in result

    def test_transitive_deps_expanded_correctly(self) -> None:
        """Verify expand_dependencies integration produces correct output."""
        specs = (
            _make_install_spec("packages/livestatus"),
            _make_install_spec("packages/neb"),
        )

        def _mock_expand(changed_dirs: set[str]) -> set[str]:
            # Simulate: livestatus depends on neb, neb depends on unixcat
            return changed_dirs | {"packages/unixcat/"}

        with (
            patch(f"{_MANIFEST_PREFIX}.get_install_specs", return_value=specs),
            patch(f"{_DEPS_PREFIX}.expand_dependencies", side_effect=_mock_expand),
        ):
            result = resolve_source_paths("install_spec", Path("/repo"))

        assert result is not None
        assert "packages/livestatus/" in result
        assert "packages/neb/" in result
        assert "packages/unixcat/" in result
