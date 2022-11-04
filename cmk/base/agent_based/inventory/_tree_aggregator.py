#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import time
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


def add_cluster_property_to(*, inventory_tree: StructuredDataNode, is_cluster: bool) -> None:
    node = inventory_tree.setdefault_node(("software", "applications", "check_mk", "cluster"))
    node.attributes.add_pairs({"is_cluster": is_cluster})


@dataclass(frozen=True)
class ItemsOfInventoryPlugin:
    items: list[Attributes | TableRow]
    raw_cache_info: tuple[int, int] | None


class RealHostTreeAggregator:
    def __init__(self) -> None:
        super().__init__()
        self._inventory_tree = StructuredDataNode()
        self._status_data_tree = StructuredDataNode()

    @property
    def inventory_tree(self) -> StructuredDataNode:
        return self._inventory_tree

    @property
    def status_data_tree(self) -> StructuredDataNode:
        return self._status_data_tree

    # ---from inventory plugins---------------------------------------------

    def aggregate_results(self, items_of_inventory_plugin: ItemsOfInventoryPlugin) -> None:
        for item in items_of_inventory_plugin.items:
            if isinstance(item, Attributes):
                self._integrate_attributes(item)
            elif isinstance(item, TableRow):
                self._integrate_table_row(item)

    def _integrate_attributes(
        self,
        attributes: Attributes,
    ) -> None:
        if attributes.inventory_attributes:
            node = self._inventory_tree.setdefault_node(tuple(attributes.path))
            node.attributes.add_pairs(attributes.inventory_attributes)

        if attributes.status_attributes:
            node = self._status_data_tree.setdefault_node(tuple(attributes.path))
            node.attributes.add_pairs(attributes.status_attributes)

    def _integrate_table_row(self, table_row: TableRow) -> None:
        # do this always, it sets key_columns!
        node = self._inventory_tree.setdefault_node(tuple(table_row.path))
        node.table.add_key_columns(sorted(table_row.key_columns))
        node.table.add_rows([{**table_row.key_columns, **table_row.inventory_columns}])

        if table_row.status_columns:
            node = self._status_data_tree.setdefault_node(tuple(table_row.path))
            node.table.add_key_columns(sorted(table_row.key_columns))
            node.table.add_rows([{**table_row.key_columns, **table_row.status_columns}])

    # ---static data from config--------------------------------------------

    def add_cluster_property(self) -> None:
        add_cluster_property_to(inventory_tree=self._inventory_tree, is_cluster=False)


class RealHostTreeUpdater:
    def __init__(
        self,
        raw_intervals_from_config: RawIntervalsFromConfig,
        inventory_tree: StructuredDataNode,
    ) -> None:
        self._from_config = _get_intervals_from_config(raw_intervals_from_config)
        self._inventory_tree = inventory_tree
        self._retention_infos: RetentionInfos = {}
        self._update_result = UpdateResult(save_tree=False, reason="")

    @property
    def update_result(self) -> UpdateResult:
        return self._update_result

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

    def may_add_cache_info(self, inventory_plugin_items: ItemsOfInventoryPlugin) -> None:
        now = int(time.time())
        for item in inventory_plugin_items.items:
            if isinstance(item, Attributes):
                self._may_add_cache_info(
                    now=now,
                    node_type=ATTRIBUTES_KEY,
                    path=tuple(item.path),
                    raw_cache_info=inventory_plugin_items.raw_cache_info,
                )
            elif isinstance(item, TableRow):
                self._may_add_cache_info(
                    now=now,
                    node_type=TABLE_KEY,
                    path=tuple(item.path),
                    raw_cache_info=inventory_plugin_items.raw_cache_info,
                )

    def _may_add_cache_info(
        self,
        *,
        now: int,
        node_type: str,
        path: SDPath,
        raw_cache_info: RawCacheInfo | None,
    ) -> None:
        retention_key = (tuple(path), node_type)

        if (from_config := self._from_config.get(retention_key)) is None:
            return

        intervals = self._make_intervals(now, raw_cache_info, from_config.interval)
        filter_func = make_filter_from_choice(from_config.choices)

        self._retention_infos.setdefault(retention_key, RetentionInfo(filter_func, intervals))

    @staticmethod
    def _make_intervals(
        now: int,
        raw_cache_info: RawCacheInfo | None,
        retention_interval: int,
    ) -> RetentionIntervals:
        if raw_cache_info:
            return RetentionIntervals(
                cached_at=raw_cache_info[0],
                cache_interval=raw_cache_info[1],
                retention_interval=retention_interval,
            )
        return RetentionIntervals(
            cached_at=now,
            cache_interval=0,
            retention_interval=retention_interval,
        )

    def may_update(self, now: int, previous_tree: StructuredDataNode) -> None:
        if not self._from_config:
            self._inventory_tree.remove_retentions()
            self._update_result = UpdateResult(
                save_tree=False,
                reason="No retention intervals found.",
            )
            return

        results = []
        for retention_key, retention_info in self._retention_infos.items():
            updater = self._make_updater(retention_key, retention_info, previous_tree)
            results.append(updater.filter_and_merge(now))

        self._update_result = UpdateResult(
            save_tree=any(result.save_tree for result in results),
            reason=", ".join(result.reason for result in results if result.reason),
        )

    def _make_updater(
        self,
        retention_key: RetentionKey,
        retention_info: RetentionInfo,
        previous_tree: StructuredDataNode,
    ) -> NodeUpdater:
        node_path, node_type = retention_key

        inv_node = self._inventory_tree.get_node(node_path)
        previous_node = previous_tree.get_node(node_path)

        if previous_node is None:
            previous_node = StructuredDataNode()

        if inv_node is None:
            inv_node = self._inventory_tree.setdefault_node(node_path)

        if node_type == ATTRIBUTES_KEY:
            return AttributesUpdater(
                retention_info,
                inv_node,
                previous_node,
            )

        if node_type == TABLE_KEY:
            return TableUpdater(
                retention_info,
                inv_node,
                previous_node,
            )

        raise NotImplementedError()


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
#   .--updater-------------------------------------------------------------.
#   |                                _       _                             |
#   |                _   _ _ __   __| | __ _| |_ ___ _ __                  |
#   |               | | | | '_ \ / _` |/ _` | __/ _ \ '__|                 |
#   |               | |_| | |_) | (_| | (_| | ||  __/ |                    |
#   |                \__,_| .__/ \__,_|\__,_|\__\___|_|                    |
#   |                     |_|                                              |
#   '----------------------------------------------------------------------'


class NodeUpdater:
    def __init__(
        self,
        retention_info: RetentionInfo,
        inv_node: StructuredDataNode,
        previous_node: StructuredDataNode,
    ) -> None:
        self._filter_func = retention_info.filter_func
        self._inv_intervals = retention_info.intervals
        self._inv_node = inv_node
        self._previous_node = previous_node

    def filter_and_merge(self, now: int) -> UpdateResult:
        raise NotImplementedError()


class AttributesUpdater(NodeUpdater):
    def filter_and_merge(self, now: int) -> UpdateResult:
        return self._inv_node.attributes.update_from_previous(
            now,
            self._previous_node.attributes,
            self._filter_func,
            self._inv_intervals,
        )


class TableUpdater(NodeUpdater):
    def filter_and_merge(self, now: int) -> UpdateResult:
        return self._inv_node.table.update_from_previous(
            now,
            self._previous_node.table,
            self._filter_func,
            self._inv_intervals,
        )
