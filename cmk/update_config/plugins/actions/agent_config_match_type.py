#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from typing import override

from cmk.gui.config import active_config
from cmk.gui.watolib.rulesets import AllRulesets, RulesetCollection
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.registry import update_action_registry, UpdateAction

MATCH_TYPE_KEY = "cmk-match-type"


class RemoveAgentConfigMatchType(UpdateAction):
    @override
    def __call__(self, logger: Logger) -> None:
        all_rulesets = AllRulesets.load_all_rulesets()
        _remove_match_type_from_agent_config_rules(logger, all_rulesets)
        all_rulesets.save(pprint_value=active_config.wato_pprint_config, debug=active_config.debug)


def _remove_match_type_from_agent_config_rules(
    logger: Logger,
    all_rulesets: RulesetCollection,
) -> None:
    for ruleset_name, ruleset in all_rulesets.get_rulesets().items():
        if not ruleset_name.startswith("agent_config:"):
            continue

        for _folder, _index, rule in ruleset.get_rules():
            if isinstance(rule.value, dict) and MATCH_TYPE_KEY in rule.value:
                rule.value.pop(MATCH_TYPE_KEY)
                logger.debug("Removed '%s' from rule in ruleset '%s'", MATCH_TYPE_KEY, ruleset_name)


update_action_registry.register(
    RemoveAgentConfigMatchType(
        name="agent_config_remove_match_type",
        title="Remove cmk-match-type from agent config rules",
        sort_index=29,  # before the main rulesets action at 30
        expiry_version=ExpiryVersion.CMK_260,
    )
)
