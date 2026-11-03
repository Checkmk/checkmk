#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections.abc import Sequence

from cmk.ccc.site import omd_site
from cmk.gui.config import Config
from cmk.gui.site_config import all_activation_sites
from cmk.gui.valuespec import Dictionary
from cmk.gui.watolib.hosts_and_folders import FolderTree
from cmk.gui.watolib.pending_changes import NoopPendingChangesStore, PendingChanges
from cmk.gui.watolib.rulesets import Rule, Ruleset, RulesetCollection
from cmk.gui.watolib.rulespec_groups import RulespecGroupMonitoringConfigurationVarious
from cmk.gui.watolib.rulespecs import HostRulespec
from cmk.ruleset_matcher.definition import RuleGroup
from cmk.ruleset_matcher.matcher import RulesetName
from cmk.update_config.plugins.actions.drop_invalid_ssc_rules import drop_invalid_ssc_rules

LOGGER = logging.getLogger("test")


def _make_ruleset(tree: FolderTree, name: RulesetName, rule_values: Sequence[object]) -> Ruleset:
    ruleset = Ruleset(
        name,
        rulespec=HostRulespec(
            name=name,
            group=RulespecGroupMonitoringConfigurationVarious,
            valuespec=lambda: Dictionary(elements=[], optional_keys=True),
        ),
    )
    folder = tree.root_folder()
    for value in rule_values:
        rule = Rule.from_ruleset(folder, ruleset, ruleset.rulespec.valuespec.default_value())
        rule.value = value
        ruleset.append_rule(folder, rule)
    return ruleset


def _make_pending_changes(config: Config) -> PendingChanges:
    return PendingChanges(
        activation_sites=all_activation_sites(config.sites),
        local_site=omd_site(),
        acting_user=None,
        store=NoopPendingChangesStore(),
        hooks=(),
    )


def test_drops_invalid_ssc_rules(config: Config, tree: FolderTree) -> None:
    active_checks_name = RuleGroup.ActiveChecks("test_check")
    special_agents_name = RuleGroup.SpecialAgents("test_agent")
    all_rulesets = RulesetCollection(
        {
            active_checks_name: _make_ruleset(
                tree,
                active_checks_name,
                [{"valid": "value"}, ("old", "tuple"), {1: "non-string key"}],
            ),
            special_agents_name: _make_ruleset(tree, special_agents_name, ["just a string"]),
        }
    )

    assert drop_invalid_ssc_rules(all_rulesets, _make_pending_changes(config), LOGGER) == 3

    assert [rule.value for _f, _i, rule in all_rulesets.get(active_checks_name).get_rules()] == [
        {"valid": "value"}
    ]
    assert not all_rulesets.get(special_agents_name).get_rules()


def test_leaves_other_rulesets_alone(config: Config, tree: FolderTree) -> None:
    name = "some_other_ruleset"
    all_rulesets = RulesetCollection({name: _make_ruleset(tree, name, [("not", "a", "dict")])})

    assert drop_invalid_ssc_rules(all_rulesets, _make_pending_changes(config), LOGGER) == 0

    assert [rule.value for _f, _i, rule in all_rulesets.get(name).get_rules()] == [
        ("not", "a", "dict")
    ]


def test_nothing_to_drop(config: Config, tree: FolderTree) -> None:
    name = RuleGroup.ActiveChecks("test_check")
    all_rulesets = RulesetCollection({name: _make_ruleset(tree, name, [{"valid": "value"}])})

    assert drop_invalid_ssc_rules(all_rulesets, _make_pending_changes(config), LOGGER) == 0

    assert len(all_rulesets.get(name).get_rules()) == 1
