#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from typing import override

from cmk.gui.watolib.rulesets import AllRulesets, RulesetCollection
from cmk.update_config.lib import ExpiryVersion, format_warning
from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.utils.rulesets.definition import RuleGroup

_LEGACY_RULESET_NAME = RuleGroup.SpecialAgents("hivemanager_ng")


def warn_obsolete_hivemanager_ng_rules(
    all_rulesets: RulesetCollection,
    logger: Logger,
) -> None:
    """Warn about obsolete Aerohive HiveManager NG special agent rules.

    Werk 16920 added the "Extreme Networks ExtremeCloud IQ" special agent as a
    replacement since Extreme Networks deprecated the legacy Aerohive Developer API
    the "Aerohive HiveManager NG" agent relied on (FN-2026-526).
    We leave the existing rules untouched but only ask the admin to migrate them manually.
    """
    if not all_rulesets.exists(_LEGACY_RULESET_NAME):
        return

    if not (n_rules := len(all_rulesets.get(_LEGACY_RULESET_NAME).get_rules())):
        return

    logger.warning(
        format_warning(
            "You have %(count)d rule(s) of the obsolete special agent 'Aerohive HiveManager NG'. "
            "Extreme Networks deprecated the legacy Aerohive Developer API it uses "
            "(FN-2026-526). Please migrate them manually to the "
            "'Extreme Networks ExtremeCloud IQ' special agent, using the "
            "ExtremeCloud IQ base URL (https://api.extremecloudiq.com), username and password."
        ),
        {"count": n_rules},
    )


class WarnObsoleteHivemanagerNgRules(UpdateAction):
    @override
    def __call__(self, logger: Logger) -> None:
        warn_obsolete_hivemanager_ng_rules(AllRulesets.load_all_rulesets(), logger)


update_action_registry.register(
    WarnObsoleteHivemanagerNgRules(
        name="warn_obsolete_hivemanager_ng_rules",
        title="Warn about obsolete Aerohive HiveManager NG special agent rules",
        sort_index=19,  # before rulesets (30)
        expiry_version=ExpiryVersion.CMK_260,
    )
)
