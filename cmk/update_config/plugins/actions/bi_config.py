#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger

from cmk.gui.bi._packs import get_cached_bi_packs

from cmk.bi.packs import BIAggregationPacks
from cmk.bi.search import BIHostSearch, BIServiceSearch
from cmk.update_config.plugins.actions.rulesets import (
    transform_condition_labels_to_label_groups,
)
from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.update_config.update_state import UpdateActionState


class UpdateBIConfig(UpdateAction):
    def __call__(self, logger: Logger, update_action_state: UpdateActionState) -> None:
        # This update action simply loads the bi config (i.e. it instantiates BIAggregationPacks
        # from cache) into aggregation_packs, updates these packs and saves the config again.
        aggregation_packs: BIAggregationPacks = get_cached_bi_packs()

        # Do migrations/updates
        _migrate_bi_rule_label_conditions(aggregation_packs)

        aggregation_packs.save_config()


def _migrate_bi_rule_label_conditions(aggregation_packs: BIAggregationPacks) -> None:
    for pack in aggregation_packs.packs.values():
        # aggregation search conditions
        for aggregation in pack.aggregations.values():
            if isinstance(aggregation.node.search, (BIHostSearch, BIServiceSearch)):
                aggregation.node.search.conditions = transform_condition_labels_to_label_groups(
                    aggregation.node.search.conditions
                )

                # handle 'refer_to' in aggregations
                if (
                    isinstance(aggregation.node.search, BIHostSearch)
                    and not isinstance(aggregation.node.search.refer_to, str)
                    and aggregation.node.search.refer_to.get("type") == "child_with"
                ):
                    aggregation.node.search.refer_to["conditions"] = (
                        transform_condition_labels_to_label_groups(
                            aggregation.node.search.refer_to["conditions"]
                        )
                    )

        # rule search conditions
        for rule in pack.rules.values():
            for node in rule.nodes:
                if isinstance(node.search, (BIHostSearch, BIServiceSearch)):
                    node.search.conditions = transform_condition_labels_to_label_groups(
                        node.search.conditions
                    )

                # handle 'refer_to' in rules
                if (
                    isinstance(node.search, BIHostSearch)
                    and not isinstance(node.search.refer_to, str)
                    and node.search.refer_to.get("type") == "child_with"
                ):
                    node.search.refer_to["conditions"] = transform_condition_labels_to_label_groups(
                        node.search.refer_to["conditions"]
                    )


update_action_registry.register(
    UpdateBIConfig(
        name="bi_config",
        title="BI config",
        sort_index=160,
    )
)
