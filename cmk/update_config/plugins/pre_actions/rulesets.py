#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Pre update checks, executed before any configuration is changed."""

from collections.abc import Sequence
from logging import Logger

from cmk.ccc import version

from cmk.utils import paths
from cmk.utils.log import VERBOSE
from cmk.utils.redis import disable_redis

from cmk.gui.exceptions import MKUserError
from cmk.gui.groups import GroupSpec
from cmk.gui.session import SuperUserContext
from cmk.gui.utils.script_helpers import gui_context
from cmk.gui.watolib.groups_io import load_contact_group_information
from cmk.gui.watolib.hosts_and_folders import Folder
from cmk.gui.watolib.rulesets import AllRulesets, Ruleset, RulesetCollection
from cmk.gui.wsgi.blueprints.global_vars import set_global_vars

from cmk.update_config.plugins.lib.rulesets import SKIP_PREACTION
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
            if _continue_on_ruleset_exception(conflict_mode).is_abort():
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
    """Validate all ruleset values.

    Returns True if the update shall continue, False otherwise.
    """
    for ruleset in all_rulesets.get_rulesets().values():
        if ruleset.name in SKIP_PREACTION:
            continue

        for folder, index, rule in ruleset.get_rules():
            logger.log(VERBOSE, f"Validating ruleset '{ruleset.name}' in folder '{folder.name()}'")
            try:
                transformed_value = ruleset.rulespec.valuespec.transform_value(rule.value)
                ruleset.rulespec.valuespec.validate_datatype(
                    transformed_value,
                    "",
                )
                ruleset.rulespec.valuespec.validate_value(
                    transformed_value,
                    "",
                )
            except (MKUserError, AssertionError, ValueError, TypeError) as e:
                error_message = _error_message(ruleset, rule.value, folder, index, e)
                logger.error(error_message)
                if _continue_on_invalid_rule(conflict_mode).is_abort():
                    return False

    return True


def _error_message(
    ruleset: Ruleset,
    rule_value: object,
    folder: Folder,
    index: int,
    exception: Exception,
) -> str:
    return "\n".join(
        [
            "WARNING: Invalid rule configuration detected",
            f"Ruleset: {ruleset.name}",
            f"Title: {ruleset.title()}",
            f"Folder: {folder.path() or 'main'}",
            f"Rule nr: {index + 1}",
            f"Exception: {exception}\n",
            *_make_additional_info(ruleset, rule_value),
        ]
    )


def _make_additional_info(ruleset: Ruleset, rule_value: object) -> Sequence[str]:
    if version.edition(paths.omd_root) is not version.Edition.CME:
        return ()
    if ruleset.name not in (
        "host_contactgroups",
        "host_groups",
        "service_contactgroups",
        "service_groups",
    ):
        return ()
    return (
        "Note:",
        (
            f"The group {rule_value!r} may not be synchronized to this site because"
            " the customer setting of the group is not set to global."
        ),
        ("If you continue the invalid rule does not have any effect but should be fixed anyway.\n"),
    )


pre_update_action_registry.register(
    PreUpdateRulesets(
        name="rulesets",
        title="Rulesets",
        sort_index=10,
    )
)
