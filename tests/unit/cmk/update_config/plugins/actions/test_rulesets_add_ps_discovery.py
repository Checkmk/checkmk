#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging

import pytest

from cmk.gui.valuespec import Dictionary
from cmk.gui.watolib.hosts_and_folders import folder_tree
from cmk.gui.watolib.rulesets import Rule, Ruleset
from cmk.gui.watolib.rulespec_groups import RulespecGroupMonitoringConfigurationVarious
from cmk.gui.watolib.rulespecs import HostRulespec
from cmk.gui.watolib.sample_config import INVENTORY_PROCESS_DISCOVERY_RULES
from cmk.update_config.plugins.actions.rulesets_add_ps_discovery import (
    _NEW_DEFAULT_RULE_IDS,
    add_ps_discovery_rules,
    EVENT_CONSOLE_RULE_ID,
    overwrite_default_ec_rule,
    PS_DISCOVERY_RULE_NAME,
    rule_present,
)

_PS_DISCOVERY_RULESPEC = HostRulespec(
    name=PS_DISCOVERY_RULE_NAME,
    group=RulespecGroupMonitoringConfigurationVarious,
    valuespec=lambda: Dictionary(elements=[], optional_keys=True),
)


def _make_ruleset_with_preexisting_rule(id_: str) -> Ruleset:
    # add some rule, but not quite one of ours:
    ruleset = Ruleset(PS_DISCOVERY_RULE_NAME, rulespec=_PS_DISCOVERY_RULESPEC)
    folder = folder_tree().root_folder()
    rule = Rule.from_ruleset(folder, ruleset, ruleset.rulespec.valuespec.default_value())
    rule.id = id_
    ruleset.append_rule(folder, rule)
    return ruleset


@pytest.mark.usefixtures("request_context")
def test_update_without_preexisting_rulesets() -> None:
    ruleset = _make_ruleset_with_preexisting_rule("some other id, not one of the shipped rules")
    assert ruleset.num_rules() == 1

    add_ps_discovery_rules(logging.getLogger(), ruleset)
    assert ruleset.num_rules() == len(INVENTORY_PROCESS_DISCOVERY_RULES) + 1


@pytest.mark.usefixtures("request_context")
def test_update_with_one_preexisting_adds_new_defaults() -> None:
    preexisting_id = INVENTORY_PROCESS_DISCOVERY_RULES[0]["id"]
    ruleset = _make_ruleset_with_preexisting_rule(preexisting_id)
    assert ruleset.num_rules() == 1

    add_ps_discovery_rules(logging.getLogger(), ruleset)

    new_ids = _NEW_DEFAULT_RULE_IDS - {preexisting_id}
    assert ruleset.num_rules() == 1 + len(new_ids)
    for rule_id in new_ids:
        assert rule_present(ruleset, rule_id)


def _event_console_default_match() -> str:
    rule = next(r for r in INVENTORY_PROCESS_DISCOVERY_RULES if r["id"] == EVENT_CONSOLE_RULE_ID)
    match = rule["value"]["match"]
    assert isinstance(match, str)
    return match


def _make_ruleset_with_event_console_match(match: str) -> Ruleset:
    ruleset = Ruleset(PS_DISCOVERY_RULE_NAME, rulespec=_PS_DISCOVERY_RULESPEC)
    folder = folder_tree().root_folder()
    rule = Rule.from_ruleset(folder, ruleset, ruleset.rulespec.valuespec.default_value())
    rule.id = EVENT_CONSOLE_RULE_ID
    rule.value = {"match": match}
    ruleset.append_rule(folder, rule)
    return ruleset


@pytest.mark.usefixtures("request_context")
def test_overwrite_migrates_untouched_event_console_rule() -> None:
    ruleset = _make_ruleset_with_event_console_match("~python3 /omd/sites/[^/]+/bin/mkeventd$")

    overwrite_default_ec_rule(logging.getLogger(), ruleset)

    rule = ruleset.get_rule_by_id(EVENT_CONSOLE_RULE_ID)
    assert rule.value["match"] == _event_console_default_match()


@pytest.mark.usefixtures("request_context")
def test_overwrite_keeps_customized_event_console_rule() -> None:
    customized = "~python3 /omd/sites/[^/]+/bin/mkeventd --my-custom-flag"
    ruleset = _make_ruleset_with_event_console_match(customized)

    overwrite_default_ec_rule(logging.getLogger(), ruleset)

    rule = ruleset.get_rule_by_id(EVENT_CONSOLE_RULE_ID)
    assert rule.value["match"] == customized


@pytest.mark.usefixtures("request_context")
def test_update_with_all_preexisting_adds_nothing() -> None:
    ruleset = Ruleset(PS_DISCOVERY_RULE_NAME, rulespec=_PS_DISCOVERY_RULESPEC)
    folder = folder_tree().root_folder()
    for shipped_rule in INVENTORY_PROCESS_DISCOVERY_RULES:
        rule = Rule.from_ruleset(folder, ruleset, ruleset.rulespec.valuespec.default_value())
        rule.id = shipped_rule["id"]
        ruleset.append_rule(folder, rule)
    assert ruleset.num_rules() == len(INVENTORY_PROCESS_DISCOVERY_RULES)

    add_ps_discovery_rules(logging.getLogger(), ruleset)

    assert ruleset.num_rules() == len(INVENTORY_PROCESS_DISCOVERY_RULES)
