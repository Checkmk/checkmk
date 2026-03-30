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
    wheel_packages: tuple[str, ...] = (),
) -> None:
    """Patch all three spec getters with simple mock objects."""
    install_specs = []
    for pkg in install_packages:
        spec = Mock()
        spec.package = pkg
        install_specs.append(spec)

    config_specs = []
    for prefix in config_prefixes:
        spec = Mock()
        spec.source_prefix = prefix
        config_specs.append(spec)

    wheel_specs = []
    for pkg in wheel_packages:
        spec = Mock()
        spec.package = pkg
        wheel_specs.append(spec)

    monkeypatch.setattr("cmk.dev_deploy.manifest.registry.get_install_specs", lambda: install_specs)
    monkeypatch.setattr("cmk.dev_deploy.manifest.registry.get_config_specs", lambda: config_specs)
    monkeypatch.setattr("cmk.dev_deploy.manifest.registry.get_wheel_specs", lambda: wheel_specs)


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
