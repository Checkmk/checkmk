# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Unit tests for cmk.dev_deploy.site.preparation (backend seam)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from cmk.dev_deploy.errors import DeployError
from cmk.dev_deploy.site import preparation, sudoers
from cmk.dev_deploy.site.preparation import (
    check_backend_conflict,
    CloneBackend,
    create_backend,
    OverlayBackend,
    resolve_backend_name,
)
from cmk.dev_deploy.site.privilege import SSHState

_SITE_ROOT = Path("/omd/sites/v260")


class TestResolveBackendName:
    def test_explicit_flag_wins(self) -> None:
        assert resolve_backend_name("overlay", "clone", _SITE_ROOT) == "overlay"

    def test_recorded_state_second(self) -> None:
        assert resolve_backend_name(None, "clone", _SITE_ROOT) == "clone"

    def test_active_clone_detected_third(self) -> None:
        with patch.object(preparation, "is_clone_active", return_value=True):
            assert resolve_backend_name(None, "", _SITE_ROOT) == "clone"

    def test_default_overlay(self) -> None:
        with patch.object(preparation, "is_clone_active", return_value=False):
            assert resolve_backend_name(None, "", _SITE_ROOT) == "overlay"


class TestCreateBackend:
    def test_overlay(self) -> None:
        backend = create_backend("overlay", SSHState())
        assert isinstance(backend, OverlayBackend)
        assert backend.name == "overlay"

    def test_clone(self) -> None:
        backend = create_backend("clone", SSHState())
        assert isinstance(backend, CloneBackend)
        assert backend.name == "clone"

    def test_unknown_raises(self) -> None:
        with pytest.raises(DeployError, match="Unknown site preparation backend"):
            create_backend("teleport", SSHState())


class TestCheckBackendConflict:
    @pytest.mark.parametrize(
        ("name", "overlay_active", "clone_active", "conflict"),
        [
            pytest.param("clone", True, False, "OverlayFS", id="clone_vs_mounted_overlay"),
            pytest.param("overlay", False, True, "clone", id="overlay_vs_active_clone"),
            pytest.param("overlay", True, False, None, id="overlay_on_overlay_ok"),
            pytest.param("clone", False, True, None, id="clone_on_clone_ok"),
            pytest.param("overlay", False, False, None, id="fresh_site_ok"),
        ],
    )
    def test_conflicts(
        self, name: str, overlay_active: bool, clone_active: bool, conflict: str | None
    ) -> None:
        with (
            patch.object(preparation, "is_overlay_active", return_value=overlay_active),
            patch.object(preparation, "is_clone_active", return_value=clone_active),
        ):
            message = check_backend_conflict(name, _SITE_ROOT)
        if conflict is None:
            assert message is None
        else:
            assert message is not None
            assert conflict in message


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


class TestOverlayBackend:
    """The wrapper must delegate verbatim to the overlay module."""

    def test_is_active_delegates(self) -> None:
        backend = OverlayBackend(SSHState())
        with patch.object(preparation, "is_overlay_active", return_value=True) as active:
            assert backend.is_active(_SITE_ROOT) is True
        active.assert_called_once_with(_SITE_ROOT)

    def test_ensure_delegates_with_ssh_state(self) -> None:
        ssh_state = SSHState()
        backend = OverlayBackend(ssh_state)
        with patch.object(preparation, "ensure_overlay") as ensure:
            backend.ensure(_SITE_ROOT)
        ensure.assert_called_once_with(_SITE_ROOT, ssh_state)

    def test_teardown_delegates(self) -> None:
        backend = OverlayBackend(SSHState())
        with (
            patch.object(preparation, "ensure_sudo") as sudo,
            patch.object(preparation, "teardown_overlay") as teardown,
        ):
            backend.teardown(_SITE_ROOT)
        sudo.assert_called_once_with()
        teardown.assert_called_once_with(_SITE_ROOT)

    @pytest.mark.parametrize(
        ("active", "full", "expect_sudo"),
        [
            pytest.param(False, False, True, id="inactive_needs_sudo"),
            pytest.param(True, True, True, id="full_needs_sudo"),
            pytest.param(True, False, False, id="active_steady_state_no_sudo"),
        ],
    )
    def test_prepare_privileges(self, active: bool, full: bool, expect_sudo: bool) -> None:
        backend = OverlayBackend(SSHState())
        with (
            patch.object(preparation, "is_overlay_active", return_value=active),
            patch.object(preparation, "ensure_sudo") as sudo,
        ):
            backend.prepare_privileges(_SITE_ROOT, full=full)
        assert sudo.called is expect_sudo
