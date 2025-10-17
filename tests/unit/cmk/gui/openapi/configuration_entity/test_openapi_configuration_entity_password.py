#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Iterator

import pytest

from cmk.gui.form_specs.visitors._utils import option_id
from cmk.gui.watolib import password_store
from cmk.shared_typing.configuration_entity import ConfigEntityType
from cmk.utils.password_store import lookup, Password, password_store_path
from tests.testlib.unit.rest_api_client import ClientRegistry


@pytest.fixture
def mock_update_passwords_merged_file(monkeypatch: pytest.MonkeyPatch) -> Iterable[None]:
    monkeypatch.setattr(
        password_store,
        password_store.update_passwords_merged_file.__name__,
        lambda: None,
    )
    yield


@pytest.fixture(autouse=True)
def create_password_test_environment(
    with_admin_login: None, load_config: None, clients: ClientRegistry
) -> Iterator[None]:
    clients.ContactGroup.create(
        name="protected",
        alias="protected_alias",
    )
    yield


@pytest.mark.usefixtures("mock_update_passwords_merged_file")
def test_list_passwords_without_permissions(clients: ClientRegistry) -> None:
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
        entity_type=ConfigEntityType.password, entity_type_specifier="all", expect_ok=False
    )

    # THEN
    assert resp.status_code == 401
    assert resp.json["title"] == "Unauthorized"


@pytest.mark.usefixtures("mock_update_passwords_merged_file")
def test_list_passwords_with_permissions(clients: ClientRegistry) -> None:
    # GIVEN
    password_store_content = {
        "protected_password_id": Password(
            title="Protected title",
            comment="Protected comment",
            docu_url="Protected docu url",
            password="PasswordCanBeSeen",
            owned_by=None,
            shared_with=["protected"],
        ),
        "admin_password_id": Password(
            title="Admin title",
            comment="Admin comment",
            docu_url="Admin docu url",
            password="PasswordNotToBeSeen",
            owned_by=None,
            shared_with=[],
        ),
    }
    password_store.PasswordStore().save(password_store_content, pprint_value=False)
    clients.User.create(
        username="normal_user",
        fullname="normal_user_alias",
        contactgroups=["protected"],
        auth_option={"auth_type": "password", "password": "supersecretish"},
        roles=["user"],
    )
    clients.ConfigurationEntity.set_credentials("normal_user", "supersecretish")

    # WHEN
    resp = clients.ConfigurationEntity.list_configuration_entities(
        entity_type=ConfigEntityType.password, entity_type_specifier="all", expect_ok=False
    )

    # THEN
    assert resp.status_code == 200
    titles = set(entry["title"] for entry in resp.json["value"])
    assert titles == {"Protected title"}


@pytest.mark.usefixtures("mock_update_passwords_merged_file")
def test_list_passwords_as_admin(clients: ClientRegistry, with_admin: tuple[str, str]) -> None:
    # GIVEN
    password_store_content = {
        "admin_password_id": Password(
            title="Admin title",
            comment="Admin comment",
            docu_url="Admin docu url",
            password="PasswordCanToBeSeen",
            owned_by=None,
            shared_with=[],
        ),
    }
    password_store.PasswordStore().save(password_store_content, pprint_value=False)
    clients.ConfigurationEntity.set_credentials(with_admin[0], with_admin[1])

    # WHEN
    resp = clients.ConfigurationEntity.list_configuration_entities(
        entity_type=ConfigEntityType.password,
        entity_type_specifier="all",
    )
    # THEN
    titles = set(entry["title"] for entry in resp.json["value"])
    assert titles == {"Admin title"}


@pytest.mark.usefixtures("mock_update_passwords_merged_file")
def test_create_password_without_permissions(clients: ClientRegistry) -> None:
    # GIVEN
    clients.User.create(
        username="guest_user1",
        fullname="guest_user1_alias",
        auth_option={"auth_type": "password", "password": "supersecretish"},
        roles=["guest"],
    )
    clients.ConfigurationEntity.set_credentials("guest_user1", "supersecretish")

    # WHEN
    resp = clients.ConfigurationEntity.create_configuration_entity(
        {
            "entity_type": ConfigEntityType.password.value,
            "entity_type_specifier": "xyz",
            "data": {
                "general_props": {
                    "id": "test_password_id",
                    "title": "My protected test password",
                    "comment": "Created by a unit test",
                    "docu_url": "",
                },
                "password_props": {
                    "password": ["my-very-secret-protected-password", False],
                    "owned_by": ("contact_group", option_id("protected")),
                    "share_with": [{"name": "protected", "title": "My protected contact group"}],
                },
            },
        },
        expect_ok=False,
    )
    # THEN
    assert resp.status_code == 401
    assert "We are sorry, but you lack the permission for this operation" in resp.json["detail"]
    with pytest.raises(ValueError):
        lookup(password_store_path(), "test_protected_password_id")


@pytest.mark.usefixtures("mock_update_passwords_merged_file")
def test_create_password_with_permissions(clients: ClientRegistry) -> None:
    # GIVEN
    clients.User.create(
        username="normal_user",
        fullname="normal_user_alias",
        contactgroups=["protected"],
        auth_option={"auth_type": "password", "password": "supersecretish"},
        roles=["user"],
    )
    clients.ConfigurationEntity.set_credentials("normal_user", "supersecretish")

    # WHEN
    resp = clients.ConfigurationEntity.create_configuration_entity(
        {
            "entity_type": ConfigEntityType.password.value,
            "entity_type_specifier": "xyz",
            "data": {
                "general_props": {
                    "id": "test_protected_password_id",
                    "title": "My protected test password",
                    "comment": "Created by a unit test",
                    "docu_url": "",
                },
                "password_props": {
                    "password": ["my-very-secret-protected-password", False],
                    "owned_by": ("contact_group", option_id("protected")),
                    "share_with": [{"name": "protected", "title": "My protected contact group"}],
                },
            },
        }
    )

    # THEN
    assert resp.status_code == 200, resp.json
    assert resp.json["title"] == "My protected test password"
    assert (
        lookup(password_store_path(), "test_protected_password_id")
        == "my-very-secret-protected-password"
    )


@pytest.mark.usefixtures("mock_update_passwords_merged_file")
def test_create_password_as_admin(clients: ClientRegistry, with_admin: tuple[str, str]) -> None:
    # GIVEN
    clients.ConfigurationEntity.set_credentials(with_admin[0], with_admin[1])

    # WHEN
    resp = clients.ConfigurationEntity.create_configuration_entity(
        {
            "entity_type": ConfigEntityType.password.value,
            "entity_type_specifier": "xyz",
            "data": {
                "general_props": {
                    "id": "test_admin_password_id",
                    "title": "My admin test password",
                    "comment": "Created by a unit test",
                    "docu_url": "",
                },
                "password_props": {
                    "password": ["my-very-secret-admin-password", False],
                    "owned_by": ("admins", None),
                    "share_with": [],
                },
            },
        }
    )

    # THEN
    assert resp.status_code == 200, resp.json
    assert resp.json["title"] == "My admin test password"
    assert (
        lookup(password_store_path(), "test_admin_password_id") == "my-very-secret-admin-password"
    )
