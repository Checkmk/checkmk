#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging

import pytest

from cmk.gui.role_types import UserRoleBase
from cmk.update_config.plugins.actions.revoke_see_pending_changes import (
    is_update_from_before_the_permission,
    revoke_see_pending_changes,
)

_LOGGER = logging.getLogger(__name__)

_ACTIVATE = "wato.activate"
_SEE = "wato.see_pending_changes"


@pytest.mark.parametrize(
    "permissions, expected_permissions, expected_changed",
    [
        pytest.param({_ACTIVATE: False}, {_ACTIVATE: False, _SEE: False}, True, id="revoked"),
        pytest.param({}, {}, False, id="activate-by-default"),
        pytest.param({_ACTIVATE: True}, {_ACTIVATE: True}, False, id="activate-granted"),
        pytest.param(
            {_ACTIVATE: False, _SEE: True},
            {_ACTIVATE: False, _SEE: True},
            False,
            id="explicit-kept",
        ),
    ],
)
def test_see_pending_changes_is_revoked_only_where_activate_is_revoked(
    permissions: dict[str, bool],
    expected_permissions: dict[str, bool],
    expected_changed: bool,
) -> None:
    roles: dict[str, UserRoleBase] = {"role": {"alias": "Role", "permissions": permissions}}

    assert revoke_see_pending_changes(roles, _LOGGER) is expected_changed
    assert roles["role"]["permissions"] == expected_permissions


@pytest.mark.parametrize(
    "from_version",
    [
        pytest.param("2.4.0p30.pro", id="2.4.0"),
        pytest.param("2.5.0.ultimate", id="2.5.0"),
        pytest.param("2.5.0p19.ultimate", id="2.5.0 patch before the permission"),
    ],
)
def test_update_from_before_the_permission(from_version: str) -> None:
    assert is_update_from_before_the_permission(from_version, _LOGGER)


@pytest.mark.parametrize(
    "from_version",
    [
        pytest.param("2.5.0p20.ultimate", id="first 2.5.0 patch with the permission"),
        pytest.param("2.5.0p21.pro", id="later 2.5.0 patch"),
        pytest.param("3.0.0b1.ultimate", id="3.0.0"),
    ],
)
def test_update_from_a_version_with_the_permission(from_version: str) -> None:
    assert not is_update_from_before_the_permission(from_version, _LOGGER)


def test_new_site_is_no_update() -> None:
    assert not is_update_from_before_the_permission(None, _LOGGER)


def test_warns_on_unparseable_version(caplog: pytest.LogCaptureFixture) -> None:
    assert not is_update_from_before_the_permission("garbage.ultimate", _LOGGER)
    assert 'Cannot parse OMD_FROM_VERSION "garbage.ultimate"' in caplog.text
