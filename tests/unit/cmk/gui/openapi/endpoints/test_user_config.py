#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator

import pytest

import cmk.utils.paths
from tests.testlib.rest_api_client import ClientRegistry


@pytest.fixture(name="remote_site")
def fixture_remote_site() -> Iterator[None]:
    """Make the test believe it's running on a remote site."""
    cmk.utils.paths.check_mk_config_dir.mkdir(parents=True, exist_ok=True)
    distr_wato_mk = cmk.utils.paths.check_mk_config_dir / "distributed_wato.mk"
    previous = distr_wato_mk.read_bytes() if distr_wato_mk.exists() else None
    distr_wato_mk.write_text("is_distributed_setup_remote_site = True\n")
    try:
        yield
    finally:
        if previous is None:
            distr_wato_mk.unlink(missing_ok=True)
        else:
            distr_wato_mk.write_bytes(previous)


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
    response.assert_status_code(403)
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
