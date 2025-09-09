#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import os
import shutil
from collections.abc import Iterator

import pytest

from cmk.gui.watolib.hosts_and_folders import folder_tree
from cmk.shared_typing.configuration_entity import ConfigEntityType
from tests.testlib.unit.rest_api_client import ClientRegistry
from tests.unit.cmk.web_test_app import SetConfig

SUB_FOLDER = "sub-folder"
SUB_FOLDER_TITLE = "Sub Folder"
PROTECTED_FOLDER = "protected-folder"
PROTECTED_FOLDER_TITLE = "Protected Folder"


@pytest.fixture(autouse=True)
def create_folder_test_environment(
    with_admin_login: None, load_config: None, clients: ClientRegistry
) -> Iterator[None]:
    tree = folder_tree()
    tree.invalidate_caches()

    tree.root_folder().create_subfolder(
        name=SUB_FOLDER,
        title=SUB_FOLDER_TITLE,
        attributes={},
        pprint_value=False,
        use_git=False,
    )

    clients.ContactGroup.create(
        name="protected",
        alias="protected_alias",
    )

    tree.root_folder().create_subfolder(
        name=PROTECTED_FOLDER,
        title=PROTECTED_FOLDER_TITLE,
        attributes={
            "contactgroups": {
                "groups": ["protected"],
                "use": True,
                "use_for_services": True,
                "recurse_use": True,
                "recurse_perms": False,
            }
        },
        pprint_value=False,
        use_git=False,
    )

    yield

    shutil.rmtree(tree.root_folder().filesystem_path(), ignore_errors=True)
    os.makedirs(tree.root_folder().filesystem_path())


def test_list_folders(clients: ClientRegistry) -> None:
    # WHEN
    resp = clients.ConfigurationEntity.list_configuration_entities(
        entity_type=ConfigEntityType.folder,
        entity_type_specifier="xyz",
    )

    # THEN
    titles = set(entry["title"] for entry in resp.json["value"])
    assert titles == {"Main", SUB_FOLDER_TITLE, PROTECTED_FOLDER_TITLE}


def test_list_folders_without_perm(clients: ClientRegistry, set_config: SetConfig) -> None:
    # GIVEN
    with set_config(wato_hide_folders_without_read_permissions=True):
        clients.User.create(
            username="guest_user1",
            fullname="guest_user1_alias",
            auth_option={"auth_type": "password", "password": "supersecretish"},
            roles=["guest"],
        )
        clients.ConfigurationEntity.set_credentials("guest_user1", "supersecretish")

        # WHEN
        resp = clients.ConfigurationEntity.list_configuration_entities(
            entity_type=ConfigEntityType.folder,
            entity_type_specifier="xyz",
        )

        # THEN
        titles = set(entry["title"] for entry in resp.json["value"])
        assert titles == {"Main"}


def test_list_folders_as_admin(
    clients: ClientRegistry, set_config: SetConfig, with_admin: tuple[str, str]
) -> None:
    # GIVEN
    with set_config(wato_hide_folders_without_read_permissions=True):
        clients.ConfigurationEntity.set_credentials(with_admin[0], with_admin[1])

        # WHEN
        resp = clients.ConfigurationEntity.list_configuration_entities(
            entity_type=ConfigEntityType.folder,
            entity_type_specifier="xyz",
        )

        # THEN
        titles = set(entry["title"] for entry in resp.json["value"])
        assert titles == {"Main", SUB_FOLDER_TITLE, PROTECTED_FOLDER_TITLE}


def test_create_folder(clients: ClientRegistry) -> None:
    # GIVEN
    schema_resp = clients.ConfigurationEntity.get_configuration_entity_schema(
        entity_type=ConfigEntityType.folder,
        entity_type_specifier="xyz",
    )

    schema_elements = schema_resp.json["extensions"]["schema"]["elements"][0]["elements"]
    choices = next(element for element in schema_elements if element["name"] == "parent_folder")[
        "parameter_form"
    ]["elements"]
    main_folder_choice = next(choice for choice in choices if choice["title"] == "Main")["name"]

    # WHEN
    resp = clients.ConfigurationEntity.create_configuration_entity(
        {
            "entity_type": ConfigEntityType.folder.value,
            "entity_type_specifier": "xyz",
            "data": {
                "general": {
                    "title": "New Folder",
                    "parent_folder": main_folder_choice,
                },
            },
        }
    )

    # THEN
    assert resp.status_code == 200, resp.json
    assert resp.json["title"] == "New Folder"
    folder_tree().invalidate_caches()
    assert folder_tree().all_folders()["new_folder"].title() == "New Folder"


def test_create_folder_without_permissions(clients: ClientRegistry) -> None:
    # GIVEN
    schema_resp = clients.ConfigurationEntity.get_configuration_entity_schema(
        entity_type=ConfigEntityType.folder,
        entity_type_specifier="xyz",
    )

    schema_elements = schema_resp.json["extensions"]["schema"]["elements"][0]["elements"]
    choices = next(element for element in schema_elements if element["name"] == "parent_folder")[
        "parameter_form"
    ]["elements"]
    main_folder_choice = next(choice for choice in choices if choice["title"] == "Main")["name"]

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
            "entity_type": ConfigEntityType.folder.value,
            "entity_type_specifier": "xyz",
            "data": {
                "general": {
                    "title": "New Folder",
                    "parent_folder": main_folder_choice,
                },
            },
        },
        expect_ok=False,
    )

    # THEN
    assert "do not have write permission" in resp.json["ext"]["validation_errors"][0]["message"]


def test_create_folder_with_permissions(clients: ClientRegistry) -> None:
    # GIVEN
    schema_resp = clients.ConfigurationEntity.get_configuration_entity_schema(
        entity_type=ConfigEntityType.folder,
        entity_type_specifier="xyz",
    )

    schema_elements = schema_resp.json["extensions"]["schema"]["elements"][0]["elements"]
    choices = next(element for element in schema_elements if element["name"] == "parent_folder")[
        "parameter_form"
    ]["elements"]
    protected_folder_choice = next(
        choice for choice in choices if choice["title"] == PROTECTED_FOLDER_TITLE
    )["name"]

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
            "entity_type": ConfigEntityType.folder.value,
            "entity_type_specifier": "xyz",
            "data": {
                "general": {
                    "title": "New Folder",
                    "parent_folder": protected_folder_choice,
                },
            },
        },
    )

    # THEN
    assert resp.status_code == 200, resp.json
    assert resp.json["title"] == "Protected Folder/New Folder"
    folder_tree().invalidate_caches()
    assert folder_tree().all_folders()["protected-folder/new_folder"].title() == "New Folder"
