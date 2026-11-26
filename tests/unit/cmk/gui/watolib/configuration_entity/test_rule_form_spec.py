#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import shutil
from collections.abc import Iterator, Mapping

import pytest

from cmk.gui.form_specs import (
    FormSpecValidationError,
    get_visitor,
    RawDiskData,
    RawFrontendData,
    VisitorOptions,
)
from cmk.gui.logged_in import LoggedInSuperUser
from cmk.gui.watolib.configuration_entity._rule_form_spec import (
    get_rule_form_spec_slidein_schema,
    save_rule_form_spec_from_slidein_schema,
)
from cmk.gui.watolib.hosts_and_folders import folder_tree, FolderTree
from cmk.gui.watolib.rulesets import FolderRulesets

RULESET_NAME = "only_hosts"


@pytest.fixture(name="tree")
def fixture_tree() -> Iterator[FolderTree]:
    tree = folder_tree()
    yield tree
    shutil.rmtree(tree.root_folder().filesystem_path(), ignore_errors=True)
    os.makedirs(tree.root_folder().filesystem_path())


@pytest.mark.parametrize(
    "rule_data",
    [
        pytest.param(
            {},
            id="no properties",
        ),
        pytest.param(
            {"properties": {}},
            id="no rule ID",
        ),
        pytest.param(
            {"properties": "x"},
            id="properties not a dictionary",
        ),
        pytest.param({"properties": {"id": 5}}, id="rule ID not a string"),
        pytest.param({"properties": {"id": ""}}, id="empty rule ID"),
    ],
)
@pytest.mark.usefixtures("with_admin_login")
def test_rule_data_without_a_rule_id_is_a_validation_error(
    tree: FolderTree, rule_data: Mapping[str, object]
) -> None:
    with pytest.raises(FormSpecValidationError) as excinfo:
        save_rule_form_spec_from_slidein_schema(
            RULESET_NAME,
            RawFrontendData(dict(rule_data)),
            tree,
            LoggedInSuperUser(),
        )

    assert [message.location for message in excinfo.value.messages] == [["properties", "id"]]


@pytest.mark.usefixtures("with_admin_login")
def test_valid_rule_data_saves_the_rule_with_its_rule_id(tree: FolderTree) -> None:
    visitor = get_visitor(
        get_rule_form_spec_slidein_schema(RULESET_NAME, tree, LoggedInSuperUser()),
        VisitorOptions(migrate_values=True, mask_values=False),
    )
    _, data = visitor.to_vue(
        RawDiskData(
            {
                "properties": {
                    "description": "",
                    "comment": "",
                    "docu_url": "",
                    "disabled": False,
                },
                "value": {"value": True},
                "conditions": {"type": ("explicit", {"folder_path": ""})},
            }
        )
    )
    assert isinstance(data, dict)
    rule_id = data["properties"]["id"]

    save_rule_form_spec_from_slidein_schema(
        RULESET_NAME,
        RawFrontendData(data),
        tree,
        LoggedInSuperUser(),
    )

    ruleset = FolderRulesets.load_folder_rulesets(tree.root_folder()).get(RULESET_NAME)
    assert ruleset.get_rule_by_id(rule_id).id == rule_id
