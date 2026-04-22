# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Unit tests for cmk.dev_deploy.site.overlay module."""

import subprocess
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# The conftest stubs out cmk.dev_deploy.site.overlay for tests that only need
# the public mount/teardown entry points.  This module tests the real overlay
# module, so drop the stub before importing.
sys.modules.pop("cmk.dev_deploy.site.overlay", None)

from cmk.dev_deploy.errors import OverlayError  # noqa: E402
from cmk.dev_deploy.site import overlay  # noqa: E402


class TestSiteTmpfsMount:
    """_site_tmpfs_mount returns the tmpfs path under <site_root>/tmp or None."""

    def test_detects_tmpfs_at_site_tmp(self, tmp_path: Path) -> None:
        site_root = tmp_path / "heute"
        site_root.mkdir()
        mounts = (
            "proc /proc proc rw,nosuid,nodev,noexec,relatime 0 0\n"
            f"tmpfs {site_root}/tmp tmpfs rw,relatime,uid=1000,gid=1000 0 0\n"
        )
        with patch("cmk.dev_deploy.site.overlay._read_proc_mounts", return_value=mounts):
            assert overlay._site_tmpfs_mount(site_root) == f"{site_root}/tmp"  # noqa: SLF001

    @pytest.mark.parametrize(
        "mounts_template",
        [
            pytest.param("proc /proc proc rw 0 0\n", id="no_tmpfs"),
            pytest.param("something {site_root}/tmp ext4 rw 0 0\n", id="non_tmpfs_at_site_tmp"),
            pytest.param("tmpfs {tmp_path}/other/tmp tmpfs rw 0 0\n", id="tmpfs_on_other_site"),
            pytest.param("tmpfs {site_root}/tmp/sub tmpfs rw 0 0\n", id="tmpfs_nested_below_tmp"),
        ],
    )
    def test_returns_none(self, tmp_path: Path, mounts_template: str) -> None:
        site_root = tmp_path / "heute"
        site_root.mkdir()
        mounts = mounts_template.format(site_root=site_root, tmp_path=tmp_path)
        with patch("cmk.dev_deploy.site.overlay._read_proc_mounts", return_value=mounts):
            assert overlay._site_tmpfs_mount(site_root) is None  # noqa: SLF001

    def test_returns_none_when_proc_unreadable(self, tmp_path: Path) -> None:
        site_root = tmp_path / "heute"
        site_root.mkdir()
        with patch("cmk.dev_deploy.site.overlay._read_proc_mounts", return_value=None):
            assert overlay._site_tmpfs_mount(site_root) is None  # noqa: SLF001


@dataclass(frozen=True)
class _Stubs:
    site_root: Path
    run_as_root: MagicMock
    tmpfs: MagicMock


class TestEnsureOverlayTmpfsHandling:
    """ensure_overlay unmounts any pre-existing tmpfs before mounting the overlay."""

    @pytest.fixture
    def stubs(self, tmp_path: Path) -> Iterator[_Stubs]:
        """Stub out everything ensure_overlay touches except the tmpfs + mount calls."""
        site_root = tmp_path / "omd" / "sites" / "heute"
        site_root.mkdir(parents=True)

        with (
            patch("cmk.dev_deploy.site.overlay.is_overlay_active", return_value=False),
            patch("cmk.dev_deploy.site.overlay._ensure_overlay_dirs"),
            patch("cmk.dev_deploy.site.overlay._wipe_stale_overlay", return_value=False),
            patch("cmk.dev_deploy.site.overlay._materialize_symlinks"),
            patch("cmk.dev_deploy.site.overlay._run_omd_via_sudo"),
            patch("cmk.dev_deploy.site.overlay.inject_ssh_key"),
            patch("cmk.dev_deploy.site.overlay._restore_capabilities"),
            patch("cmk.dev_deploy.site.overlay._save_site_inode"),
            patch("cmk.dev_deploy.site.overlay.get_real_user", return_value="dev"),
            patch("cmk.dev_deploy.site.overlay.run_as_root") as mock_run_as_root,
            patch("cmk.dev_deploy.site.overlay._site_tmpfs_mount") as mock_tmpfs,
        ):
            mock_run_as_root.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="", stderr=""
            )
            yield _Stubs(site_root=site_root, run_as_root=mock_run_as_root, tmpfs=mock_tmpfs)

    def test_unmounts_tmpfs_before_overlay_mount(self, stubs: _Stubs) -> None:
        stubs.tmpfs.return_value = f"{stubs.site_root}/tmp"

        overlay.ensure_overlay(stubs.site_root, MagicMock())

        calls = [tuple(c.args[0]) for c in stubs.run_as_root.call_args_list]
        umount_idx = next(
            i for i, c in enumerate(calls) if c[:2] == ("umount", f"{stubs.site_root}/tmp")
        )
        mount_idx = next(
            i for i, c in enumerate(calls) if c[:2] == ("mount", "-t") and c[2] == "overlay"
        )
        assert umount_idx < mount_idx

    def test_skips_umount_when_no_tmpfs(self, stubs: _Stubs) -> None:
        stubs.tmpfs.return_value = None

        overlay.ensure_overlay(stubs.site_root, MagicMock())

        umount_calls = [c for c in stubs.run_as_root.call_args_list if c.args[0][:1] == ["umount"]]
        assert umount_calls == []

    def test_umount_failure_raises_and_leaves_site_stopped(self, stubs: _Stubs) -> None:
        stubs.tmpfs.return_value = f"{stubs.site_root}/tmp"

        def run_side_effect(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            if cmd[:1] == ["umount"]:
                return subprocess.CompletedProcess(args=cmd, returncode=1, stdout="", stderr="busy")
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

        stubs.run_as_root.side_effect = run_side_effect
        with (
            patch("cmk.dev_deploy.site.overlay._run_omd_via_sudo") as mock_omd,
            pytest.raises(OverlayError, match="Failed to unmount tmpfs"),
        ):
            overlay.ensure_overlay(stubs.site_root, MagicMock())
        # Site must NOT be restarted after a umount failure.  Restarting would
        # let services reattach to the busy mount, masking which process is
        # holding files open and preventing the user from diagnosing it.
        start_calls = [call for call in mock_omd.call_args_list if call.args[1] == "start"]
        assert start_calls == [], "site must stay stopped after umount failure for diagnosis"
