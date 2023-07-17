#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
""" Pre update checks, executed before any configuration is changed. """


from cmk.utils.redis import disable_redis

from cmk.gui.exceptions import MKUserError
from cmk.gui.session import SuperUserContext
from cmk.gui.utils.script_helpers import gui_context
from cmk.gui.watolib.hosts_and_folders import Folder
from cmk.gui.watolib.rulesets import AllRulesets, Ruleset, RulesetCollection
from cmk.gui.wsgi.blueprints.global_vars import set_global_vars

from cmk.update_config.plugins.pre_actions.utils import (
    ConflictMode,
    NEED_USER_INPUT_MODES,
    USER_INPUT_CONTINUE,
)
from cmk.update_config.registry import pre_update_action_registry, PreUpdateAction


class PreUpdateRulesets(PreUpdateAction):
    """Load all rulesets before the real update happens"""

    def __call__(self, conflict_mode: ConflictMode) -> None:
        try:
            with disable_redis(), gui_context(), SuperUserContext():
                set_global_vars()
                rulesets = AllRulesets.load_all_rulesets()
        except Exception as exc:
            if (
                conflict_mode in NEED_USER_INPUT_MODES
                and _request_user_input_on_ruleset_exception(exc).lower() in USER_INPUT_CONTINUE
            ):
                return None
            raise MKUserError(None, "an incompatible ruleset") from exc

        with disable_redis(), gui_context(), SuperUserContext():
            set_global_vars()
            result = _validate_rule_values(rulesets, conflict_mode)

        if not result:
            raise MKUserError(None, "failed ruleset validation")

        return None


def _request_user_input_on_ruleset_exception(exc: Exception) -> str:
    return input(
        f"Exception while trying to load rulesets: {exc}\n\n"
        "You can abort the update process (A) and try to fix "
        "the incompatibilities or try to continue the update (c).\n"
        "Abort update? [A/c]\n"
    )


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
            except MKUserError as e:
                return (
                    conflict_mode in NEED_USER_INPUT_MODES
                    and _request_user_input_on_invalid_rule(ruleset, folder, index, e).lower()
                    in USER_INPUT_CONTINUE
                )

    return True


def _request_user_input_on_invalid_rule(
    ruleset: Ruleset, folder: Folder, index: int, exception: MKUserError
) -> str:
    return input(
        "WARNING: Invalid rule configuration detected\n"
        f"Ruleset: {ruleset.name}\n"
        f"Title: {ruleset.title()}\n"
        f"Folder: {folder.path() or 'main'}\n"
        f"Rule nr: {index + 1}\n"
        f"Exception: {exception}\n\n"
        "You can abort the update process (A) and "
        "try to fix the incompatibilities with a downgrade "
        "to the version you came from or continue (c) the update.\n\n"
        "Abort update? [A/c]\n"
    )


pre_update_action_registry.register(
    PreUpdateRulesets(
        name="rulesets",
        title="Rulesets",
        sort_index=10,
    )
)
