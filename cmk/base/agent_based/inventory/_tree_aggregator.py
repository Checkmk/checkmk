#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass
from typing import NamedTuple

from cmk.utils.structured_data import (
    ATTRIBUTES_KEY,
    make_filter_from_choice,
    parse_visible_raw_path,
    RawIntervalsFromConfig,
    RetentionIntervals,
    SDFilterFunc,
    SDPath,
    StructuredDataNode,
    TABLE_KEY,
    UpdateResult,
)

from cmk.base.api.agent_based.inventory_classes import Attributes, TableRow

RawCacheInfo = tuple[int, int]


class IntervalFromConfig(NamedTuple):
    choices: tuple[str, list[str]] | str
    interval: int


class RetentionInfo(NamedTuple):
    filter_func: SDFilterFunc
    intervals: RetentionIntervals


RetentionKey = tuple[SDPath, str]
RetentionInfos = dict[RetentionKey, RetentionInfo]
IntervalsFromConfig = dict[RetentionKey, IntervalFromConfig]


@dataclass(frozen=True)
class ItemsOfInventoryPlugin:
    items: list[Attributes | TableRow]
    raw_cache_info: tuple[int, int] | None


class RealHostTreeUpdater:
    def __init__(self, raw_intervals_from_config: RawIntervalsFromConfig) -> None:
        self._from_config = _get_intervals_from_config(raw_intervals_from_config)
        self._retention_infos: RetentionInfos = {}

    # ---from retention intervals-------------------------------------------

    # Data for the HW/SW Inventory has a validity period (live data or persisted).
    # With the retention intervals configuration you can keep specific attributes or table columns
    # longer than their validity period.
    #
    # 1.) Collect cache infos from plugins if and only if there is a configured 'path-to-node' and
    #     attributes/table keys entry in the ruleset 'Retention intervals for HW/SW inventory
    #     entities'.
    #
    # 2.) Process collected cache infos - handle the following four cases via AttributesUpdater,
    #     TableUpdater:
    #
    #       previous node | inv node | retention intervals from
    #     -----------------------------------------------------------------------------------
    #       no            | no       | None
    #       no            | yes      | inv_node keys
    #       yes           | no       | previous_node keys
    #       yes           | yes      | previous_node keys + inv_node keys
    #
    #     - If there's no previous node then filtered keys + intervals of current node is stored
    #       (like a first run) and will be checked against the future node in the next run.
    #     - if there's a previous node then check if the data is recent enough and merge
    #       attributes/tables data from the previous node with the current one.
    #       'Recent enough' means: now <= cache_at + cache_interval + retention_interval
    #       where cache_at, cache_interval: from agent data (or set to (now, 0) if not persisted),
    #             retention_interval: configured in the above ruleset

    def may_add_cache_info(
        self,
        *,
        now: int,
        items_of_inventory_plugins: Collection[ItemsOfInventoryPlugin],
    ) -> None:
        def _get_node_type(item: Attributes | TableRow) -> str:
            if isinstance(item, Attributes):
                return ATTRIBUTES_KEY
            if isinstance(item, TableRow):
                return TABLE_KEY
            raise NotImplementedError()

        raw_cache_info_by_retention_key = {
            (tuple(item.path), _get_node_type(item)): items_of_inventory_plugin.raw_cache_info
            for items_of_inventory_plugin in items_of_inventory_plugins
            for item in items_of_inventory_plugin.items
        }

        for retention_key, from_config in self._from_config.items():
            if (raw_cache_info := raw_cache_info_by_retention_key.get(retention_key)) is None:
                raw_cache_info = (now, 0)

            self._retention_infos.setdefault(
                retention_key,
                RetentionInfo(
                    make_filter_from_choice(from_config.choices),
                    RetentionIntervals(
                        cached_at=raw_cache_info[0],
                        cache_interval=raw_cache_info[1],
                        retention_interval=from_config.interval,
                    ),
                ),
            )

    def may_update(
        self,
        *,
        now: int,
        inventory_tree: StructuredDataNode,
        previous_tree: StructuredDataNode,
    ) -> UpdateResult:
        if not self._from_config:
            inventory_tree.remove_retentions()
            return UpdateResult(
                save_tree=False,
                reason="No retention intervals found.",
            )

        results = []
        for retention_key, retention_info in self._retention_infos.items():
            node_path, node_type = retention_key

            if (previous_node := previous_tree.get_node(node_path)) is None:
                previous_node = StructuredDataNode()

            if (inv_node := inventory_tree.get_node(node_path)) is None:
                inv_node = inventory_tree.setdefault_node(node_path)

            if node_type == ATTRIBUTES_KEY:
                results.append(
                    inv_node.attributes.update_from_previous(
                        now,
                        previous_node.attributes,
                        retention_info.filter_func,
                        retention_info.intervals,
                    )
                )

            elif node_type == TABLE_KEY:
                results.append(
                    inv_node.table.update_from_previous(
                        now,
                        previous_node.table,
                        retention_info.filter_func,
                        retention_info.intervals,
                    )
                )

        return UpdateResult(
            save_tree=any(result.save_tree for result in results),
            reason=", ".join(result.reason for result in results if result.reason),
        )


#   .--config--------------------------------------------------------------.
#   |                                      __ _                            |
#   |                      ___ ___  _ __  / _(_) __ _                      |
#   |                     / __/ _ \| '_ \| |_| |/ _` |                     |
#   |                    | (_| (_) | | | |  _| | (_| |                     |
#   |                     \___\___/|_| |_|_| |_|\__, |                     |
#   |                                           |___/                      |
#   '----------------------------------------------------------------------'


def _get_intervals_from_config(
    raw_intervals_from_config: RawIntervalsFromConfig,
) -> IntervalsFromConfig:
    intervals: IntervalsFromConfig = {}

    for entry in raw_intervals_from_config:
        interval = entry["interval"]
        node_path = tuple(parse_visible_raw_path(entry["visible_raw_path"]))

        if for_attributes := entry.get("attributes"):
            intervals.setdefault(
                (node_path, ATTRIBUTES_KEY), IntervalFromConfig(for_attributes, interval)
            )

        if for_table := entry.get("columns"):
            intervals.setdefault((node_path, TABLE_KEY), IntervalFromConfig(for_table, interval))

    return intervals


# .
