#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging

import pytest

from cmk.gui.watolib.hosts_and_folders import folder_tree
from cmk.gui.watolib.rulesets import Rule, Ruleset, RulesetCollection
from cmk.update_config.plugins.actions.rulesets_add_host_check_commands import (
    add_host_check_commands_rules,
    HOST_CHECK_COMMANDS_RULESET_NAME,
    PODMAN_HOST_CHECK_COMMAND_RULE_ID,
)


def _make_ruleset_collection(rule_ids: list[str]) -> RulesetCollection:
    ruleset = Ruleset(HOST_CHECK_COMMANDS_RULESET_NAME)
    folder = folder_tree().root_folder()
    for rule_id in rule_ids:
        rule = Rule.from_ruleset(folder, ruleset, ruleset.rulespec.valuespec.default_value())
        rule.id = rule_id
        ruleset.append_rule(folder, rule)
    return RulesetCollection({ruleset.name: ruleset})


@pytest.mark.usefixtures("request_context")
def test_ruleset_missing_does_nothing() -> None:
    rulesets = RulesetCollection({})

    add_host_check_commands_rules(logging.getLogger(), rulesets)

    assert HOST_CHECK_COMMANDS_RULESET_NAME not in rulesets.get_rulesets()


@pytest.mark.usefixtures("request_context")
def test_adds_podman_rule_when_missing() -> None:
    rulesets = _make_ruleset_collection([])

    add_host_check_commands_rules(logging.getLogger(), rulesets)

    ruleset = rulesets.get_rulesets()[HOST_CHECK_COMMANDS_RULESET_NAME]
    assert ruleset.num_rules() == 1
    ruleset.get_rule_by_id(PODMAN_HOST_CHECK_COMMAND_RULE_ID)


@pytest.mark.usefixtures("request_context")
def test_skips_when_rule_already_present() -> None:
    rulesets = _make_ruleset_collection([PODMAN_HOST_CHECK_COMMAND_RULE_ID])

    add_host_check_commands_rules(logging.getLogger(), rulesets)

    ruleset = rulesets.get_rulesets()[HOST_CHECK_COMMANDS_RULESET_NAME]
    assert ruleset.num_rules() == 1


@pytest.mark.usefixtures("request_context")
def test_idempotent() -> None:
    rulesets = _make_ruleset_collection([])

    add_host_check_commands_rules(logging.getLogger(), rulesets)
    count_after_first = rulesets.get_rulesets()[HOST_CHECK_COMMANDS_RULESET_NAME].num_rules()

    add_host_check_commands_rules(logging.getLogger(), rulesets)
    count_after_second = rulesets.get_rulesets()[HOST_CHECK_COMMANDS_RULESET_NAME].num_rules()

    assert count_after_first == count_after_second
