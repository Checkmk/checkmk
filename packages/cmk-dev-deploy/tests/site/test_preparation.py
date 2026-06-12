# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Unit tests for cmk.dev_deploy.site.preparation (backend seam)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from cmk.dev_deploy.errors import DeployError
from cmk.dev_deploy.site import preparation
from cmk.dev_deploy.site.preparation import (
    create_backend,
    OverlayBackend,
    resolve_backend_name,
)
from cmk.dev_deploy.site.privilege import SSHState

_SITE_ROOT = Path("/omd/sites/v260")


class TestResolveBackendName:
    def test_explicit_flag_wins(self) -> None:
        assert resolve_backend_name("overlay", "clone") == "overlay"

    def test_recorded_state_second(self) -> None:
        assert resolve_backend_name(None, "clone") == "clone"

    def test_default_overlay(self) -> None:
        assert resolve_backend_name(None, "") == "overlay"


class TestCreateBackend:
    def test_overlay(self) -> None:
        backend = create_backend("overlay", SSHState())
        assert isinstance(backend, OverlayBackend)
        assert backend.name == "overlay"

    def test_unknown_raises(self) -> None:
        with pytest.raises(DeployError, match="Unknown site preparation backend"):
            create_backend("teleport", SSHState())


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
