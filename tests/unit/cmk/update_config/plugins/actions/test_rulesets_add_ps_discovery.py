#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging

import pytest

from cmk.gui.watolib.hosts_and_folders import folder_tree
from cmk.gui.watolib.rulesets import Rule, Ruleset, RulesetCollection
from cmk.gui.watolib.sample_config import PS_DISCOVERY_RULES

from cmk.update_config.plugins.actions.rulesets_add_ps_discovery import (
    add_ps_discovery_rules,
    PS_DISCOVERY_RULE_NAME,
)


def _make_ruleset_collection_with_preexisting_rule(id_: str) -> RulesetCollection:
    # add some rule, but not quite one of ours:
    ruleset = Ruleset(PS_DISCOVERY_RULE_NAME, {})
    folder = folder_tree().root_folder()
    rule = Rule.from_ruleset_defaults(folder, ruleset)
    rule.id = id_
    ruleset.append_rule(folder, rule)
    return RulesetCollection({ruleset.name: ruleset})


@pytest.mark.usefixtures("request_context")
def test_update_without_preexisting_rulesets() -> None:
    rulesets = _make_ruleset_collection_with_preexisting_rule(
        "some other id, not one of the shipped rules"
    )
    assert rulesets.get_rulesets()[PS_DISCOVERY_RULE_NAME].num_rules() == 1

    add_ps_discovery_rules(logging.getLogger(), rulesets)
    assert (
        rulesets.get_rulesets()[PS_DISCOVERY_RULE_NAME].num_rules() == len(PS_DISCOVERY_RULES) + 1
    )


@pytest.mark.usefixtures("request_context")
def test_update_with_preexisting_rulesets() -> None:
    rulesets = _make_ruleset_collection_with_preexisting_rule(PS_DISCOVERY_RULES[0]["id"])
    assert rulesets.get_rulesets()[PS_DISCOVERY_RULE_NAME].num_rules() == 1

    add_ps_discovery_rules(logging.getLogger(), rulesets)
    assert rulesets.get_rulesets()[PS_DISCOVERY_RULE_NAME].num_rules() == 1
