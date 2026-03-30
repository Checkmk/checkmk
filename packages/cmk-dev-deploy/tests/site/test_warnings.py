# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Tests for cmk.dev_deploy.warnings -- branch and edition mismatch detection."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from cmk.dev_deploy.site.warnings import (
    _required_edition_for_file,
    check_branch_mismatch,
    check_edition_mismatch,
)
from cmk.dev_deploy.types import ChangeSet, Edition, SiteInfo

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_site(
    name: str = "testsite",
    edition: Edition = Edition.COMMUNITY,
    build_commit: str | None = "abc123",
) -> SiteInfo:
    return SiteInfo(
        name=name,
        root=Path("/omd/sites") / name,
        edition=edition,
        version_string="2.6.0-2026.03.17." + edition.value,
        build_commit=build_commit,
    )


def _make_changes(
    files: tuple[str, ...],
    build_commit: str = "abc123",
) -> ChangeSet:
    return ChangeSet(
        build_commit=build_commit,
        files=files,
        categories={},
    )


def _empty_changes(build_commit: str = "abc123") -> ChangeSet:
    return ChangeSet(
        build_commit=build_commit,
        files=(),
        categories={},
    )


def _make_subprocess_result(
    returncode: int = 0,
    stdout: str = "",
    stderr: str = "",
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


# ---------------------------------------------------------------------------
# _required_edition_for_file
# ---------------------------------------------------------------------------


class TestRequiredEditionForFile:
    def test_regular_file_no_edition(self) -> None:
        assert _required_edition_for_file("cmk/gui/views.py") is None

    def test_nonfree_pro(self) -> None:
        assert _required_edition_for_file("nonfree/pro/foo.py") == "pro"

    def test_nonfree_ultimate(self) -> None:
        assert _required_edition_for_file("nonfree/ultimate/bar.py") == "ultimate"

    def test_nonfree_ultimatemt(self) -> None:
        assert _required_edition_for_file("nonfree/ultimatemt/baz.py") == "ultimatemt"

    def test_nonfree_cloud(self) -> None:
        assert _required_edition_for_file("nonfree/cloud/bar.py") == "cloud"

    def test_non_free_legacy_maps_to_pro(self) -> None:
        assert _required_edition_for_file("non-free/baz.py") == "pro"

    def test_nested_path(self) -> None:
        assert _required_edition_for_file("packages/cmk-agent/nonfree/cloud/agent.py") == "cloud"

    def test_empty_string(self) -> None:
        assert _required_edition_for_file("") is None


# ---------------------------------------------------------------------------
# check_branch_mismatch
# ---------------------------------------------------------------------------


class TestCheckBranchMismatch:
    """Tests for check_branch_mismatch using monkeypatch on subprocess.run."""

    def test_build_commit_none_returns_none(self, tmp_path: Path) -> None:
        result = check_branch_mismatch(None, tmp_path)
        assert result is None

    def test_git_rev_parse_fails_returns_none(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setattr(
            "cmk.dev_deploy.site.warnings.subprocess.run",
            lambda *_a, **_kw: _make_subprocess_result(returncode=128, stderr="fatal"),
        )
        assert check_branch_mismatch("abc123", tmp_path) is None

    def test_detached_head_returns_none(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setattr(
            "cmk.dev_deploy.site.warnings.subprocess.run",
            lambda *_a, **_kw: _make_subprocess_result(stdout="HEAD\n"),
        )
        assert check_branch_mismatch("abc123", tmp_path) is None

    def test_empty_branch_returns_none(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setattr(
            "cmk.dev_deploy.site.warnings.subprocess.run",
            lambda *_a, **_kw: _make_subprocess_result(stdout="  \n"),
        )
        assert check_branch_mismatch("abc123", tmp_path) is None

    def test_build_commit_is_ancestor_returns_none(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """When build_commit is ancestor of current branch, no warning."""
        calls: list[list[str]] = []

        def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
            cmd = args[0] if args else kwargs.get("args", [])
            assert isinstance(cmd, list)
            calls.append(cmd)
            if "rev-parse" in cmd:
                return _make_subprocess_result(stdout="my-feature\n")
            # merge-base --is-ancestor returns 0 when it IS an ancestor
            return _make_subprocess_result(returncode=0)

        monkeypatch.setattr("cmk.dev_deploy.site.warnings.subprocess.run", fake_run)
        assert check_branch_mismatch("abc123", tmp_path) is None
        assert len(calls) == 2

    def test_branch_mismatch_returns_warning(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """When build_commit is NOT ancestor, returns warning string."""
        call_count = 0

        def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
            nonlocal call_count
            cmd = args[0] if args else kwargs.get("args", [])
            assert isinstance(cmd, list)
            call_count += 1
            if "rev-parse" in cmd:
                return _make_subprocess_result(stdout="my-feature\n")
            if "merge-base" in cmd:
                # returncode 1 = not an ancestor
                return _make_subprocess_result(returncode=1)
            if "branch" in cmd and "--contains" in cmd:
                return _make_subprocess_result(stdout="main\n")
            return _make_subprocess_result()

        monkeypatch.setattr("cmk.dev_deploy.site.warnings.subprocess.run", fake_run)
        result = check_branch_mismatch("abc123def456", tmp_path)
        assert result is not None
        assert "my-feature" in result
        assert "Branch mismatch" in result

    def test_branch_mismatch_with_unknown_build_branch(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """When build branch cannot be found, shows commit hash instead."""

        def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
            cmd = args[0] if args else kwargs.get("args", [])
            assert isinstance(cmd, list)
            if "rev-parse" in cmd:
                return _make_subprocess_result(stdout="my-feature\n")
            if "merge-base" in cmd:
                return _make_subprocess_result(returncode=1)
            if "branch" in cmd and "--contains" in cmd:
                # No branch found
                return _make_subprocess_result(returncode=1, stdout="")
            return _make_subprocess_result()

        monkeypatch.setattr("cmk.dev_deploy.site.warnings.subprocess.run", fake_run)
        commit = "abc123def456789000"
        result = check_branch_mismatch(commit, tmp_path)
        assert result is not None
        assert "commit abc123def456" in result

    def test_timeout_on_rev_parse_returns_none(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        def fake_run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
            raise subprocess.TimeoutExpired(cmd="git", timeout=5)

        monkeypatch.setattr("cmk.dev_deploy.site.warnings.subprocess.run", fake_run)
        assert check_branch_mismatch("abc123", tmp_path) is None

    def test_timeout_on_merge_base_returns_none(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        call_count = 0

        def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
            nonlocal call_count
            call_count += 1
            cmd = args[0] if args else kwargs.get("args", [])
            assert isinstance(cmd, list)
            if "rev-parse" in cmd:
                return _make_subprocess_result(stdout="my-feature\n")
            # Second call (merge-base) times out
            raise subprocess.TimeoutExpired(cmd="git", timeout=5)

        monkeypatch.setattr("cmk.dev_deploy.site.warnings.subprocess.run", fake_run)
        assert check_branch_mismatch("abc123", tmp_path) is None
        assert call_count == 2

    def test_oserror_on_rev_parse_returns_none(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        def fake_run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
            raise OSError("git not found")

        monkeypatch.setattr("cmk.dev_deploy.site.warnings.subprocess.run", fake_run)
        assert check_branch_mismatch("abc123", tmp_path) is None


# ---------------------------------------------------------------------------
# check_edition_mismatch
# ---------------------------------------------------------------------------


class TestCheckEditionMismatch:
    def test_changes_none_returns_none(self) -> None:
        site = _make_site()
        assert check_edition_mismatch(None, site) is None

    def test_site_none_returns_none(self) -> None:
        changes = _make_changes(files=("cmk/gui/views.py",))
        assert check_edition_mismatch(changes, None) is None

    def test_empty_changes_returns_none(self) -> None:
        site = _make_site()
        changes = _empty_changes()
        assert check_edition_mismatch(changes, site) is None

    def test_no_edition_specific_files_returns_none(self) -> None:
        site = _make_site(edition=Edition.COMMUNITY)
        changes = _make_changes(files=("cmk/gui/views.py", "cmk/utils/foo.py"))
        assert check_edition_mismatch(changes, site) is None

    def test_pro_file_on_community_site_warns(self) -> None:
        site = _make_site(edition=Edition.COMMUNITY)
        changes = _make_changes(files=("nonfree/pro/licensing.py",))
        result = check_edition_mismatch(changes, site)
        assert result is not None
        assert "Edition mismatch" in result
        assert "nonfree/pro/licensing.py" in result
        assert "1 changed file(s)" in result

    def test_pro_file_on_pro_site_no_warning(self) -> None:
        site = _make_site(edition=Edition.PRO)
        changes = _make_changes(files=("nonfree/pro/licensing.py",))
        assert check_edition_mismatch(changes, site) is None

    def test_ultimate_file_on_pro_site_warns(self) -> None:
        """Pro edition does not include ultimate files."""
        site = _make_site(edition=Edition.PRO)
        changes = _make_changes(files=("nonfree/ultimate/feature.py",))
        result = check_edition_mismatch(changes, site)
        assert result is not None
        assert "Edition mismatch" in result

    def test_ultimate_file_on_ultimate_site_no_warning(self) -> None:
        site = _make_site(edition=Edition.ULTIMATE)
        changes = _make_changes(files=("nonfree/ultimate/feature.py",))
        assert check_edition_mismatch(changes, site) is None

    def test_cloud_file_on_cloud_site_no_warning(self) -> None:
        site = _make_site(edition=Edition.CLOUD)
        changes = _make_changes(files=("nonfree/cloud/dashboard.py",))
        assert check_edition_mismatch(changes, site) is None

    def test_cloud_file_on_ultimate_site_warns(self) -> None:
        """Ultimate does NOT include cloud (non-linear hierarchy)."""
        site = _make_site(edition=Edition.ULTIMATE)
        changes = _make_changes(files=("nonfree/cloud/dashboard.py",))
        result = check_edition_mismatch(changes, site)
        assert result is not None

    def test_ultimatemt_file_on_cloud_site_warns(self) -> None:
        """Cloud does NOT include ultimatemt."""
        site = _make_site(edition=Edition.CLOUD)
        changes = _make_changes(files=("nonfree/ultimatemt/mt_feature.py",))
        result = check_edition_mismatch(changes, site)
        assert result is not None

    def test_pro_file_on_ultimate_site_no_warning(self) -> None:
        """Ultimate includes pro."""
        site = _make_site(edition=Edition.ULTIMATE)
        changes = _make_changes(files=("nonfree/pro/licensing.py",))
        assert check_edition_mismatch(changes, site) is None

    def test_pro_file_on_cloud_site_no_warning(self) -> None:
        """Cloud includes pro."""
        site = _make_site(edition=Edition.CLOUD)
        changes = _make_changes(files=("nonfree/pro/licensing.py",))
        assert check_edition_mismatch(changes, site) is None

    def test_non_free_legacy_on_community_warns(self) -> None:
        """non-free/ maps to pro, which community doesn't include."""
        site = _make_site(edition=Edition.COMMUNITY)
        changes = _make_changes(files=("non-free/agents/cmk-agent.py",))
        result = check_edition_mismatch(changes, site)
        assert result is not None

    def test_non_free_legacy_on_pro_no_warning(self) -> None:
        """non-free/ maps to pro, which pro site includes."""
        site = _make_site(edition=Edition.PRO)
        changes = _make_changes(files=("non-free/agents/cmk-agent.py",))
        assert check_edition_mismatch(changes, site) is None

    def test_multiple_mismatched_files_count(self) -> None:
        site = _make_site(edition=Edition.COMMUNITY)
        files = tuple(f"nonfree/pro/file{i}.py" for i in range(5))
        changes = _make_changes(files=files)
        result = check_edition_mismatch(changes, site)
        assert result is not None
        assert "5 changed file(s)" in result

    def test_more_than_10_mismatched_shows_and_more(self) -> None:
        site = _make_site(edition=Edition.COMMUNITY)
        files = tuple(f"nonfree/pro/file{i}.py" for i in range(15))
        changes = _make_changes(files=files)
        result = check_edition_mismatch(changes, site)
        assert result is not None
        assert "15 changed file(s)" in result
        assert "... and 5 more" in result
        # Only first 10 files should be listed individually
        assert "file0.py" in result
        assert "file9.py" in result
        # 11th file should NOT be listed individually
        assert "file10.py" not in result

    def test_exactly_10_mismatched_no_and_more(self) -> None:
        site = _make_site(edition=Edition.COMMUNITY)
        files = tuple(f"nonfree/pro/file{i}.py" for i in range(10))
        changes = _make_changes(files=files)
        result = check_edition_mismatch(changes, site)
        assert result is not None
        assert "10 changed file(s)" in result
        assert "... and" not in result

    def test_mixed_edition_and_regular_files(self) -> None:
        """Only edition-specific files that mismatch should appear in warning."""
        site = _make_site(edition=Edition.COMMUNITY)
        changes = _make_changes(
            files=(
                "cmk/gui/views.py",
                "nonfree/pro/licensing.py",
                "cmk/utils/foo.py",
            )
        )
        result = check_edition_mismatch(changes, site)
        assert result is not None
        assert "1 changed file(s)" in result
        assert "nonfree/pro/licensing.py" in result
        assert "cmk/gui/views.py" not in result

    def test_warning_mentions_site_name_and_edition(self) -> None:
        site = _make_site(name="v260", edition=Edition.COMMUNITY)
        changes = _make_changes(files=("nonfree/pro/foo.py",))
        result = check_edition_mismatch(changes, site)
        assert result is not None
        assert "v260" in result
        assert "community" in result
