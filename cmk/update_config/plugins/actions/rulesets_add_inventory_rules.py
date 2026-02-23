#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from typing import override

from cmk.gui.config import active_config
from cmk.gui.watolib.hosts_and_folders import folder_tree
from cmk.gui.watolib.rulesets import AllRulesets, Rule, Ruleset, RulesetCollection
from cmk.gui.watolib.sample_config import CMK_INV_RULES
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.registry import update_action_registry, UpdateAction

CMK_INV_RULESET_NAME = "active_checks:cmk_inv"


class UpdateInventoryRules(UpdateAction):
    @override
    def __call__(self, logger: Logger) -> None:
        all_rulesets = AllRulesets.load_all_rulesets()
        add_cmk_inv_rules(logger, all_rulesets)
        all_rulesets.save(pprint_value=active_config.wato_pprint_config, debug=active_config.debug)


def add_cmk_inv_rules(logger: Logger, all_rulesets: RulesetCollection) -> None:
    if (cmk_inv_rules := all_rulesets.get_rulesets().get(CMK_INV_RULESET_NAME)) is None:
        return

    root_folder = folder_tree().root_folder()
    for rule_config in reversed(CMK_INV_RULES):
        if _rule_present(cmk_inv_rules, rule_config["id"]):
            continue
        logger.info("Adding: %s", rule_config["options"]["description"])
        cmk_inv_rules.prepend_rule(
            root_folder, Rule.from_config(root_folder, cmk_inv_rules, rule_config)
        )


def _rule_present(current_rules: Ruleset, rule_id: str) -> bool:
    try:
        current_rules.get_rule_by_id(rule_id)
        return True
    except KeyError:
        pass
    return False


update_action_registry.register(
    UpdateInventoryRules(
        name="rulesets_add_inventory_rules",
        title="Inventory rules for shipped dashboards",
        sort_index=40,  # after ruleset migration
        expiry_version=ExpiryVersion.NEVER,
    )
)
