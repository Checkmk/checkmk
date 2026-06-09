# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Unit tests for cmk.dev_deploy.source_paths (per-deployer path resolution)."""

from __future__ import annotations

from unittest.mock import patch

from cmk.dev_deploy.execution.source_paths import resolve_source_paths
from cmk.dev_deploy.types import ConfigDeploySpec, DeployMethod, InstallSpec

# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

_MANIFEST_PREFIX = "cmk.dev_deploy.manifest.reader"
_DEPS_PREFIX = "cmk.dev_deploy.manifest.deps"


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
            result = resolve_source_paths("config_spec")

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
            result = resolve_source_paths("install_spec")

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
            result = resolve_source_paths("install_spec")

        assert result is not None
        for prefix in result:
            assert prefix.endswith("/"), f"Prefix {prefix!r} should end with '/'"


# ---------------------------------------------------------------------------
# TestFallback
# ---------------------------------------------------------------------------


class TestFallback:
    """Tests for fallback behavior with unknown deployers."""

    def test_unknown_deployer_returns_none(self) -> None:
        """resolve_source_paths('totally_unknown', ...) returns None."""
        result = resolve_source_paths("totally_unknown")
        assert result is None

    def test_deployers_without_metadata_return_none(self) -> None:
        """Deployers without any known prefix pattern return None."""
        for name in ("manual_deployer", "some_custom_thing", ""):
            result = resolve_source_paths(name)
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
            result = resolve_source_paths("install_spec")

        assert result is not None
        assert "packages/livestatus/" in result
        assert "packages/neb/" in result

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
            result = resolve_source_paths("install_spec")

        assert result is not None
        assert "packages/livestatus/" in result
        assert "packages/neb/" in result
        assert "packages/unixcat/" in result
