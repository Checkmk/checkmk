#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from logging import Logger
from typing import override

from cmk.utils import tty

from cmk.gui.watolib.rulesets import AllRulesets

from cmk.update_config.registry import update_action_registry, UpdateAction


class CheckHTTPRules(UpdateAction):
    @override
    def __call__(self, logger: Logger) -> None:
        http_ruleset = AllRulesets.load_all_rulesets().get("active_checks:http")
        if http_ruleset is not None:
            if (count := len(http_ruleset.get_rules())) > 0:
                logger.info(
                    tty.format_warning(
                        f"You have {tty.yellow}{count} {tty.white}{'rule' if count == 1 else 'rules'} "
                        f"using the ruleset {tty.yellow}Check HTTP service deprecated{tty.white}.\n"
                        "This ruleset will be deprecated along with the old HTTP "
                        "monitoring plug-in in the next version(s) of Checkmk.\n"
                        "Rules must therefore be migrated to the new ruleset which is used by the httpv2 plugin.\n"
                        f"Rule migration can be done manually or by calling {tty.yellow}cmk-migrate-http "
                        f"{tty.white}as site user. See cmk-migrate-http --help "
                        "for more information on this helper script.\n"
                        "For additional information on the deprecation of the HTTP plug-in see the werk #17665."
                    )
                )


update_action_registry.register(
    CheckHTTPRules(
        name="check_http_rules",
        title="Check for check_http plug-in rules",
        sort_index=997,
    )
)
