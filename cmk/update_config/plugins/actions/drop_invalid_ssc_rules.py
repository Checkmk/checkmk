#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from typing import override

from cmk.ccc.site import omd_site
from cmk.gui.config import active_config
from cmk.gui.user_sites import activation_sites
from cmk.gui.watolib.pending_changes import NoopPendingChangesStore, PendingChanges
from cmk.gui.watolib.rulesets import AllRulesets, RulesetCollection
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.utils.rulesets.definition import RuleGroup


def _is_valid_ssc_value(value: object) -> bool:
    return isinstance(value, dict) and all(isinstance(k, str) for k in value)


def drop_invalid_ssc_rules(
    all_rulesets: RulesetCollection,
    pending_changes: PendingChanges,
    logger: Logger,
) -> int:
    """Delete all SSC rules whose values are not Mapping[str, object]s

    These days, we rely on all values of these type of rules to be Mappings.
    This is ensured by the new ruleset types, but users could have old
    configurations flying around. Those rules have been ignored at config
    load time until now.
    """
    n_dropped = 0
    for ruleset in all_rulesets.get_rulesets().values():
        if not (
            RuleGroup.is_active_checks_rule(ruleset.name)
            or RuleGroup.is_special_agents_rule(ruleset.name)
        ):
            continue
        for folder, _index, rule in ruleset.get_rules():
            if _is_valid_ssc_value(rule.value):
                continue
            logger.info(
                f"Dropping rule {rule.id} of ruleset '{ruleset.name}' in folder "
                f"'{folder.path() or 'main'}': its value is not a dictionary, "
                "so it has been ignored anyway"
            )
            ruleset.delete_rule(rule, create_change=False, pending_changes=pending_changes)
            n_dropped += 1
    return n_dropped


class DropInvalidSSCRules(UpdateAction):
    @override
    def __call__(self, logger: Logger) -> None:
        all_rulesets = AllRulesets.load_all_rulesets()
        pending_changes = PendingChanges(
            activation_sites=activation_sites(active_config.sites),
            local_site=omd_site(),
            acting_user=None,
            store=NoopPendingChangesStore(),
            hooks=(),
        )
        if drop_invalid_ssc_rules(all_rulesets, pending_changes, logger):
            all_rulesets.save(
                pprint_value=active_config.wato_pprint_config, debug=active_config.debug
            )


update_action_registry.register(
    DropInvalidSSCRules(
        name="drop_invalid_ssc_rules",
        title="Drop invalid rules of active checks and special agents",
        sort_index=18,  # before rulesets
        expiry_version=ExpiryVersion.CMK_310,
    )
)
