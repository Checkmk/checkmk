#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from typing import override

from cmk.gui.config import active_config
from cmk.gui.watolib.hosts_and_folders import Folder, folder_tree
from cmk.gui.watolib.rulesets import AllRulesets, Rule, Ruleset
from cmk.gui.watolib.sample_config import INVENTORY_PROCESS_DISCOVERY_RULES
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.utils.rulesets.definition import RuleGroup

PS_DISCOVERY_RULE_NAME = RuleGroup.DiscoveryParameters("inventory_processes_rules")
_NEW_DEFAULT_RULE_IDS = frozenset(
    [
        "9c90e72e-443e-4400-8374-cd4f9d9fdbf5",  # mcp-server
    ]
)
EVENT_CONSOLE_RULE_ID = "2105c8a7-5672-4242-98f6-fd6ce8b8f3a7"


class UpdatePSDiscovery(UpdateAction):
    @override
    def __call__(self, logger: Logger) -> None:
        all_rulesets = AllRulesets.load_all_rulesets()

        if ps_discovery_rules := all_rulesets.get_rulesets().get(PS_DISCOVERY_RULE_NAME):
            add_ps_discovery_rules(logger, ps_discovery_rules)
            overwrite_default_ec_rule(logger, ps_discovery_rules)

        all_rulesets.save(pprint_value=active_config.wato_pprint_config, debug=active_config.debug)


def add_ps_discovery_rules(
    logger: Logger,
    ps_discovery_rules: Ruleset,
) -> None:
    root_folder = folder_tree().root_folder()
    if _some_shipped_rules_present(ps_discovery_rules):
        # a new default rule was added since the previous batch was added
        add_new_default_rules(logger, ps_discovery_rules, root_folder)
        return

    for rule in reversed(INVENTORY_PROCESS_DISCOVERY_RULES):
        logger.info("Adding: %s", rule["options"]["description"])
        ps_discovery_rules.prepend_rule(
            root_folder, Rule.from_config(root_folder, ps_discovery_rules, rule)
        )


def add_new_default_rules(logger: Logger, ps_discovery_rules: Ruleset, root_folder: Folder) -> None:
    for rule in reversed(INVENTORY_PROCESS_DISCOVERY_RULES):
        if rule["id"] not in _NEW_DEFAULT_RULE_IDS or rule_present(ps_discovery_rules, rule["id"]):
            continue

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
            default_rule = next(
                rule for rule in INVENTORY_PROCESS_DISCOVERY_RULES if rule["id"] == rule_id
            )
        except StopIteration:
            logger.debug("No actual rule for %s.", ps_descr)
            return
        rule.value["match"] = default_rule["value"]["match"]
        logger.info("Overwriting default value: %s", rule.rule_options.description)
    else:
        logger.debug("Rule for %s was changed. Nothing to do.", ps_descr)


def overwrite_default_ec_rule(logger: Logger, ps_discovery_rules: Ruleset) -> None:
    # One-time migration: the corrected default covers new sites, this fixes existing ones.
    _ = ExpiryVersion.CMK_310

    # The event console may be started with optional built-in receivers appended
    # to its command line (--syslog, --syslog-tcp, --snmptrap). The original
    # default anchored the command line with "$" right after "mkeventd", so such
    # sites reported the service as CRIT.
    overwrite_ps_discovery_rule(
        logger,
        ps_discovery_rules,
        EVENT_CONSOLE_RULE_ID,
        "~python3 /omd/sites/[^/]+/bin/mkeventd$",
        "self-monitoring of the event console",
    )


def rule_present(current_rules: Ruleset, rule_id: str) -> bool:
    try:
        current_rules.get_rule_by_id(rule_id)
        return True
    except KeyError:
        pass
    return False


def _some_shipped_rules_present(current_rules: Ruleset) -> bool:
    for rule in INVENTORY_PROCESS_DISCOVERY_RULES:
        if rule_present(current_rules, rule["id"]):
            return True
    return False


update_action_registry.register(
    UpdatePSDiscovery(
        name="rulesets_add_ps_discovery",
        title="Process discovery for self monitoring",
        sort_index=40,  # after ruleset migration
        expiry_version=ExpiryVersion.NEVER,
    )
)
