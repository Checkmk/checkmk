#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from logging import Logger
from typing import override

from cmk.ccc import tty
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKUserError
from cmk.gui.script_helpers import gui_context
from cmk.gui.session import SuperUserContext
from cmk.gui.site_config import is_distributed_setup_remote_site
from cmk.gui.watolib.rulesets import AllRulesets
from cmk.gui.wsgi.blueprints.global_vars import set_global_vars
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.plugins.pre_actions.utils import (
    ConflictMode,
    continue_per_users_choice,
    Resume,
)
from cmk.update_config.registry import pre_update_action_registry, PreUpdateAction
from cmk.utils.redis import disable_redis


class CheckHTTPRules(PreUpdateAction):
    @override
    def __call__(self, logger: Logger, conflict_mode: ConflictMode) -> None:
        with disable_redis(), gui_context(), SuperUserContext():
            set_global_vars()
            if is_distributed_setup_remote_site(active_config.sites):
                return None
            http_ruleset = AllRulesets.load_all_rulesets().get("active_checks:http")
        if (count := len(http_ruleset.get_rules())) > 0:
            logger.info(
                tty.format_warning(
                    f"You have {tty.yellow}{count}{tty.normal} "
                    f"{'rule' if count == 1 else 'rules'} "
                    f"using the ruleset {tty.yellow}Check HTTP service (deprecated){tty.normal}.\n"
                    "Rules must be migrated manually to the new "
                    f"{tty.yellow}Check HTTP web service{tty.normal} ruleset.\n"
                    "The cmk-migrate-http migration tool has been removed. "
                    "See werk #19702 for details.\n"
                )
            )
            if _should_abort(conflict_mode).is_abort():
                raise MKUserError(None, "deprecated check_http rules present")


def _should_abort(conflict_mode: ConflictMode) -> Resume:
    match conflict_mode:
        case ConflictMode.FORCE:
            return Resume.UPDATE
        case ConflictMode.ABORT:
            return Resume.ABORT
        case ConflictMode.ASK:
            return continue_per_users_choice(
                "You can abort the update process (A) or continue (c) the update. Abort update? [A/c]\n"
            )


pre_update_action_registry.register(
    CheckHTTPRules(
        name="check_http_rules",
        title="Check for deprecated check_http plug-in rules",
        sort_index=50,
        expiry_version=ExpiryVersion.CMK_310,
    )
)
