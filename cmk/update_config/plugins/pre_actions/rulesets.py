#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Pre update checks, executed before any configuration is changed."""

import warnings
from collections.abc import Sequence
from logging import Logger

from cmk.utils import version
from cmk.utils.log import VERBOSE
from cmk.utils.redis import disable_redis
from cmk.utils.rulesets.definition import RuleGroup

from cmk.gui.exceptions import MKUserError
from cmk.gui.groups import GroupSpec, load_contact_group_information
from cmk.gui.session import SuperUserContext
from cmk.gui.utils.script_helpers import gui_context
from cmk.gui.valuespec import RegexFutureWarning
from cmk.gui.watolib.hosts_and_folders import Folder
from cmk.gui.watolib.rulesets import AllRulesets, Ruleset, RulesetCollection
from cmk.gui.wsgi.blueprints.global_vars import set_global_vars

from cmk.update_config.plugins.actions.rulesets import REPLACED_RULESETS
from cmk.update_config.plugins.pre_actions.utils import (
    ConflictMode,
    continue_per_users_choice,
    Resume,
)
from cmk.update_config.registry import pre_update_action_registry, PreUpdateAction


class PreUpdateRulesets(PreUpdateAction):
    """Load all rulesets before the real update happens"""

    def __call__(self, logger: Logger, conflict_mode: ConflictMode) -> None:
        try:
            with disable_redis(), gui_context(), SuperUserContext():
                set_global_vars()
                rulesets = AllRulesets.load_all_rulesets()
        except Exception as exc:
            logger.error(f"Exception while trying to load rulesets: {exc}\n\n")
            if _continue_on_ruleset_exception(conflict_mode).is_not_abort():
                return None
            raise MKUserError(None, "an incompatible ruleset") from exc

        with disable_redis(), gui_context(), SuperUserContext():
            set_global_vars()
            result = _validate_rule_values(
                rulesets,
                load_contact_group_information(),
                conflict_mode,
                logger,
            )
            for ruleset in rulesets.get_rulesets().values():
                try:
                    ruleset.valuespec()
                except Exception:
                    logger.error(
                        "ERROR: Failed to load Ruleset: %s. "
                        "There is likely an error in the implementation.",
                        ruleset.name,
                    )
                    logger.exception("This is the exception: ")
                    if _continue_on_broken_ruleset(conflict_mode).is_abort():
                        raise MKUserError(None, "broken ruleset")
        if not result:
            raise MKUserError(None, "failed ruleset validation")
        return None


def _continue_on_broken_ruleset(conflict_mode: ConflictMode) -> Resume:
    match conflict_mode:
        case ConflictMode.FORCE:
            return Resume.UPDATE
        case ConflictMode.ABORT:
            return Resume.UPDATE
        case ConflictMode.INSTALL | ConflictMode.KEEP_OLD:
            return Resume.UPDATE
        case ConflictMode.ASK:
            return continue_per_users_choice(
                "You can abort the update process (A) or continue (c) the update. Abort update? [A/c]\n"
            )


def _continue_on_invalid_rule(conflict_mode: ConflictMode) -> Resume:
    match conflict_mode:
        case ConflictMode.FORCE:
            return Resume.UPDATE
        case ConflictMode.ABORT:
            return Resume.ABORT
        case ConflictMode.INSTALL | ConflictMode.KEEP_OLD:
            return Resume.UPDATE
        case ConflictMode.ASK:
            return continue_per_users_choice(
                "You can abort the update process (A) or continue (c) the update. Abort update? [A/c]\n"
            )


def _continue_on_ruleset_exception(conflict_mode: ConflictMode) -> Resume:
    match conflict_mode:
        case ConflictMode.FORCE:
            return Resume.UPDATE
        case ConflictMode.ABORT:
            return Resume.ABORT
        case ConflictMode.INSTALL | ConflictMode.KEEP_OLD:
            return Resume.ABORT
        case ConflictMode.ASK:
            return continue_per_users_choice(
                "You can abort the update process (A) and try to fix "
                "the incompatibilities or try to continue the update (c).\n"
                "Abort update? [A/c]\n"
            )


def _validate_rule_values(
    all_rulesets: RulesetCollection,
    contact_groups: GroupSpec,
    conflict_mode: ConflictMode,
    logger: Logger,
) -> bool:
    rulesets_skip = {
        # the valid choices for this ruleset are user-dependent (SLAs) and not even an admin can
        # see all of them
        RuleGroup.ExtraServiceConf("_sla_config"),
        # validating a ruleset for static checks, where we want to replace the ruleset anyway,
        # does not work:
        # * the validation checks if there are checks which subscribe to that check group
        # * when replacing a ruleset, we have no check anymore subscribing to the old name
        # * in that case, the validation will always fail, so we skip it during update
        # * the rule validation with the replaced ruleset will happen after the replacing anyway again
        # see cmk.update_config.plugins.actions.rulesets._validate_rule_values
        *{ruleset for ruleset in REPLACED_RULESETS if ruleset.startswith("static_checks:")},
        # Validating the ignored checks ruleset does not make sense:
        # Invalid choices are the plugins that don't exist (anymore).
        # These do no harm, they are dropped upon rule edit. On the other hand, the plugin
        # could be missing only temporarily, so better not remove it.
        "ignored_checks",
        "snmp_exclude_sections",  # same as "ignored_checks".
        "snmp_check_interval",  # same as "ignored_checks".
    }

    for ruleset in all_rulesets.get_rulesets().values():
        if ruleset.name in rulesets_skip:
            continue

        for folder, index, rule in ruleset.get_rules():
            logger.log(
                VERBOSE,
                f"Validating ruleset '{ruleset.name}' in folder '{folder.name()}'",
            )
            with warnings.catch_warnings(action="error", category=RegexFutureWarning):
                try:
                    ruleset.rulespec.valuespec.validate_value(
                        rule.value,
                        "",
                    )
                except RegexFutureWarning as e:
                    error_messages = [
                        f"WARNING: {e}",
                        f"Ruleset: {ruleset.name}",
                        f"Title: {ruleset.title()}",
                        f"Folder: {folder.path() or 'main'}",
                        f"Rule nr: {index + 1}",
                        "At the moment your regex works correctly, but it might stop working or",
                        "behave differently in a future Python version. Please consider updating it.",
                        "",
                    ]

                    if version.edition() is version.Edition.CME and ruleset.name in (
                        "host_contactgroups",
                        "host_groups",
                        "service_contactgroups",
                        "service_groups",
                    ):
                        error_messages += [
                            "Note:",
                            (
                                f"The group {rule.value!r} may not be synchronized to this site because"
                                " the customer setting of the group is not set to global."
                            ),
                            (
                                "If you continue the invalid rule does not have any effect but should"
                                " be fixed anyway.\n"
                            ),
                        ]

                    logger.warning("\n".join(error_messages))

                except (MKUserError, AssertionError, ValueError, TypeError) as e:
                    if version.edition() is version.Edition.CME and ruleset.name in (
                        "host_contactgroups",
                        "host_groups",
                        "service_contactgroups",
                        "service_groups",
                    ):
                        addition_info = [
                            "Note:",
                            (
                                f"The group {rule.value!r} may not be synchronized to this site because"
                                " the customer setting of the group is not set to global."
                            ),
                            (
                                "If you continue the invalid rule does not have any effect but should"
                                " be fixed anyway.\n"
                            ),
                        ]
                    else:
                        addition_info = []
                    error_message = _error_message(ruleset, folder, index, e, addition_info)
                    logger.error(error_message)
                    if _continue_on_invalid_rule(conflict_mode).is_abort():
                        return False

    return True


def _error_message(
    ruleset: Ruleset,
    folder: Folder,
    index: int,
    exception: Exception,
    additional_info: Sequence[str],
) -> str:
    parts = [
        "WARNING: Invalid rule configuration detected",
        f"Ruleset: {ruleset.name}",
        f"Title: {ruleset.title()}",
        f"Folder: {folder.path() or 'main'}",
        f"Rule nr: {index + 1}",
        f"Exception: {exception}\n",
    ]
    if additional_info:
        parts.extend(additional_info)
    return "\n".join(parts)


pre_update_action_registry.register(
    PreUpdateRulesets(
        name="rulesets",
        title="Rulesets",
        sort_index=10,
    )
)
