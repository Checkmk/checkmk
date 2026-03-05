#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from typing import cast, override

from cmk.gui.config import active_config
from cmk.gui.watolib.hosts_and_folders import folder_tree
from cmk.gui.watolib.rulesets import AllRulesets, Rule, Ruleset, RulesetCollection
from cmk.gui.watolib.sample_config._constants import SHIPPED_RULES
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.utils.rulesets.ruleset_matcher import RuleSpec

HOST_CHECK_COMMANDS_RULESET_NAME = "host_check_commands"
PODMAN_HOST_CHECK_COMMAND_RULE_ID = "1c07de55-49b2-4ceb-839f-9afa81bf1d03"


class UpdateHostCheckCommandRules(UpdateAction):
    @override
    def __call__(self, logger: Logger) -> None:
        all_rulesets = AllRulesets.load_all_rulesets()
        add_host_check_commands_rules(logger, all_rulesets)
        all_rulesets.save(pprint_value=active_config.wato_pprint_config, debug=active_config.debug)


def add_host_check_commands_rules(logger: Logger, all_rulesets: RulesetCollection) -> None:
    if (
        host_check_commands_rules := all_rulesets.get_rulesets().get(
            HOST_CHECK_COMMANDS_RULESET_NAME
        )
    ) is None:
        return

    if _rule_present(host_check_commands_rules, PODMAN_HOST_CHECK_COMMAND_RULE_ID):
        return

    podman_rule = _get_podman_rule_config()
    if podman_rule is None:
        logger.debug("No shipped Podman host check commands rule found.")
        return

    logger.info("Adding shipped Podman host check commands rule")
    root_folder = folder_tree().root_folder()
    host_check_commands_rules.prepend_rule(
        root_folder, Rule.from_config(root_folder, host_check_commands_rules, podman_rule)
    )


def _get_podman_rule_config() -> RuleSpec[object] | None:
    host_check_rules = cast(list[RuleSpec[object]], SHIPPED_RULES[HOST_CHECK_COMMANDS_RULESET_NAME])
    return next(
        (rule for rule in host_check_rules if rule.get("id") == PODMAN_HOST_CHECK_COMMAND_RULE_ID),
        None,
    )


def _rule_present(current_rules: Ruleset, rule_id: str) -> bool:
    try:
        current_rules.get_rule_by_id(rule_id)
        return True
    except KeyError:
        pass
    return False


update_action_registry.register(
    UpdateHostCheckCommandRules(
        name="rulesets_add_host_check_commands",
        title="Host check commands rules",
        sort_index=40,  # after ruleset migration
        expiry_version=ExpiryVersion.NEVER,
    )
)
