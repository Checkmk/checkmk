#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger

from cmk.gui.watolib.rulesets import AllRulesets

from cmk.update_config.registry import update_action_registry, UpdateAction


class CheckHTTPRules(UpdateAction):
    def __call__(self, logger: Logger) -> None:
        http_ruleset = AllRulesets.load_all_rulesets().get("active_checks:http")
        if http_ruleset is not None:
            if (count := len(http_ruleset.get_rules())) > 0:
                logger.warning(
                    f"WARNING: You have {count} rules using the ruleset Check HTTP service."
                )
                logger.info(
                    "This ruleset will be deprecated along with the check_http monitoring plug-in in the next version(s) of Checkmk."
                )
                logger.info(
                    "Rules must therefore be migrated to the new ruleset of the check_httpv2 plugin."
                )
                logger.info(
                    "Rule migration can be done manually or by calling migrate_httpv2 as site user. See migrate_httpv2 --help for more information "
                    "to this helper script. For additional information please see the werk #17665."
                )


update_action_registry.register(
    CheckHTTPRules(
        name="check_http_rules",
        title="Check for check_http plug-in rules",
        sort_index=997,
    )
)
