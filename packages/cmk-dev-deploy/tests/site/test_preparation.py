# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Unit tests for cmk.dev_deploy.site.preparation (backend seam)."""

from pathlib import Path
from unittest.mock import patch

import pytest

from cmk.dev_deploy.errors import DeployError
from cmk.dev_deploy.site import preparation, sudoers
from cmk.dev_deploy.site.preparation import (
    check_backend_conflict,
    CloneBackend,
    create_backend,
    resolve_backend_name,
)

_SITE_ROOT = Path("/omd/sites/v260")


class TestResolveBackendName:
    def test_recorded_state_wins(self) -> None:
        assert resolve_backend_name("overlay", _SITE_ROOT) == "overlay"

    def test_active_clone_detected(self) -> None:
        with patch.object(preparation, "is_clone_active", return_value=True):
            assert resolve_backend_name("", _SITE_ROOT) == "clone"

    def test_default_clone(self) -> None:
        with patch.object(preparation, "is_clone_active", return_value=False):
            assert resolve_backend_name("", _SITE_ROOT) == "clone"


class TestCreateBackend:
    def test_clone(self) -> None:
        backend = create_backend("clone")
        assert isinstance(backend, CloneBackend)
        assert backend.name == "clone"

    def test_removed_overlay_raises_migration_error(self) -> None:
        with pytest.raises(DeployError, match="OverlayFS backend") as excinfo:
            create_backend("overlay")
        assert "umount" in str(excinfo.value)

    def test_unknown_raises(self) -> None:
        with pytest.raises(DeployError, match="Unknown site preparation backend"):
            create_backend("teleport")


class TestCheckBackendConflict:
    def test_leftover_overlay_mount_refused(self) -> None:
        with patch.object(preparation, "_overlay_mounted", return_value=True):
            message = check_backend_conflict(_SITE_ROOT)
        assert message is not None
        assert "umount" in message

    def test_clean_site_ok(self) -> None:
        with patch.object(preparation, "_overlay_mounted", return_value=False):
            assert check_backend_conflict(_SITE_ROOT) is None


class TestOverlayMounted:
    def test_detects_overlay_on_site_root(self, tmp_path: Path) -> None:
        mounts = f"overlay {tmp_path} overlay rw,lowerdir=/x 0 0\n"
        with patch.object(Path, "read_text", return_value=mounts):
            assert preparation._overlay_mounted(tmp_path) is True  # noqa: SLF001

    def test_ignores_other_mounts(self, tmp_path: Path) -> None:
        mounts = f"tmpfs {tmp_path} tmpfs rw 0 0\noverlay /elsewhere overlay rw 0 0\n"
        with patch.object(Path, "read_text", return_value=mounts):
            assert preparation._overlay_mounted(tmp_path) is False  # noqa: SLF001


class TestCloneBackend:
    def test_is_active_delegates(self) -> None:
        with patch.object(preparation, "is_clone_active", return_value=True) as active:
            assert CloneBackend().is_active(_SITE_ROOT) is True
        active.assert_called_once_with(_SITE_ROOT)

    def test_ensure_delegates(self) -> None:
        with patch.object(preparation, "ensure_clone") as ensure:
            CloneBackend().ensure(_SITE_ROOT)
        ensure.assert_called_once_with(_SITE_ROOT)

    def test_teardown_delegates(self) -> None:
        with patch.object(preparation, "teardown_clone") as teardown:
            CloneBackend().teardown(_SITE_ROOT)
        teardown.assert_called_once_with(_SITE_ROOT)

    def test_prepare_privileges_probe_ok(self) -> None:
        with (
            patch.object(sudoers, "probe", return_value=True) as probe,
            patch.object(sudoers, "bootstrap") as bootstrap,
            patch.object(sudoers, "ensure_dev_versions_dir") as ensure_dir,
        ):
            CloneBackend().prepare_privileges(_SITE_ROOT, full=False)
        probe.assert_called_once_with("v260")
        bootstrap.assert_not_called()
        ensure_dir.assert_called_once_with()

    def test_prepare_privileges_bootstraps_on_missing_rule(self) -> None:
        with (
            patch.object(sudoers, "probe", return_value=False),
            patch.object(sudoers, "bootstrap") as bootstrap,
            patch.object(sudoers, "ensure_dev_versions_dir"),
        ):
            CloneBackend().prepare_privileges(_SITE_ROOT, full=False)
        bootstrap.assert_called_once_with("v260")
