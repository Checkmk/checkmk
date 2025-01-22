#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger

from cmk.gui.exceptions import MKUserError
from cmk.gui.watolib.hosts_and_folders import Folder
from cmk.gui.watolib.rulesets import Ruleset, RulesetCollection

from cmk.update_config.lib import format_warning
from cmk.update_config.plugins.lib.rulesets import load_and_transform, SKIP_ACTION
from cmk.update_config.registry import update_action_registry, UpdateAction


class UpdateRulesets(UpdateAction):
    def __call__(self, logger: Logger) -> None:
        all_rulesets = load_and_transform(logger)
        validate_rule_values(logger, all_rulesets)
        all_rulesets.save()


def validate_rule_values(
    logger: Logger,
    all_rulesets: RulesetCollection,
) -> None:
    n_invalid, n_broken = 0, 0
    for ruleset in all_rulesets.get_rulesets().values():
        if ruleset.name in SKIP_ACTION:
            continue

        for folder, index, rule in ruleset.get_rules():
            try:
                ruleset.rulespec.valuespec.validate_value(
                    rule.value,
                    "",
                )
            except MKUserError as excpt:
                n_invalid += 1
                logger.warning(
                    format_warning(
                        f"WARNING: Invalid rule configuration detected ({_make_rule_reference(ruleset, folder, index, excpt)})"
                    ),
                )

            except Exception as excpt:
                n_broken += 1
                logger.warning(
                    format_warning(
                        f"WARNING: Exception in ruleset implementation detected ({_make_rule_reference(ruleset, folder, index, excpt)})"
                    ),
                    exc_info=True,
                )

    if n_invalid:
        logger.warning(
            format_warning(
                "Detected %s issue(s) in configured rules.\n"
                "To correct these issues, we recommend to open the affected rules in the GUI.\n"
                "Upon attempting to save them, any problematic fields will be highlighted."
            ),
            n_invalid,
        )
    if n_broken:
        logger.warning(
            format_warning(
                "Detected %s issue(s) in loaded rulesets. This is a problem with the plug-in implementation.\n"
                "To correct these issues, fix either the `migrate` or `custom_validate` attribute."
            ),
            n_broken,
        )


def _make_rule_reference(ruleset: Ruleset, folder: Folder, index: int, excpt: Exception) -> str:
    return (
        f"Ruleset: {ruleset.name}, Title: {ruleset.title()}, Folder: {folder.path()},\n"
        f"Rule nr: {index + 1}, Exception: {excpt}"
    )


update_action_registry.register(
    UpdateRulesets(
        name="rulesets",
        title="Rulesets",
        sort_index=30,
    )
)
