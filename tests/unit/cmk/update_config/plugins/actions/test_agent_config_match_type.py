#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from unittest.mock import MagicMock

import pytest

from cmk.gui.watolib.hosts_and_folders import Folder, folder_tree
from cmk.gui.watolib.rulesets import (
    Rule,
    RuleConditions,
    RuleOptions,
    Ruleset,
    RulesetCollection,
)
from cmk.update_config.plugins.actions.agent_config_match_type import (
    _remove_match_type_from_agent_config_rules,
    MATCH_TYPE_KEY,
)


def _make_rule(folder: Folder, ruleset: Ruleset, value: object) -> Rule:
    return Rule(
        "test-rule-id",
        folder,
        ruleset,
        RuleConditions(folder.path()),
        RuleOptions(
            disabled=False,
            description="",
            comment="",
            docu_url="",
            predefined_condition_id=None,
        ),
        value,
    )


def _make_ruleset_with_rules(ruleset_name: str, values: list[object]) -> tuple[str, Ruleset]:
    rulespec = MagicMock()
    rulespec.name = ruleset_name
    ruleset = Ruleset(ruleset_name, rulespec=rulespec)
    folder = folder_tree().root_folder()
    for i, value in enumerate(values):
        rule = _make_rule(folder, ruleset, value)
        rule.id = f"test-rule-{i}"
        ruleset.append_rule(folder, rule)
    return ruleset_name, ruleset


@pytest.mark.usefixtures("request_context")
def test_removes_match_type_key_from_dict_values() -> None:
    name, ruleset = _make_ruleset_with_rules(
        "agent_config:my_plugin",
        [{"foo": "bar", MATCH_TYPE_KEY: "dict"}, {"baz": 1, MATCH_TYPE_KEY: "dict"}],
    )
    rulesets = RulesetCollection({name: ruleset})

    _remove_match_type_from_agent_config_rules(logging.getLogger(), rulesets)

    for _folder, _index, rule in ruleset.get_rules():
        assert MATCH_TYPE_KEY not in rule.value


@pytest.mark.usefixtures("request_context")
def test_ignores_non_agent_config_rulesets() -> None:
    name, ruleset = _make_ruleset_with_rules(
        "some_other_ruleset",
        [{"foo": "bar", MATCH_TYPE_KEY: "dict"}],
    )
    rulesets = RulesetCollection({name: ruleset})

    _remove_match_type_from_agent_config_rules(logging.getLogger(), rulesets)

    for _folder, _index, rule in ruleset.get_rules():
        assert MATCH_TYPE_KEY in rule.value


@pytest.mark.usefixtures("request_context")
def test_ignores_non_dict_values() -> None:
    name, ruleset = _make_ruleset_with_rules(
        "agent_config:simple_plugin",
        [True],
    )
    rulesets = RulesetCollection({name: ruleset})

    _remove_match_type_from_agent_config_rules(logging.getLogger(), rulesets)

    for _folder, _index, rule in ruleset.get_rules():
        assert rule.value is True


@pytest.mark.usefixtures("request_context")
def test_no_change_when_key_absent() -> None:
    name, ruleset = _make_ruleset_with_rules(
        "agent_config:clean_plugin",
        [{"foo": "bar"}],
    )
    rulesets = RulesetCollection({name: ruleset})

    _remove_match_type_from_agent_config_rules(logging.getLogger(), rulesets)

    for _folder, _index, rule in ruleset.get_rules():
        assert rule.value == {"foo": "bar"}
