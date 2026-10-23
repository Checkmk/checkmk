#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from http import HTTPStatus

import pytest
from pytest_mock import MockerFixture

import cmk.ccc.resulttype as result
from cmk.gui.background_job.job import AlreadyRunningError
from cmk.gui.userdb.user_sync_job import UserSyncBackgroundJob
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
