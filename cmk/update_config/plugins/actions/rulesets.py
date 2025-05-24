#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from typing import override

from cmk.gui.config import active_config
from cmk.gui.crash_handler import create_gui_crash_report
from cmk.gui.exceptions import MKUserError
from cmk.gui.watolib.hosts_and_folders import Folder
from cmk.gui.watolib.rulesets import Ruleset, RulesetCollection

from cmk.update_config.lib import format_warning
from cmk.update_config.plugins.lib.rulesets import load_and_transform, SKIP_ACTION
from cmk.update_config.registry import update_action_registry, UpdateAction


class UpdateRulesets(UpdateAction):
    @override
    def __call__(self, logger: Logger) -> None:
        all_rulesets = load_and_transform(logger)
        validate_rule_values(logger, all_rulesets)
        all_rulesets.save(pprint_value=active_config.wato_pprint_config, debug=active_config.debug)


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
                ruleset.rulespec.valuespec.validate_datatype(
                    rule.value,
                    "",
                )
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
                identity = create_gui_crash_report().ident_to_text()
                logger.warning(f"A crash report was generated with ID: {identity}")

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
                "Detected %s issue(s) in loaded rulesets. This is a problem with the plug-in "
                "implementation. It needs to be addressed by the maintainers. Please review the "
                "crashes in the crash reports page to help fix the issues. "
                "Until all issues are resolved, we recommend disabling the affected rules."
            ),
            n_broken,
        )


def _make_rule_reference(ruleset: Ruleset, folder: Folder, index: int, excpt: Exception) -> str:
    return (
        f"Ruleset: {ruleset.name}, Title: {ruleset.title()}, Folder: {folder.path()},\n"
        f"Rule nr: {index}, Exception: {excpt}"
    )


update_action_registry.register(
    UpdateRulesets(
        name="rulesets",
        title="Rulesets",
        sort_index=30,
    )
)
