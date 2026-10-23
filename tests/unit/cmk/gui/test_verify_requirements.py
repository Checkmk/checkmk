#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc.user import UserId
from cmk.gui.exceptions import MKAuthException, MKUserError
from cmk.gui.session import session
from cmk.gui.session_context import UserContext
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.verify_requirements import verify_requirements

_PERMISSION = "general.edit_profile"
_NO_PERMISSIONS = UserPermissions({}, {}, {}, [])


@pytest.mark.usefixtures("request_context")
def test_raises_when_not_logged_in() -> None:
    with pytest.raises(MKUserError, match="logged in"):
        verify_requirements(_NO_PERMISSIONS, _PERMISSION, wato_enabled=True)


@pytest.mark.usefixtures("with_admin_login")
def test_allows_a_user_with_the_required_permission() -> None:
    verify_requirements(_NO_PERMISSIONS, _PERMISSION, wato_enabled=True)  # must not raise


@pytest.mark.usefixtures("request_context")
def test_denies_a_user_without_the_required_permission() -> None:
    with (
        UserContext(UserId("guest"), _NO_PERMISSIONS),
        pytest.raises(MKAuthException, match="not allowed"),
    ):
        verify_requirements(_NO_PERMISSIONS, _PERMISSION, wato_enabled=True)


@pytest.mark.usefixtures("with_admin_login")
def test_denies_access_when_wato_is_disabled() -> None:
    with pytest.raises(MKAuthException, match="Setup is disabled"):
        verify_requirements(_NO_PERMISSIONS, _PERMISSION, wato_enabled=False)


@pytest.mark.usefixtures("request_context")
def test_allows_a_user_without_permission_when_a_password_change_is_needed() -> None:
    with UserContext(UserId("guest"), _NO_PERMISSIONS):
        session.session_info.session_state = "password_change_needed"
        verify_requirements(_NO_PERMISSIONS, _PERMISSION, wato_enabled=True)  # must not raise


@pytest.mark.usefixtures("request_context")
def test_allows_a_user_without_permission_when_second_factor_setup_is_needed() -> None:
    with UserContext(UserId("guest"), _NO_PERMISSIONS):
        session.session_info.session_state = "second_factor_setup_needed"
        verify_requirements(_NO_PERMISSIONS, _PERMISSION, wato_enabled=True)  # must not raise
