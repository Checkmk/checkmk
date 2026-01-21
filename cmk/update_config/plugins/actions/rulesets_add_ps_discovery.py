#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from typing import override

from cmk.gui.config import active_config
from cmk.gui.watolib.hosts_and_folders import folder_tree
from cmk.gui.watolib.rulesets import AllRulesets, Rule, Ruleset, RulesetCollection
from cmk.gui.watolib.sample_config import PS_DISCOVERY_RULES
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.registry import update_action_registry, UpdateAction

PS_DISCOVERY_RULE_NAME = "inventory_processes_rules"
RABBITMQ_RULE_ID = "65a3dca4-8d71-45d8-8887-53ef0c63d06f"
AUTOMATION_HELPER_RULE_ID = "94190e27-2836-488a-b6b4-f23f694a455e"


class UpdatePSDiscovery(UpdateAction):
    @override
    def __call__(self, logger: Logger) -> None:
        all_rulesets = AllRulesets.load_all_rulesets()
        add_ps_discovery_rules(logger, all_rulesets)
        overwrite_ps_discovery_rules(logger, all_rulesets)
        all_rulesets.save(pprint_value=active_config.wato_pprint_config, debug=active_config.debug)


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


def overwrite_ps_discovery_rule(
    logger: Logger, ps_discovery_rules: Ruleset, rule_id: str, old_rule_match: str, ps_descr: str
) -> None:
    try:
        rule = ps_discovery_rules.get_rule_by_id(rule_id)
    except KeyError:
        logger.debug("No default rule for %s.", ps_descr)
        return

    if rule.value["match"] == old_rule_match:
        try:
            default_rule = next(rule for rule in PS_DISCOVERY_RULES if rule["id"] == rule_id)
        except StopIteration:
            logger.debug("No actual rule for %s.", ps_descr)
            return
        rule.value["match"] = default_rule["value"]["match"]
        logger.info("Overwriting default value: %s", rule.rule_options.description)
    else:
        logger.debug("Rule for %s was changed. Nothing to do.", ps_descr)


def overwrite_ps_discovery_rules(logger: Logger, all_rulesets: RulesetCollection) -> None:
    if (ps_discovery_rules := all_rulesets.get_rulesets().get(PS_DISCOVERY_RULE_NAME)) is None:
        return

    rabbitmq_old_rule_match = "~(?:/omd/versions/.*/lib/erlang)|(?:.*bin/rabbitmq)"
    rabbitmq_ps_descr = "self-monitoring of RabbitMQ"
    overwrite_ps_discovery_rule(
        logger, ps_discovery_rules, RABBITMQ_RULE_ID, rabbitmq_old_rule_match, rabbitmq_ps_descr
    )

    automation_helper_old_rule_match = "~gunicorn:.*automation-helper"
    automation_helper_logging_id = "self-monitoring of automation helper"
    overwrite_ps_discovery_rule(
        logger,
        ps_discovery_rules,
        AUTOMATION_HELPER_RULE_ID,
        automation_helper_old_rule_match,
        automation_helper_logging_id,
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
        expiry_version=ExpiryVersion.NEVER,
    )
)
