#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Callable
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from cmk.gui.valuespec import Dictionary
from cmk.gui.wato.pages._password_store_valuespecs import (
    IndividualOrStoredPassword,
)
from cmk.gui.watolib.hosts_and_folders import Folder, folder_tree
from cmk.gui.watolib.rulesets import (
    AllRulesets,
    Rule,
    RuleConditions,
    RuleOptions,
    Ruleset,
)
from cmk.gui.watolib.rulespec_groups import RulespecGroupMonitoringConfigurationVarious
from cmk.gui.watolib.rulespecs import Rulespec


@pytest.fixture(name="allrulesets_with_rules_in_multiple_files")
def fixture_allrulesets_with_rules_in_multiple_files() -> AllRulesets:
    rule_name = "special_agents:foo_rule"

    ruleset = Ruleset(
        name=rule_name,
        tag_to_group_map={},
        rulespec=Rulespec(
            name="foo-rulespec",
            group=RulespecGroupMonitoringConfigurationVarious,
            title=lambda: "foo-rulespec",
            valuespec=lambda: Dictionary(
                elements=[("value", IndividualOrStoredPassword())], optional_keys=False
            ),
            match_type="dict",
            item_type=None,
            item_spec=None,
            item_name=None,
            item_help=None,
            is_optional=False,
            is_deprecated=False,
            deprecation_planned=False,
            is_cloud_and_managed_edition_only=False,
            is_for_services=False,
            is_binary_ruleset=False,
            factory_default={
                "value": (
                    "cmk_postprocessed",
                    "explicit_password",
                    ("uuid992d5025-f689-43de-b9c4-09db3a345976", "password"),
                )
            },
            help_func=None,
            doc_references=None,
        ),
    )
    tree = folder_tree()
    root_folder = tree.root_folder()
    sub_folder = Folder(
        tree=tree,  # type: ignore[abstract]
        name="Sub",
        folder_id="sub",
        folder_path="sub",
        parent_folder=root_folder,
        validators=root_folder.validators,
        title="Sub",
        attributes=root_folder.attributes,
        locked=False,
        locked_subfolders=False,
        num_hosts=0,
        hosts=None,
    )
    root_folder._subfolders["sub"] = sub_folder
    tree.all_folders = lambda: {"": root_folder, "sub": sub_folder}  # type: ignore[method-assign]
    ruleset.append_rule(
        folder=root_folder,
        rule=Rule(
            id_="id-1",
            folder=root_folder,
            ruleset=ruleset,
            conditions=RuleConditions(host_folder=root_folder.name()),
            options=RuleOptions(disabled=False, description="", comment="", docu_url=""),
            value={
                "value": (
                    "cmk_postprocessed",
                    "explicit_password",
                    ("uuid992d5025-f689-43de-b9c4-09db3a345977", "root password"),
                )
            },
        ),
    )
    ruleset.append_rule(
        folder=sub_folder,
        rule=Rule(
            id_="id-2",
            folder=sub_folder,
            ruleset=ruleset,
            conditions=RuleConditions(host_folder=sub_folder.name()),
            options=RuleOptions(disabled=False, description="", comment="", docu_url=""),
            value={
                "value": (
                    "cmk_postprocessed",
                    "explicit_password",
                    ("uuid992d5025-f689-43de-b9c4-09db3a345978", "sub password"),
                )
            },
        ),
    )
    return AllRulesets(rulesets={rule_name: ruleset})


@pytest.mark.parametrize(
    ["callback"],
    [
        pytest.param(None, id="Successful hook call"),
        pytest.param(lambda *args, **kwargs: 1 / 0, id="Exception in hook call"),
    ],
)
@pytest.mark.usefixtures("request_context")
@patch("cmk.gui.watolib.rulesets.update_merged_password_file")
def test_all_rulesets_save(
    updated_password_file_automation: MagicMock,
    allrulesets_with_rules_in_multiple_files: AllRulesets,
    callback: Callable[..., Any] | None,
) -> None:
    updated_password_file_automation.side_effect = callback

    if callback is not None:
        with pytest.raises(ZeroDivisionError):
            allrulesets_with_rules_in_multiple_files.save(pprint_value=False, debug=False)
    else:
        allrulesets_with_rules_in_multiple_files.save(pprint_value=False, debug=False)

    assert updated_password_file_automation.called
