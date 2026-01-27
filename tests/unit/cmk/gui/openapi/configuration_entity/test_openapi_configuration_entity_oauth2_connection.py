#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import uuid
from collections.abc import Iterable

import pytest

from cmk.gui.form_specs.visitors._utils import option_id
from cmk.gui.oauth2_connections.watolib.store import save_oauth2_connection
from cmk.gui.watolib import password_store
from cmk.shared_typing.configuration_entity import ConfigEntityType
from cmk.utils.oauth2_connection import OAuth2Connection
from tests.testlib.unit.rest_api_client import ClientRegistry

MY_OAUTH2_CONNECTION_UUID = str(uuid.uuid4())
MY_CLIENT_ID = str(uuid.uuid4())
MY_TENANT_ID = str(uuid.uuid4())

OAUTH2_CONNECTION_CONTENT = {
    MY_OAUTH2_CONNECTION_UUID: OAuth2Connection(
        title="My OAuth2 connection",
        client_secret=("cmk_postprocessed", "stored_password", ("my_client_secret", "")),
        access_token=("cmk_postprocessed", "stored_password", ("my_access_token", "")),
        refresh_token=("cmk_postprocessed", "stored_password", ("my_refresh_token", "")),
        client_id=MY_CLIENT_ID,
        tenant_id=MY_TENANT_ID,
        authority="global",
        connector_type="microsoft_entra_id",
    ),
}


@pytest.fixture
def mock_update_passwords_merged_file(monkeypatch: pytest.MonkeyPatch) -> Iterable[None]:
    monkeypatch.setattr(
        password_store,
        password_store.update_passwords_merged_file.__name__,
        lambda: None,
    )
    yield


def test_list_oauth2_connections_without_permissions(clients: ClientRegistry) -> None:
    # GIVEN
    clients.User.create(
        username="guest_user1",
        fullname="guest_user1_alias",
        auth_option={"auth_type": "password", "password": "supersecretish"},
        roles=["guest"],
    )
    clients.ConfigurationEntity.set_credentials("guest_user1", "supersecretish")

    # WHEN
    resp = clients.ConfigurationEntity.list_configuration_entities(
        entity_type=ConfigEntityType.oauth2_connection,
        entity_type_specifier="microsoft_entra_id",
        expect_ok=False,
    )

    # THEN
    assert resp.status_code == 401
    assert resp.json["title"] == "Unauthorized"


def test_list_oauth2_connections_as_admin(
    clients: ClientRegistry, with_admin: tuple[str, str]
) -> None:
    # GIVEN
    for ident, details in OAUTH2_CONNECTION_CONTENT.items():
        save_oauth2_connection(ident, details, user_id=None, pprint_value=False, use_git=False)
    clients.ConfigurationEntity.set_credentials(with_admin[0], with_admin[1])

    # WHEN
    resp = clients.ConfigurationEntity.list_configuration_entities(
        entity_type=ConfigEntityType.oauth2_connection,
        entity_type_specifier="microsoft_entra_id",
    )
    # THEN
    titles = {entry["title"] for entry in resp.json["value"]}
    assert titles == {"My OAuth2 connection"}


@pytest.mark.usefixtures("mock_update_passwords_merged_file")
def test_create_already_existing_oauth2_connection(
    clients: ClientRegistry, with_admin: tuple[str, str]
) -> None:
    # GIVEN
    for ident, details in OAUTH2_CONNECTION_CONTENT.items():
        save_oauth2_connection(ident, details, user_id=None, pprint_value=False, use_git=False)
    clients.ConfigurationEntity.set_credentials(with_admin[0], with_admin[1])

    # WHEN
    resp = clients.ConfigurationEntity.create_configuration_entity(
        {
            "entity_type": ConfigEntityType.oauth2_connection.value,
            "entity_type_specifier": "all",
            "data": {
                "ident": MY_OAUTH2_CONNECTION_UUID,
                "title": "My OAuth2 Connection",
                "client_secret": ("explicit_password", "", "my_client_secret", False),
                "access_token": ("explicit_password", "", "my_access_token", False),
                "refresh_token": ("explicit_password", "", "my_refresh_token", False),
                "client_id": MY_CLIENT_ID,
                "tenant_id": MY_TENANT_ID,
                "authority": option_id("global"),
            },
        },
        expect_ok=False,
    )

    # THEN
    assert resp.status_code == 400, resp.json
    assert "This ID is already in use." in resp.json["detail"], resp.json


@pytest.mark.usefixtures("mock_update_passwords_merged_file")
def test_create_non_existing_oauth2_connection(
    clients: ClientRegistry, with_admin: tuple[str, str]
) -> None:
    # GIVEN
    for ident, details in OAUTH2_CONNECTION_CONTENT.items():
        save_oauth2_connection(ident, details, user_id=None, pprint_value=False, use_git=False)
    clients.ConfigurationEntity.set_credentials(with_admin[0], with_admin[1])
    my_new_uuid = str(uuid.uuid4())

    # WHEN
    resp = clients.ConfigurationEntity.create_configuration_entity(
        {
            "entity_type": ConfigEntityType.oauth2_connection.value,
            "entity_type_specifier": "all",
            "data": {
                "ident": my_new_uuid,
                "title": "My non existing OAuth2 Connection",
                "client_secret": ("explicit_password", "", "my_client_secret", False),
                "access_token": ("explicit_password", "", "my_access_token", False),
                "refresh_token": ("explicit_password", "", "my_refresh_token", False),
                "client_id": MY_CLIENT_ID,
                "tenant_id": MY_TENANT_ID,
                "authority": option_id("global"),
            },
        },
        expect_ok=True,
    )

    # THEN
    assert resp.status_code == 200, resp.json
    assert resp.json["id"] == my_new_uuid, resp.json


@pytest.mark.usefixtures("mock_update_passwords_merged_file")
def test_create_non_existing_oauth2_connection_without_permissions(
    clients: ClientRegistry, with_admin: tuple[str, str]
) -> None:
    # GIVEN
    clients.User.create(
        username="guest_user1",
        fullname="guest_user1_alias",
        auth_option={"auth_type": "password", "password": "supersecretish"},
        roles=["guest"],
    )
    clients.ConfigurationEntity.set_credentials("guest_user1", "supersecretish")

    for ident, details in OAUTH2_CONNECTION_CONTENT.items():
        save_oauth2_connection(ident, details, user_id=None, pprint_value=False, use_git=False)

    my_new_uuid = str(uuid.uuid4())

    # WHEN
    resp = clients.ConfigurationEntity.create_configuration_entity(
        {
            "entity_type": ConfigEntityType.oauth2_connection.value,
            "entity_type_specifier": "all",
            "data": {
                "ident": my_new_uuid,
                "title": "My non existing OAuth2 Connection",
                "client_secret": ("explicit_password", "", "my_client_secret", False),
                "access_token": ("explicit_password", "", "my_access_token", False),
                "refresh_token": ("explicit_password", "", "my_refresh_token", False),
                "client_id": "my_client_id",
                "tenant_id": "my_tenant_id",
                "authority": option_id("global"),
            },
        },
        expect_ok=False,
    )

    # THEN
    assert resp.status_code == 401
    assert resp.json["title"] == "Unauthorized"
