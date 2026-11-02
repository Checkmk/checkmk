#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime
from http import HTTPStatus
from typing import cast

import pytest
from pytest_mock import MockerFixture

import cmk.ccc.resulttype as result
from cmk.ccc.user import UserId
from cmk.gui import userdb
from cmk.gui.background_job.job import AlreadyRunningError
from cmk.gui.user_connection_config_types import LDAPUserConnectionConfig
from cmk.gui.userdb import get_user_attributes
from cmk.gui.userdb.user_sync_job import UserSyncBackgroundJob
from tests.testlib.unit.gui.web_test_app import SetConfig
from tests.testlib.unit.rest_api_client import ClientRegistry


@pytest.fixture(name="existing_user")
def fixture_existing_user(clients: ClientRegistry) -> str:
    username = "pw_test_user"
    clients.User.create(
        username=username,
        fullname="Password Test User",
        auth_option={"auth_type": "password", "password": "initial_password_123"},
        roles=["guest"],
    )
    return username


@pytest.mark.usefixtures("remote_site")
@pytest.mark.parametrize(
    "auth_option",
    [
        {"auth_type": "password", "password": "new_password_456"},
        {"auth_type": "automation", "secret": "AUTOMATION_SECRET_VALUE"},
        {"auth_type": "remove"},
    ],
)
def test_edit_user_credentials_blocked_on_remote_site(
    clients: ClientRegistry, existing_user: str, auth_option: dict[str, str]
) -> None:
    response = clients.User.edit(
        username=existing_user,
        auth_option=auth_option,
        expect_ok=False,
        customer=None,
    )
    response.assert_status_code(HTTPStatus.FORBIDDEN)
    assert response.json["title"] == "Not allowed on remote site"


def test_edit_user_password_allowed_on_central_site(
    clients: ClientRegistry, existing_user: str
) -> None:
    clients.User.edit(
        username=existing_user,
        auth_option={"auth_type": "password", "password": "new_password_456"},
        customer=None,
    )


@pytest.mark.usefixtures("remote_site")
def test_edit_user_non_credential_attribute_allowed_on_remote_site(
    clients: ClientRegistry, existing_user: str
) -> None:
    clients.User.edit(
        username=existing_user,
        fullname="Renamed User",
        customer=None,
    )


def test_trigger_user_sync(clients: ClientRegistry, mocker: MockerFixture) -> None:
    start_mock = mocker.patch.object(UserSyncBackgroundJob, "start", return_value=result.OK(None))

    resp = clients.User.trigger_user_sync()
    assert resp.status_code == HTTPStatus.SEE_OTHER
    assert "/objects/background_job/" in resp.headers["Location"]
    start_mock.assert_called_once()


def test_trigger_user_sync_already_running(clients: ClientRegistry, mocker: MockerFixture) -> None:
    mocker.patch.object(
        UserSyncBackgroundJob,
        "start",
        return_value=result.Error(AlreadyRunningError("Job already running")),
    )

    resp = clients.User.trigger_user_sync(expect_ok=False)
    assert resp.status_code == HTTPStatus.CONFLICT


_LDAP_CONNECTION = cast(
    LDAPUserConnectionConfig,
    {"type": "ldap", "id": "ldap_corp", "disabled": False, "active_plugins": {}},
)


@pytest.fixture(name="ldap_user")
def fixture_ldap_user(clients: ClientRegistry) -> str:
    """A user owned by the LDAP connection ``ldap_corp``."""
    username = "ldap_test_user"
    clients.User.create(
        username=username,
        fullname="Directory User",
        auth_option={"auth_type": "password", "password": "initial_password_123"},
        roles=["guest"],
    )
    users = userdb.load_users(lock=True)
    users[UserId(username)]["connector"] = "ldap_corp"
    userdb.save_users(
        users,
        get_user_attributes([]),
        [],
        now=datetime.now(),
        pprint_value=False,
        call_users_saved_hook=False,
        changed_users=[UserId(username)],
    )
    return username


@pytest.mark.usefixtures("request_context")
def test_connector_managed_user_can_be_disabled(
    clients: ClientRegistry, ldap_user: str, set_config: SetConfig
) -> None:
    """An administrator may disable the login of an LDAP user in Checkmk; the
    connectors then refuse to log the person in (CMK-40515)."""
    with set_config(user_connections=[_LDAP_CONNECTION]):
        response = clients.User.edit(username=ldap_user, disable_login=True, customer=None)

    assert response.json["extensions"]["disable_login"] is True
