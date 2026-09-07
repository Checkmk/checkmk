#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# ruff: noqa: ARG001  # Unused fixtures are needed for setup side effects

from time import time

import pytest
from pytest_mock import MockerFixture

from cmk.ccc.user import UserId
from cmk.gui.ldap_integration.ldap_connector import (
    _reactivate_quarantined_user,
    LDAPUserConnector,
    SyncUsersResult,
)
from cmk.gui.type_defs import QuarantineInfo, Users, UserSpec
from tests.testlib.gui.web_test_app import SetConfig
from tests.unit.cmk.gui.ldap.test_ldap_golden import _test_config

_CONNECTION_ID = "test-golden-ldap-connector"


@pytest.fixture(name="connector")
def fixture_connector() -> LDAPUserConnector:
    return LDAPUserConnector(_test_config)


@pytest.fixture(name="sync_result")
def fixture_sync_result() -> SyncUsersResult:
    return SyncUsersResult(sync_start_time=time(), fetched_users={})


@pytest.fixture(autouse=True)
def _no_security_log(mocker: MockerFixture) -> None:
    mocker.patch("cmk.gui.ldap_integration.ldap_connector.log_security_event")
    mocker.patch(
        "cmk.gui.ldap_integration.ldap_connector.logged_in_user_id", lambda: UserId("admin")
    )


def _synced_user(*, locked: bool = False) -> UserSpec:
    return UserSpec(connector=_CONNECTION_ID, locked=locked, roles=["user"])


def test_vanished_user_is_quarantined(
    connector: LDAPUserConnector,
    sync_result: SyncUsersResult,
    request_context: None,
    set_config: SetConfig,
) -> None:
    users = Users({UserId("bob"): _synced_user()})

    with set_config(ldap_quarantine_period=30 * 86400):
        connector._quarantine_or_remove_users_no_longer_in_ldap(users, {}, sync_result)  # noqa: SLF001

    assert UserId("bob") in users, "quarantined user must not be deleted"
    assert users[UserId("bob")]["locked"] is True
    assert users[UserId("bob")]["ldap_quarantine"]["connection_id"] == _CONNECTION_ID
    assert any("Quarantined user bob" in change for change in sync_result.changes)


def test_already_quarantined_user_is_left_untouched(
    connector: LDAPUserConnector,
    sync_result: SyncUsersResult,
    request_context: None,
    set_config: SetConfig,
) -> None:
    user = _synced_user(locked=True)
    user["ldap_quarantine"] = QuarantineInfo(quarantined_on=123, connection_id=_CONNECTION_ID)
    users = Users({UserId("bob"): user})

    with set_config(ldap_quarantine_period=30 * 86400):
        connector._quarantine_or_remove_users_no_longer_in_ldap(users, {}, sync_result)  # noqa: SLF001

    assert users[UserId("bob")]["ldap_quarantine"]["quarantined_on"] == 123
    assert sync_result.changes == []


def test_vanished_user_is_deleted_when_quarantine_disabled(
    connector: LDAPUserConnector,
    sync_result: SyncUsersResult,
    request_context: None,
    set_config: SetConfig,
) -> None:
    users = Users({UserId("bob"): _synced_user()})

    with set_config(ldap_quarantine_period=None):
        connector._quarantine_or_remove_users_no_longer_in_ldap(users, {}, sync_result)  # noqa: SLF001

    assert UserId("bob") not in users, "immediate-deletion behavior must be preserved"
    assert any("Removed user bob" in change for change in sync_result.changes)


def test_present_user_is_not_quarantined(
    connector: LDAPUserConnector,
    sync_result: SyncUsersResult,
    request_context: None,
    set_config: SetConfig,
) -> None:
    users = Users({UserId("bob"): _synced_user()})

    with set_config(ldap_quarantine_period=30 * 86400):
        connector._quarantine_or_remove_users_no_longer_in_ldap(  # noqa: SLF001
            users,
            {"bob": None},  # type: ignore[dict-item]
            sync_result,
        )

    assert "ldap_quarantine" not in users[UserId("bob")]
    assert sync_result.changes == []


def test_reactivate_clears_quarantine_and_unlocks(
    connector: LDAPUserConnector, sync_result: SyncUsersResult
) -> None:
    user = _synced_user(locked=True)
    user["ldap_quarantine"] = QuarantineInfo(quarantined_on=123, connection_id=_CONNECTION_ID)

    reactivated = _reactivate_quarantined_user(UserId("bob"), user, connector, sync_result)

    assert reactivated is True
    assert "ldap_quarantine" not in user
    assert user["locked"] is False
    assert any("Reactivated quarantined user bob" in change for change in sync_result.changes)


def test_reactivate_does_not_unlock_manually_locked_user(
    connector: LDAPUserConnector, sync_result: SyncUsersResult
) -> None:
    user = _synced_user(locked=True)  # locked, but NOT quarantined by us

    reactivated = _reactivate_quarantined_user(UserId("bob"), user, connector, sync_result)

    assert reactivated is False
    assert user["locked"] is True, "a manual admin lock must never be lifted here"
    assert sync_result.changes == []
