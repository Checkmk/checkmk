#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
""" Pre update checks, executed before any configuration is changed. """

import traceback

from cmk.utils.redis import disable_redis

from cmk.gui.exceptions import MKUserError
from cmk.gui.session import SuperUserContext
from cmk.gui.utils.script_helpers import gui_context
from cmk.gui.watolib.rulesets import RulesetCollection
from cmk.gui.wsgi.blueprints.global_vars import set_global_vars

from cmk.update_config.plugins.actions.rulesets import AllRulesets
from cmk.update_config.plugins.pre_actions.utils import ConflictMode
from cmk.update_config.registry import pre_update_action_registry, PreUpdateAction


class PreUpdateRulesets(PreUpdateAction):
    """Load all rulesets before the real update happens"""

    def __call__(self, conflict_mode: ConflictMode) -> None:
        try:
            with disable_redis(), gui_context(), SuperUserContext():
                set_global_vars()
                rulesets = AllRulesets.load_all_rulesets()
        except Exception:
            if conflict_mode in (ConflictMode.INSTALL, ConflictMode.KEEP_OLD) or (
                conflict_mode is ConflictMode.ASK
                and input(
                    "Unknown exception while trying to load rulesets.\n"
                    f"Error: {traceback.format_exc()}\n\n"
                    "You can abort the update process (A) and try to fix "
                    "the incompatibilities or try to continue the update (c).\n"
                    "Abort update? [A/c]\n"
                ).lower()
                in ["c", "continue"]
            ):
                return None
            raise MKUserError(None, "an incompatible ruleset")

        with disable_redis(), gui_context(), SuperUserContext():
            set_global_vars()
            result = _validate_rule_values(rulesets, conflict_mode)

        if not result:
            raise MKUserError(None, "failed ruleset validation")

        return None


def _validate_rule_values(
    all_rulesets: RulesetCollection,
    conflict_mode: ConflictMode,
) -> bool:
    rulesets_skip = {
        # the valid choices for this ruleset are user-dependent (SLAs) and not even an admin can
        # see all of them
        "extra_service_conf:_sla_config",
    }

    for ruleset in all_rulesets.get_rulesets().values():
        if ruleset.name in rulesets_skip:
            continue

        for folder, index, rule in ruleset.get_rules():
            try:
                ruleset.rulespec.valuespec.validate_value(
                    rule.value,
                    "",
                )
            except MKUserError as excpt:
                if conflict_mode in (ConflictMode.INSTALL, ConflictMode.KEEP_OLD) or (
                    conflict_mode is ConflictMode.ASK
                    and input(
                        f"WARNING: Invalid rule configuration detected\n"
                        f"Ruleset: {ruleset.name}\n"
                        f"Title: {ruleset.title()}\n"
                        f"Folder: {folder.path() if folder.path() else 'main'}\n"
                        f"Rule nr: {index + 1}\n"
                        f"Exception: {excpt}\n\n"
                        f"You can abort the update process (A) and "
                        f"try to fix the incompatibilities with a downgrade "
                        f"to the version you came from or continue (c) the update.\n\n"
                        f"Abort update? [A/c]\n"
                    ).lower()
                    in ["c", "continue"]
                ):
                    return True
                return False
    return True


pre_update_action_registry.register(
    PreUpdateRulesets(
        name="rulesets",
        title="Rulesets",
        sort_index=10,
    )
)
