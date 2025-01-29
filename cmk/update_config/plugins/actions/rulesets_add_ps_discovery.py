#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger

from cmk.gui.watolib.hosts_and_folders import folder_tree
from cmk.gui.watolib.rulesets import AllRulesets, Rule, Ruleset, RulesetCollection
from cmk.gui.watolib.sample_config import PS_DISCOVERY_RULES

from cmk.update_config.registry import update_action_registry, UpdateAction

PS_DISCOVERY_RULE_NAME = "inventory_processes_rules"


class UpdatePSDiscovery(UpdateAction):
    def __call__(self, logger: Logger) -> None:
        all_rulesets = AllRulesets.load_all_rulesets()
        add_ps_discovery_rules(logger, all_rulesets)
        all_rulesets.save()


def add_ps_discovery_rules(
    logger: Logger,
    all_rulesets: RulesetCollection,
) -> None:
    if (ps_discovery_rules := all_rulesets.get_rulesets().get(PS_DISCOVERY_RULE_NAME)) is None:
        return  # uh?

    if _some_shipped_rules_present(ps_discovery_rules):
        return

    root_folder = folder_tree().root_folder()
    for rule in reversed(PS_DISCOVERY_RULES):
        logger.info("Adding: %s", rule["options"]["description"])
        ps_discovery_rules.prepend_rule(
            root_folder, Rule.from_config(root_folder, ps_discovery_rules, rule)
        )


def _some_shipped_rules_present(current_rules: Ruleset) -> bool:
    for rule in PS_DISCOVERY_RULES:
        try:
            current_rules.get_rule_by_id(rule["id"])
            return True
        except KeyError:
            pass
    return False


update_action_registry.register(
    UpdatePSDiscovery(
        name="rulesets_add_ps_discovery",
        title="Process discovery for self monitoring",
        sort_index=40,  # after ruleset migration
    )
)
