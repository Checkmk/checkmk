#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import os
import shutil
from collections.abc import Iterator

import pytest

from cmk.gui.form_specs.vue.visitors._registry import get_visitor
from cmk.gui.form_specs.vue.visitors._type_defs import DataOrigin, VisitorOptions
from cmk.gui.watolib.configuration_entity._folder import (
    get_folder_slidein_schema,
    save_folder_from_slidein_schema,
)
from cmk.gui.watolib.hosts_and_folders import folder_tree

MAIN_FOLDER = ""
SUB_FOLDER = "sub-folder"
SUB_FOLDER_TITLE = "Sub Folder"


@pytest.fixture(autouse=True)
def create_folder_test_environment(with_admin_login: None, load_config: None) -> Iterator[None]:
    tree = folder_tree()
    tree.invalidate_caches()

    tree.root_folder().create_subfolder(
        name=SUB_FOLDER, title=SUB_FOLDER_TITLE, attributes={}, pprint_value=False
    )

    yield

    shutil.rmtree(tree.root_folder().filesystem_path(), ignore_errors=True)
    os.makedirs(tree.root_folder().filesystem_path())


def test_folder_save_returns_full_title(create_folder_test_environment: None) -> None:
    # GIVEN
    visitor = get_visitor(get_folder_slidein_schema(), VisitorOptions(DataOrigin.DISK))
    _, data = visitor.to_vue({"general": {"title": "foo", "parent_folder": SUB_FOLDER}})

    # WHEN
    description = save_folder_from_slidein_schema(data, pprint_value=False)

    # THEN
    assert description.title == f"{SUB_FOLDER_TITLE}/foo"


@pytest.mark.parametrize(
    "parent_folder",
    [MAIN_FOLDER, SUB_FOLDER],
)
def test_folder_save_roundtrip(create_folder_test_environment: None, parent_folder: str) -> None:
    # GIVEN
    visitor = get_visitor(get_folder_slidein_schema(), VisitorOptions(DataOrigin.DISK))
    _, data = visitor.to_vue({"general": {"title": "foo", "parent_folder": parent_folder}})

    # WHEN
    save_folder_from_slidein_schema(data, pprint_value=False)

    # THEN
    parent = folder_tree().all_folders()[parent_folder]
    assert parent.subfolder_by_title("foo")
