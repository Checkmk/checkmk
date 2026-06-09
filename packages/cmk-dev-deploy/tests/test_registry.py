# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Unit tests for cmk.dev_deploy.manifest.registry (uncovered_changed_files)."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from cmk.dev_deploy.manifest.registry import uncovered_changed_files

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_specs(
    monkeypatch: pytest.MonkeyPatch,
    install_packages: tuple[str, ...] = (),
    config_prefixes: tuple[str, ...] = (),
    config_specs_with_files: tuple[tuple[str, tuple[str, ...]], ...] = (),
    wheel_packages: tuple[str, ...] = (),
) -> None:
    """Patch all three spec getters with simple mock objects.

    Args:
        config_prefixes: Config specs without an explicit files list (use
            source_prefix for coverage).
        config_specs_with_files: (source_prefix, (file_src, ...)) pairs for
            config specs that enumerate the files they deploy.  Coverage uses
            the file list, not the prefix.
    """
    install_specs = []
    for pkg in install_packages:
        spec = Mock()
        spec.package = pkg
        install_specs.append(spec)

    config_specs = []
    for prefix in config_prefixes:
        spec = Mock()
        spec.source_prefix = prefix
        spec.files = ()
        config_specs.append(spec)
    for prefix, files in config_specs_with_files:
        spec = Mock()
        spec.source_prefix = prefix
        spec.files = tuple(Mock(src=src) for src in files)
        config_specs.append(spec)

    wheel_prefixes = tuple(pkg + "/" for pkg in wheel_packages)

    monkeypatch.setattr("cmk.dev_deploy.manifest.registry.get_install_specs", lambda: install_specs)
    monkeypatch.setattr("cmk.dev_deploy.manifest.registry.get_config_specs", lambda: config_specs)
    monkeypatch.setattr(
        "cmk.dev_deploy.manifest.registry.get_wheel_prefixes", lambda: wheel_prefixes
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestUncoveredChangedFiles:
    """Tests for uncovered_changed_files."""

    def test_empty_changed_files(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _mock_specs(monkeypatch)
        assert uncovered_changed_files(()) == []

    def test_all_files_covered(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _mock_specs(
            monkeypatch,
            install_packages=("packages/livestatus",),
            config_prefixes=("agents/",),
            wheel_packages=("packages/cmk-ccc",),
        )
        changed = (
            "packages/livestatus/src/main.cc",
            "agents/check_mk_agent.linux",
            "packages/cmk-ccc/cmk/ccc/foo.py",
        )
        assert uncovered_changed_files(changed) == []

    def test_root_file_skipped(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _mock_specs(monkeypatch)
        # Files without "/" are in repo root and should be skipped (not reported)
        assert uncovered_changed_files(("Makefile", ".gitignore")) == []

    def test_uncovered_file_returned(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _mock_specs(monkeypatch)
        result = uncovered_changed_files(("unknown/dir/file.py",))
        assert result == ["unknown/dir/file.py"]

    def test_mix_covered_and_uncovered(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _mock_specs(
            monkeypatch,
            install_packages=("packages/livestatus",),
        )
        changed = (
            "packages/livestatus/src/main.cc",
            "some/other/file.py",
            "another/uncovered.txt",
        )
        result = uncovered_changed_files(changed)
        assert result == ["another/uncovered.txt", "some/other/file.py"]

    def test_result_is_sorted(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _mock_specs(monkeypatch)
        changed = (
            "zzz/file.py",
            "aaa/file.py",
            "mmm/file.py",
        )
        result = uncovered_changed_files(changed)
        assert result == sorted(result)
        assert result == ["aaa/file.py", "mmm/file.py", "zzz/file.py"]

    def test_config_spec_with_files_uses_explicit_list(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Config specs with an explicit files list cover only those files.

        Mirrors the real //omd:info_files spec: source_prefix collapses to
        ``omd/`` (commonpath of two siblings at different depths) but the
        spec only deploys those two files.  A sibling like
        ``omd/packages/Python/sitecustomize.py`` is NOT in the files list
        and must be reported as uncovered, not silently swallowed by the
        broad source_prefix.
        """
        _mock_specs(
            monkeypatch,
            config_specs_with_files=(("omd/", ("omd/distros/UBUNTU_24.04.mk", "omd/omd.info")),),
        )
        changed = (
            "omd/distros/UBUNTU_24.04.mk",
            "omd/omd.info",
            "omd/packages/Python/sitecustomize.py",
        )
        result = uncovered_changed_files(changed)
        assert result == ["omd/packages/Python/sitecustomize.py"]

    def test_config_spec_without_files_falls_back_to_prefix(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A config spec with no enumerated files uses source_prefix coverage."""
        _mock_specs(monkeypatch, config_prefixes=("agents/",))
        changed = (
            "agents/check_mk_agent.linux",
            "agents/plugins/whatever",
        )
        assert uncovered_changed_files(changed) == []
