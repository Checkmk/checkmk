# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Unit tests for cmk.dev_deploy.site_resolver (find_repo_root, resolve_site, helpers)."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from cmk.dev_deploy.errors import RepoNotFoundError, SiteError, SiteNotFoundError
from cmk.dev_deploy.site.site_resolver import (
    _read_edition,
    _resolve_site_name,
    find_repo_root,
    read_build_commit,
    resolve_site,
)
from cmk.dev_deploy.types import Edition

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_run(
    returncode: int = 0,
    stdout: str = "",
    stderr: str = "",
) -> object:
    """Create a callable that returns a mock CompletedProcess."""

    def _mock_run(
        cmd: list[str],
        **_kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=returncode,
            stdout=stdout,
            stderr=stderr,
        )

    return _mock_run


def _create_site_dir(
    tmp_path: Path,
    site_name: str,
    version: str = "2.6.0-2026.02.13.pro",
    commit: str | None = "a" * 40,
) -> Path:
    """Create a realistic OMD site directory structure under tmp_path.

    Returns the site root directory.
    """
    site_root = tmp_path / "omd" / "sites" / site_name
    site_root.mkdir(parents=True)

    # Create version symlink pointing to ../../versions/<version>
    versions_dir = tmp_path / "omd" / "versions" / version
    versions_dir.mkdir(parents=True, exist_ok=True)
    os.symlink(f"../../versions/{version}", site_root / "version")

    if commit is not None:
        doc_dir = site_root / "share" / "doc"
        doc_dir.mkdir(parents=True)
        (doc_dir / "COMMIT").write_text(commit)

    return site_root


# ---------------------------------------------------------------------------
# find_repo_root tests
# ---------------------------------------------------------------------------


def test_find_repo_root_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """find_repo_root returns a Path when git reports a valid repo root."""
    monkeypatch.setattr(
        "cmk.dev_deploy.site.site_resolver.subprocess.run",
        _make_mock_run(returncode=0, stdout="/home/dev/checkmk\n"),
    )
    result = find_repo_root()
    assert result == Path("/home/dev/checkmk")


def test_find_repo_root_not_in_repo(monkeypatch: pytest.MonkeyPatch) -> None:
    """find_repo_root raises RepoNotFoundError with recovery suggestion."""
    monkeypatch.setattr(
        "cmk.dev_deploy.site.site_resolver.subprocess.run",
        _make_mock_run(returncode=128, stderr="fatal: not a git repository"),
    )
    with pytest.raises(RepoNotFoundError, match="Not inside a git repository"):
        find_repo_root()


# ---------------------------------------------------------------------------
# _resolve_site_name tests (isolated name resolution)
# ---------------------------------------------------------------------------


def test_resolve_site_name_from_cli_arg(tmp_path: Path) -> None:
    """CLI --site argument is returned directly without any filesystem checks."""
    result = _resolve_site_name("mysite", tmp_path, tmp_path)
    assert result == "mysite"


def test_resolve_site_name_from_site_file(tmp_path: Path) -> None:
    """Site name is read from .site file at repo root."""
    (tmp_path / ".site").write_text("mysite\n")
    result = _resolve_site_name(None, tmp_path, tmp_path)
    assert result == "mysite"


def test_resolve_site_name_from_omd_sites_single(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """When omd sites returns exactly one site, it is auto-selected."""
    monkeypatch.setattr(
        "cmk.dev_deploy.site.site_resolver.subprocess.run",
        _make_mock_run(returncode=0, stdout="onlyone\n"),
    )
    monkeypatch.delenv("SITE", raising=False)
    result = _resolve_site_name(None, tmp_path, tmp_path)
    assert result == "onlyone"


def test_resolve_site_name_from_omd_sites_multiple(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """When omd sites returns multiple sites, SiteNotFoundError lists them."""
    monkeypatch.setattr(
        "cmk.dev_deploy.site.site_resolver.subprocess.run",
        _make_mock_run(returncode=0, stdout="site1\nsite2\nsite3\n"),
    )
    monkeypatch.delenv("SITE", raising=False)
    with pytest.raises(SiteNotFoundError, match="Multiple OMD sites found"):
        _resolve_site_name(None, tmp_path, tmp_path)


def test_resolve_site_name_no_site_found(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """When no site can be detected, SiteNotFoundError includes recovery steps."""
    monkeypatch.setattr(
        "cmk.dev_deploy.site.site_resolver.subprocess.run",
        _make_mock_run(returncode=1, stderr="omd not found"),
    )
    monkeypatch.delenv("SITE", raising=False)
    with pytest.raises(SiteNotFoundError, match="No OMD site found"):
        _resolve_site_name(None, tmp_path, tmp_path)


def test_resolve_site_name_from_env_var(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """SITE env var is used as fallback (with deprecation warning to stderr)."""
    monkeypatch.setenv("SITE", "envsite")
    result = _resolve_site_name(None, tmp_path, tmp_path)
    assert result == "envsite"


# ---------------------------------------------------------------------------
# resolve_site integration (mocked internals)
# ---------------------------------------------------------------------------


def test_resolve_site_full_pipeline(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """resolve_site wires name resolution, validation, edition, and commit reading."""
    # Mock all internals so resolve_site assembles a SiteInfo without real /omd/sites.
    with (
        patch(
            "cmk.dev_deploy.site.site_resolver._resolve_site_name",
            return_value="testsite",
        ),
        patch(
            "cmk.dev_deploy.site.site_resolver._read_edition",
            return_value=(Edition.PRO, "2.6.0-2026.02.13.pro"),
        ),
        patch(
            "cmk.dev_deploy.site.site_resolver.read_build_commit",
            return_value="b" * 40,
        ),
        patch(
            "cmk.dev_deploy.site.site_resolver._list_sites",
            return_value="testsite",
        ),
    ):
        # Monkeypatch the is_dir check on the Path object
        original_is_dir = Path.is_dir
        monkeypatch.setattr(
            Path,
            "is_dir",
            lambda self: True if str(self) == "/omd/sites/testsite" else original_is_dir(self),
        )

        result = resolve_site("testsite", tmp_path, tmp_path)

    assert result.name == "testsite"
    assert result.edition is Edition.PRO
    assert result.version_string == "2.6.0-2026.02.13.pro"
    assert result.build_commit == "b" * 40


def test_resolve_site_nonexistent_directory(tmp_path: Path) -> None:
    """resolve_site raises SiteNotFoundError when site directory does not exist."""
    with patch(
        "cmk.dev_deploy.site.site_resolver._list_sites",
        return_value="(none found)",
    ):
        with pytest.raises(SiteNotFoundError, match="Site directory does not exist"):
            resolve_site("nonexistent", tmp_path, tmp_path)


# ---------------------------------------------------------------------------
# _read_edition tests
# ---------------------------------------------------------------------------


def test_read_edition_pro(tmp_path: Path) -> None:
    """Version symlink with 'pro' suffix returns Edition.PRO."""
    site_root = _create_site_dir(tmp_path, "test", version="2.6.0-2026.02.13.pro")
    edition, version_string = _read_edition(site_root)
    assert edition is Edition.PRO
    assert version_string == "2.6.0-2026.02.13.pro"


def test_read_edition_community(tmp_path: Path) -> None:
    """Version symlink with 'community' suffix returns Edition.COMMUNITY."""
    site_root = _create_site_dir(tmp_path, "test", version="2.6.0-2026.01.01.community")
    edition, version_string = _read_edition(site_root)
    assert edition is Edition.COMMUNITY
    assert version_string == "2.6.0-2026.01.01.community"


def test_read_edition_missing_symlink(tmp_path: Path) -> None:
    """Missing version symlink raises SiteError with recovery suggestion."""
    site_root = tmp_path / "missing_site"
    site_root.mkdir(parents=True)
    with pytest.raises(SiteError, match="No version symlink"):
        _read_edition(site_root)


# ---------------------------------------------------------------------------
# read_build_commit tests
# ---------------------------------------------------------------------------


def test_read_build_commit_present(tmp_path: Path) -> None:
    """COMMIT file with valid 40-char hash is returned."""
    site_root = _create_site_dir(tmp_path, "test", commit="a" * 40)
    result = read_build_commit(site_root)
    assert result == "a" * 40


def test_read_build_commit_missing(tmp_path: Path) -> None:
    """Missing COMMIT file returns None."""
    site_root = _create_site_dir(tmp_path, "test", commit=None)
    result = read_build_commit(site_root)
    assert result is None


def test_read_build_commit_invalid(tmp_path: Path) -> None:
    """COMMIT file with non-40-char content returns None."""
    site_root = _create_site_dir(tmp_path, "test", commit=None)
    doc_dir = site_root / "share" / "doc"
    doc_dir.mkdir(parents=True, exist_ok=True)
    (doc_dir / "COMMIT").write_text("short_hash")
    result = read_build_commit(site_root)
    assert result is None
