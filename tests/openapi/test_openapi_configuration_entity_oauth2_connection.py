#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import uuid
from collections.abc import Iterable

import pytest

from cmk.gui.form_specs.visitors._utils import option_id
from cmk.gui.oauth2_connections.watolib.store import save_oauth2_connection
from cmk.gui.userdb import UserRolesConfigFile
from cmk.gui.watolib import password_store
from cmk.gui.watolib.passwords import save_password
from cmk.gui.watolib.userroles import clone_role, get_all_roles, RoleID
from cmk.shared_typing.configuration_entity import ConfigEntityType
from cmk.utils.oauth2_connection import OAuth2Connection
from cmk.utils.password_store import PasswordConfig
from tests.testlib.rest_api_client import ClientRegistry

MY_OAUTH2_CONNECTION_UUID = str(uuid.uuid4())
MY_CLIENT_ID = str(uuid.uuid4())
MY_TENANT_ID = str(uuid.uuid4())

SECOND_OAUTH2_CONNECTION_UUID = str(uuid.uuid4())
SECOND_CLIENT_ID = str(uuid.uuid4())
SECOND_TENANT_ID = str(uuid.uuid4())

OAUTH2_CONNECTION_CONTENT = {
    MY_OAUTH2_CONNECTION_UUID: OAuth2Connection(
        title="My OAuth2 connection",
        client_secret=("cmk_postprocessed", "stored_password", ("my_client_secret", "")),
        access_token=("cmk_postprocessed", "stored_password", ("my_access_token", "")),
        refresh_token=("cmk_postprocessed", "stored_password", ("my_refresh_token", "")),
        client_id=MY_CLIENT_ID,
        tenant_id=MY_TENANT_ID,
        authority="global",
        sites=("all", None),
        connector_type="microsoft_entra_id",
    ),
}

TWO_OAUTH2_CONNECTIONS_CONTENT = {
    **OAUTH2_CONNECTION_CONTENT,
    SECOND_OAUTH2_CONNECTION_UUID: OAuth2Connection(
        title="Second OAuth2 connection",
        client_secret=("cmk_postprocessed", "stored_password", ("second_client_secret", "")),
        access_token=("cmk_postprocessed", "stored_password", ("second_access_token", "")),
        refresh_token=("cmk_postprocessed", "stored_password", ("second_refresh_token", "")),
        client_id=SECOND_CLIENT_ID,
        tenant_id=SECOND_TENANT_ID,
        authority="global",
        sites=("all", None),
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


@pytest.mark.usefixtures("mock_update_passwords_merged_file")
def test_list_oauth2_connections_as_admin(
    clients: ClientRegistry, with_admin: tuple[str, str]
) -> None:
    # GIVEN
    for ident, details in OAUTH2_CONNECTION_CONTENT.items():
        save_oauth2_connection(ident, details, user_id=None, pprint_value=False, use_git=False)
    _create_passwords_for_connection(OAUTH2_CONNECTION_CONTENT[MY_OAUTH2_CONNECTION_UUID])
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
            "entity_type_specifier": "microsoft_entra_id",
            "data": {
                "ident": MY_OAUTH2_CONNECTION_UUID,
                "title": "My OAuth2 Connection",
                "editable_by": ("administrators", None),
                "shared_with": [],
                "client_secret": ("explicit_password", "", "my_client_secret", False),
                "access_token": ("explicit_password", "", "my_access_token", False),
                "refresh_token": ("explicit_password", "", "my_refresh_token", False),
                "client_id": MY_CLIENT_ID,
                "tenant_id": MY_TENANT_ID,
                "authority": option_id("global"),
                "sites": ("all", None),
            },
        },
        expect_ok=False,
    )

    # THEN
    assert resp.status_code == 400, resp.json
    assert "This ID is already in use." in resp.json["detail"], resp.json


@pytest.mark.usefixtures("mock_update_passwords_merged_file")
def test_update_already_existing_oauth2_connection(
    clients: ClientRegistry, with_admin: tuple[str, str]
) -> None:
    # GIVEN
    for ident, details in OAUTH2_CONNECTION_CONTENT.items():
        save_oauth2_connection(ident, details, user_id=None, pprint_value=False, use_git=False)
    clients.ConfigurationEntity.set_credentials(with_admin[0], with_admin[1])

    # WHEN
    resp = clients.ConfigurationEntity.update_configuration_entity(
        {
            "entity_id": MY_OAUTH2_CONNECTION_UUID,
            "entity_type": ConfigEntityType.oauth2_connection.value,
            "entity_type_specifier": "microsoft_entra_id",
            "data": {
                "ident": MY_OAUTH2_CONNECTION_UUID,
                "title": "My OAuth2 Connection",
                "editable_by": ("administrators", None),
                "shared_with": [],
                "client_secret": ("explicit_password", "", "my_client_secret", False),
                "access_token": ("explicit_password", "", "my_access_token", False),
                "refresh_token": ("explicit_password", "", "my_refresh_token", False),
                "client_id": MY_CLIENT_ID,
                "tenant_id": MY_TENANT_ID,
                "authority": option_id("global"),
                "sites": ("all", None),
            },
        },
        expect_ok=False,
    )

    # THEN
    assert resp.status_code == 200, resp.json
    assert resp.json["id"] == MY_OAUTH2_CONNECTION_UUID, resp.json


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
            "entity_type_specifier": "microsoft_entra_id",
            "data": {
                "ident": my_new_uuid,
                "title": "My non existing OAuth2 Connection",
                "editable_by": ("administrators", None),
                "shared_with": [],
                "client_secret": ("explicit_password", "", "my_client_secret", False),
                "access_token": ("explicit_password", "", "my_access_token", False),
                "refresh_token": ("explicit_password", "", "my_refresh_token", False),
                "client_id": MY_CLIENT_ID,
                "tenant_id": MY_TENANT_ID,
                "authority": option_id("global"),
                "sites": ("all", None),
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
            "entity_type_specifier": "microsoft_entra_id",
            "data": {
                "ident": my_new_uuid,
                "title": "My non existing OAuth2 Connection",
                "editable_by": ("administrators", None),
                "shared_with": [],
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


@pytest.mark.usefixtures("mock_update_passwords_merged_file")
def test_create_oauth2_connection_with_duplicate_title(
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
            "entity_type_specifier": "microsoft_entra_id",
            "data": {
                "ident": my_new_uuid,
                "title": "My OAuth2 connection",
                "editable_by": ("administrators", None),
                "shared_with": [],
                "client_secret": ("explicit_password", "", "my_client_secret", False),
                "access_token": ("explicit_password", "", "my_access_token", False),
                "refresh_token": ("explicit_password", "", "my_refresh_token", False),
                "client_id": MY_CLIENT_ID,
                "tenant_id": MY_TENANT_ID,
                "authority": option_id("global"),
                "sites": ("all", None),
            },
        },
        expect_ok=False,
    )

    # THEN
    assert resp.status_code == 422, resp.json
    validation_errors = resp.json["ext"]["validation_errors"]
    assert len(validation_errors) == 1
    assert validation_errors[0]["location"] == ["title"]
    assert "The title must be unique" in validation_errors[0]["message"]


@pytest.mark.usefixtures("mock_update_passwords_merged_file")
def test_update_oauth2_connection_keeping_same_title(
    clients: ClientRegistry, with_admin: tuple[str, str]
) -> None:
    # GIVEN
    for ident, details in OAUTH2_CONNECTION_CONTENT.items():
        save_oauth2_connection(ident, details, user_id=None, pprint_value=False, use_git=False)
    clients.ConfigurationEntity.set_credentials(with_admin[0], with_admin[1])

    # WHEN
    resp = clients.ConfigurationEntity.update_configuration_entity(
        {
            "entity_id": MY_OAUTH2_CONNECTION_UUID,
            "entity_type": ConfigEntityType.oauth2_connection.value,
            "entity_type_specifier": "microsoft_entra_id",
            "data": {
                "ident": MY_OAUTH2_CONNECTION_UUID,
                "title": "My OAuth2 connection",
                "editable_by": ("administrators", None),
                "shared_with": [],
                "client_secret": ("explicit_password", "", "my_client_secret", False),
                "access_token": ("explicit_password", "", "my_access_token", False),
                "refresh_token": ("explicit_password", "", "my_refresh_token", False),
                "client_id": MY_CLIENT_ID,
                "tenant_id": MY_TENANT_ID,
                "authority": option_id("global"),
                "sites": ("all", None),
            },
        },
        expect_ok=True,
    )

    # THEN
    assert resp.status_code == 200, resp.json
    assert resp.json["id"] == MY_OAUTH2_CONNECTION_UUID, resp.json


@pytest.mark.usefixtures("mock_update_passwords_merged_file")
def test_create_oauth2_connection_without_tokens(
    clients: ClientRegistry, with_admin: tuple[str, str]
) -> None:
    # GIVEN
    clients.ConfigurationEntity.set_credentials(with_admin[0], with_admin[1])
    my_new_uuid = str(uuid.uuid4())

    # WHEN
    resp = clients.ConfigurationEntity.create_configuration_entity(
        {
            "entity_type": ConfigEntityType.oauth2_connection.value,
            "entity_type_specifier": "microsoft_entra_id",
            "data": {
                "ident": my_new_uuid,
                "title": "OAuth2 Connection without tokens",
                "editable_by": ("administrators", None),
                "shared_with": [],
                "client_secret": ("explicit_password", "", "my_client_secret", False),
                "access_token": ("explicit_password", "", "", False),
                "refresh_token": ("explicit_password", "", "", False),
                "client_id": MY_CLIENT_ID,
                "tenant_id": MY_TENANT_ID,
                "authority": option_id("global"),
            },
        },
        expect_ok=False,
    )

    # THEN
    assert resp.status_code == 422, resp.json
    validation_errors = resp.json["ext"]["validation_errors"]
    assert len(validation_errors) > 0


@pytest.mark.usefixtures("mock_update_passwords_merged_file")
def test_update_oauth2_connection_to_existing_title(
    clients: ClientRegistry, with_admin: tuple[str, str]
) -> None:
    # GIVEN
    for ident, details in TWO_OAUTH2_CONNECTIONS_CONTENT.items():
        save_oauth2_connection(ident, details, user_id=None, pprint_value=False, use_git=False)
    clients.ConfigurationEntity.set_credentials(with_admin[0], with_admin[1])

    # WHEN
    resp = clients.ConfigurationEntity.update_configuration_entity(
        {
            "entity_id": MY_OAUTH2_CONNECTION_UUID,
            "entity_type": ConfigEntityType.oauth2_connection.value,
            "entity_type_specifier": "microsoft_entra_id",
            "data": {
                "ident": MY_OAUTH2_CONNECTION_UUID,
                "title": "Second OAuth2 connection",
                "editable_by": ("administrators", None),
                "shared_with": [],
                "client_secret": ("explicit_password", "", "my_client_secret", False),
                "access_token": ("explicit_password", "", "my_access_token", False),
                "refresh_token": ("explicit_password", "", "my_refresh_token", False),
                "client_id": MY_CLIENT_ID,
                "tenant_id": MY_TENANT_ID,
                "authority": option_id("global"),
                "sites": ("all", None),
            },
        },
        expect_ok=False,
    )

    # THEN
    assert resp.status_code == 422, resp.json
    validation_errors = resp.json["ext"]["validation_errors"]
    assert len(validation_errors) == 1
    assert validation_errors[0]["location"] == ["title"]
    assert "The title must be unique" in validation_errors[0]["message"]


def _create_passwords_for_connection(
    connection: OAuth2Connection,
    *,
    owned_by: str | None = None,
    shared_with: list[str] | None = None,
) -> None:
    """Create password store entries for all password references in an OAuth2 connection."""
    for field in ("client_secret", "access_token", "refresh_token"):
        pw_id = connection[field][2][0]
        save_password(
            ident=pw_id,
            config=PasswordConfig(
                title=f"Test {pw_id}",
                comment="",
                docu_url="",
                password="secret",
                owned_by=owned_by,
                shared_with=shared_with or [],
            ),
            new_password=True,
            user_id=None,
            pprint_value=False,
            use_git=False,
        )


@pytest.mark.usefixtures("mock_update_passwords_merged_file")
def test_list_oauth2_connections_shows_all_as_admin(
    clients: ClientRegistry, with_admin: tuple[str, str]
) -> None:
    """List endpoint should only return connections whose passwords are accessible."""
    # GIVEN - two connections, but only the first has passwords in the store
    for ident, details in TWO_OAUTH2_CONNECTIONS_CONTENT.items():
        save_oauth2_connection(ident, details, user_id=None, pprint_value=False, use_git=False)
    _create_passwords_for_connection(OAUTH2_CONNECTION_CONTENT[MY_OAUTH2_CONNECTION_UUID])
    _create_passwords_for_connection(
        TWO_OAUTH2_CONNECTIONS_CONTENT[SECOND_OAUTH2_CONNECTION_UUID],
        owned_by="other_group",
    )
    clients.ConfigurationEntity.set_credentials(with_admin[0], with_admin[1])

    # WHEN
    resp = clients.ConfigurationEntity.list_configuration_entities(
        entity_type=ConfigEntityType.oauth2_connection,
        entity_type_specifier="microsoft_entra_id",
    )

    # THEN - only the connection with passwords should be listed
    titles = {entry["title"] for entry in resp.json["value"]}
    assert titles == {"My OAuth2 connection", "Second OAuth2 connection"}


@pytest.mark.usefixtures("mock_update_passwords_merged_file")
def test_show_oauth2_connection_not_usable(
    clients: ClientRegistry, with_admin: tuple[str, str]
) -> None:
    """Show endpoint should return 404 for a connection whose passwords are not accessible."""
    # GIVEN - connection exists but without passwords in the store
    for ident, details in OAUTH2_CONNECTION_CONTENT.items():
        save_oauth2_connection(ident, details, user_id=None, pprint_value=False, use_git=False)
    clients.ConfigurationEntity.set_credentials(with_admin[0], with_admin[1])

    # WHEN
    resp = clients.ConfigurationEntity.get_configuration_entity(
        entity_type=ConfigEntityType.oauth2_connection,
        entity_id=MY_OAUTH2_CONNECTION_UUID,
        expect_ok=False,
    )

    # THEN
    assert resp.status_code == 404
    assert resp.json["title"] == "Not found"


@pytest.mark.usefixtures("mock_update_passwords_merged_file")
def test_list_oauth2_connections_filtered_by_contact_group(
    clients: ClientRegistry,
) -> None:
    """A user should only see connections whose passwords are owned by their contact group."""
    # GIVEN - create a custom role based on admin but without wato.edit_all_passwords
    custom_role = clone_role(RoleID("admin"), pprint_value=False)
    custom_role.permissions["wato.edit_all_passwords"] = False
    all_roles = get_all_roles()
    all_roles[RoleID(custom_role.name)] = custom_role
    UserRolesConfigFile().save(
        {role.name: role.to_dict() for role in all_roles.values()}, pprint_value=False
    )

    # Create contact groups
    clients.ContactGroup.create("my_group", "My Group")
    clients.ContactGroup.create("other_group", "Other Group")

    # Create a user in "my_group" with the custom role
    clients.User.create(
        username="oauth2_user",
        fullname="OAuth2 User",
        auth_option={"auth_type": "password", "password": "supersecretish"},
        contactgroups=["my_group"],
        roles=[custom_role.name],
    )

    # Create both connections with passwords
    for ident, details in TWO_OAUTH2_CONNECTIONS_CONTENT.items():
        save_oauth2_connection(ident, details, user_id=None, pprint_value=False, use_git=False)
    _create_passwords_for_connection(
        OAUTH2_CONNECTION_CONTENT[MY_OAUTH2_CONNECTION_UUID],
        owned_by="my_group",
    )
    _create_passwords_for_connection(
        TWO_OAUTH2_CONNECTIONS_CONTENT[SECOND_OAUTH2_CONNECTION_UUID],
        owned_by="other_group",
    )

    clients.ConfigurationEntity.set_credentials("oauth2_user", "supersecretish")

    # WHEN
    resp = clients.ConfigurationEntity.list_configuration_entities(
        entity_type=ConfigEntityType.oauth2_connection,
        entity_type_specifier="microsoft_entra_id",
    )

    # THEN - only the connection owned by user's contact group should be listed
    titles = {entry["title"] for entry in resp.json["value"]}
    assert titles == {"My OAuth2 connection"}


@pytest.mark.usefixtures("mock_update_passwords_merged_file")
def test_list_oauth2_connections_editable_field_as_admin(
    clients: ClientRegistry, with_admin: tuple[str, str]
) -> None:
    """Admin should see all connections marked as editable."""
    # GIVEN - two connections with passwords owned by different groups
    for ident, details in TWO_OAUTH2_CONNECTIONS_CONTENT.items():
        save_oauth2_connection(ident, details, user_id=None, pprint_value=False, use_git=False)
    _create_passwords_for_connection(
        OAUTH2_CONNECTION_CONTENT[MY_OAUTH2_CONNECTION_UUID],
        owned_by="my_group",
    )
    _create_passwords_for_connection(
        TWO_OAUTH2_CONNECTIONS_CONTENT[SECOND_OAUTH2_CONNECTION_UUID],
        owned_by="other_group",
    )
    clients.ConfigurationEntity.set_credentials(with_admin[0], with_admin[1])

    # WHEN
    resp = clients.ConfigurationEntity.list_configuration_entities(
        entity_type=ConfigEntityType.oauth2_connection,
        entity_type_specifier="microsoft_entra_id",
    )

    # THEN - admin can edit all connections regardless of password ownership
    editable_by_id = {
        entry["id"]: not entry["extensions"]["ui_hide_edit_button"] for entry in resp.json["value"]
    }
    assert editable_by_id == {
        MY_OAUTH2_CONNECTION_UUID: True,
        SECOND_OAUTH2_CONNECTION_UUID: True,
    }


@pytest.mark.usefixtures("mock_update_passwords_merged_file")
def test_list_oauth2_connections_editable_field_for_non_admin(
    clients: ClientRegistry,
) -> None:
    """Connections with passwords owned by the user's group are editable;
    connections with passwords only shared with the user's group are not."""
    # GIVEN - create a custom role based on admin but without wato.edit_all_passwords
    custom_role = clone_role(RoleID("admin"), pprint_value=False)
    custom_role.permissions["wato.edit_all_passwords"] = False
    all_roles = get_all_roles()
    all_roles[RoleID(custom_role.name)] = custom_role
    UserRolesConfigFile().save(
        {role.name: role.to_dict() for role in all_roles.values()}, pprint_value=False
    )

    clients.ContactGroup.create("my_group", "My Group")
    clients.ContactGroup.create("other_group", "Other Group")
    clients.User.create(
        username="oauth2_user",
        fullname="OAuth2 User",
        auth_option={"auth_type": "password", "password": "supersecretish"},
        contactgroups=["my_group"],
        roles=[custom_role.name],
    )

    # Create both connections
    for ident, details in TWO_OAUTH2_CONNECTIONS_CONTENT.items():
        save_oauth2_connection(ident, details, user_id=None, pprint_value=False, use_git=False)
    # First connection: passwords owned by the user's group → editable
    _create_passwords_for_connection(
        OAUTH2_CONNECTION_CONTENT[MY_OAUTH2_CONNECTION_UUID],
        owned_by="my_group",
    )
    # Second connection: passwords owned by another group but shared with user's group → usable but not editable
    _create_passwords_for_connection(
        TWO_OAUTH2_CONNECTIONS_CONTENT[SECOND_OAUTH2_CONNECTION_UUID],
        owned_by="other_group",
        shared_with=["my_group"],
    )

    clients.ConfigurationEntity.set_credentials("oauth2_user", "supersecretish")

    # WHEN
    resp = clients.ConfigurationEntity.list_configuration_entities(
        entity_type=ConfigEntityType.oauth2_connection,
        entity_type_specifier="microsoft_entra_id",
    )

    # THEN - both connections are listed, but only the owned one is editable
    assert resp.status_code == 200
    editable_by_id = {
        entry["id"]: not entry["extensions"]["ui_hide_edit_button"] for entry in resp.json["value"]
    }
    assert editable_by_id == {
        MY_OAUTH2_CONNECTION_UUID: True,
        SECOND_OAUTH2_CONNECTION_UUID: False,
    }
