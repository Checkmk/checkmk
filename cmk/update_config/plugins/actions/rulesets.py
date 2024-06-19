#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger

from cmk.utils.rulesets.definition import RuleGroup

from cmk.gui.exceptions import MKUserError
from cmk.gui.watolib.rulesets import RulesetCollection

from cmk.update_config.lib import format_warning
from cmk.update_config.plugins.lib.rulesets import load_and_transform
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
    rulesets_skip = {
        # the valid choices for this ruleset are user-dependent (SLAs) and not even an admin can
        # see all of them
        RuleGroup.ExtraServiceConf("_sla_config"),
        # Validating the ignored checks ruleset does not make sense:
        # Invalid choices are the plugins that don't exist (anymore).
        # These do no harm, they are dropped upon rule edit. On the other hand, the plugin
        # could be missing only temporarily, so better not remove it.
        "ignored_checks",
    }

    n_invalid = 0
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
                n_invalid += 1
                logger.warning(
                    format_warning(
                        "WARNING: Invalid rule configuration detected (Ruleset: %s, Title: %s, "
                        "Folder: %s,\nRule nr: %s, Exception: %s)"
                    ),
                    ruleset.name,
                    ruleset.title(),
                    folder.path(),
                    index + 1,
                    excpt,
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


update_action_registry.register(
    UpdateRulesets(
        name="rulesets",
        title="Rulesets",
        sort_index=30,
    )
)
