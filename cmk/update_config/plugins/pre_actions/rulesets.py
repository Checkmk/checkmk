#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Pre update checks, executed before any configuration is changed."""

import warnings
from dataclasses import dataclass
from logging import Logger
from typing import override

from cmk.ccc import version

from cmk.utils import paths
from cmk.utils.log import VERBOSE
from cmk.utils.redis import disable_redis

from cmk.gui.exceptions import MKUserError
from cmk.gui.groups import GroupSpec
from cmk.gui.session import SuperUserContext
from cmk.gui.utils.script_helpers import gui_context
from cmk.gui.valuespec.definitions import RegexFutureWarning
from cmk.gui.watolib.groups_io import load_contact_group_information
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

    @override
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
            with warnings.catch_warnings(action="error", category=RegexFutureWarning):
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
                    add_info = _additional_info(ruleset, rule.value, contact_groups)
                    logger.warning("\n".join(error_messages + add_info.messages))

                except (MKUserError, AssertionError, ValueError, TypeError) as e:
                    error_messages = [
                        "WARNING: Invalid rule configuration detected",
                        f"Ruleset: {ruleset.name}",
                        f"Title: {ruleset.title()}",
                        f"Folder: {folder.path() or 'main'}",
                        f"Rule nr: {index + 1}",
                        f"Exception: {e}\n",
                    ]
                    add_info = _additional_info(ruleset, rule.value, contact_groups)
                    logger.error("\n".join(error_messages + add_info.messages))
                    if add_info.skip_user_input:
                        continue
                    if _continue_on_invalid_rule(conflict_mode).is_abort():
                        return False

    return True


@dataclass(frozen=True, kw_only=True)
class _AdditionalInfo:
    messages: list[str]
    skip_user_input: bool


def _additional_info(
    ruleset: Ruleset,
    rule_value: object,
    contact_groups: GroupSpec,
) -> _AdditionalInfo:
    if version.edition(paths.omd_root) is not version.Edition.CME:
        return _AdditionalInfo(messages=[], skip_user_input=False)
    if ruleset.name not in (
        "host_contactgroups",
        "host_groups",
        "service_contactgroups",
        "service_groups",
    ):
        return _AdditionalInfo(messages=[], skip_user_input=False)
    if rule_value == "all" and (
        "all" not in contact_groups
        or ("all" in contact_groups and "customer" not in contact_groups["all"])
    ):
        # These special cases are handled later in the update action 'SetContactGroupAllScope'.
        # Thus we skip them here.
        return _AdditionalInfo(
            messages=["Note:", f"The group {rule_value!r} will be automatically updated later.\n"],
            skip_user_input=True,
        )
    return _AdditionalInfo(
        messages=[
            "Note:",
            (
                f"The group {rule_value!r} may not be synchronized to this site because"
                " the customer setting of the group is not set to global."
            ),
            (
                "If you continue the invalid rule does not have any effect but should be fixed anyway.\n"
            ),
        ],
        skip_user_input=False,
    )


pre_update_action_registry.register(
    PreUpdateRulesets(
        name="rulesets",
        title="Rulesets",
        sort_index=10,
    )
)
