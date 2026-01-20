#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from logging import Logger
from typing import override

from cmk.ccc import tty
from cmk.gui.config import active_config
from cmk.gui.site_config import is_distributed_setup_remote_site
from cmk.gui.watolib.rulesets import AllRulesets
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.registry import update_action_registry, UpdateAction


class CheckHTTPRules(UpdateAction):
    @override
    def __call__(self, logger: Logger) -> None:
        if is_distributed_setup_remote_site(active_config.sites):
            return None
        http_ruleset = AllRulesets.load_all_rulesets().get("active_checks:http")
        if (count := len(http_ruleset.get_rules())) > 0:
            logger.info(
                tty.format_warning(
                    f"You have {tty.yellow}{count} {tty.normal}{'rule' if count == 1 else 'rules'} "
                    f"using the ruleset {tty.yellow}Check HTTP service deprecated{tty.normal}.\n"
                    "This ruleset will be deprecated along with the old HTTP "
                    "monitoring plug-in in the next version(s) of Checkmk.\n"
                    "Rules must therefore be migrated to the new ruleset which is used by the httpv2 plugin.\n"
                    f"Rule migration can be done manually or by calling {tty.yellow}cmk-migrate-http "
                    f"{tty.normal}as site user.\n"
                    "See our blog post for more information on this helper script:\n"
                    "https://checkmk.com/blog/migrating-new-http-active-check\n"
                    "For additional information on the deprecation of the HTTP plug-in see the werk #17665."
                )
            )


update_action_registry.register(
    CheckHTTPRules(
        name="check_http_rules",
        title="Check for deprecated check_http plug-in rules",
        sort_index=997,
        expiry_version=ExpiryVersion.CMK_300,
    )
)
