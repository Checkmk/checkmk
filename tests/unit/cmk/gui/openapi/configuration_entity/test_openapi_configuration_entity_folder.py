#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import os
import shutil
from typing import Iterator

import pytest

from tests.testlib.unit.rest_api_client import ClientRegistry

from tests.unit.cmk.web_test_app import SetConfig

from cmk.gui.watolib.hosts_and_folders import folder_tree

from cmk.shared_typing.configuration_entity import ConfigEntityType

SUB_FOLDER = "sub-folder"
SUB_FOLDER_TITLE = "Sub Folder"


@pytest.fixture(autouse=True)
def create_folder_test_environment(with_admin_login: None, load_config: None) -> Iterator[None]:
    tree = folder_tree()
    tree.invalidate_caches()

    tree.root_folder().create_subfolder(name=SUB_FOLDER, title=SUB_FOLDER_TITLE, attributes={})

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
    assert titles == {"Main", SUB_FOLDER_TITLE}


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
        assert titles == {"Main", SUB_FOLDER_TITLE}
