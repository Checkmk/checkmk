#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import os
import shutil
from collections.abc import Iterator

import pytest

from tests.testlib.unit.rest_api_client import ClientRegistry

from cmk.gui.watolib.hosts_and_folders import folder_tree

from cmk.shared_typing.configuration_entity import ConfigEntityType

SUB_FOLDER = "sub-folder"
SUB_FOLDER_TITLE = "Sub Folder"


@pytest.fixture(autouse=True)
def create_folder_test_environment(with_admin_login: None, load_config: None) -> Iterator[None]:
    tree = folder_tree()
    tree.invalidate_caches()

    tree.root_folder().create_subfolder(
        name=SUB_FOLDER,
        title=SUB_FOLDER_TITLE,
        attributes={},
        pprint_value=False,
    )

    yield

    shutil.rmtree(tree.root_folder().filesystem_path(), ignore_errors=True)
    os.makedirs(tree.root_folder().filesystem_path())


def test_list_configuration_entities(clients: ClientRegistry) -> None:
    # WHEN
    resp = clients.ConfigurationEntity.list_configuration_entities(
        entity_type=ConfigEntityType.folder,
        entity_type_specifier="xyz",
    )

    # THEN
    assert len(resp.json["value"]) == 2
    assert resp.json["value"][0]["id"] == ""
    assert resp.json["value"][0]["title"] == "Main"
    assert resp.json["value"][1]["id"] == SUB_FOLDER
    assert resp.json["value"][1]["title"] == SUB_FOLDER_TITLE
