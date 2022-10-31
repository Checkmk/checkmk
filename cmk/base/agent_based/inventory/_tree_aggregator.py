#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import time
from typing import Iterable, NamedTuple, Sequence

import cmk.utils.debug
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
from cmk.utils.type_defs import HostName

from cmk.base.api.agent_based.inventory_classes import Attributes, InventoryResult, TableRow

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


class TreeAggregator:
    def __init__(self) -> None:
        self._inventory_tree = StructuredDataNode()
        self._update_result = UpdateResult(save_tree=False, reason="")

    @property
    def inventory_tree(self) -> StructuredDataNode:
        return self._inventory_tree

    @property
    def update_result(self) -> UpdateResult:
        return self._update_result

    # ---static data from config--------------------------------------------

    def _add_cluster_property(self, *, is_cluster: bool) -> None:
        node = self._inventory_tree.setdefault_node(
            ("software", "applications", "check_mk", "cluster")
        )
        node.attributes.add_pairs({"is_cluster": is_cluster})


class ClusterTreeAggregator(TreeAggregator):

    # ---static data from config--------------------------------------------

    def add_cluster_properties(self, *, nodes: list[HostName]) -> None:
        self._add_cluster_property(is_cluster=True)

        if nodes:
            node = self._inventory_tree.setdefault_node(
                ("software", "applications", "check_mk", "cluster", "nodes")
            )
            node.table.add_key_columns(["name"])
            node.table.add_rows([{"name": node_name} for node_name in nodes])


class RealHostTreeAggregator(TreeAggregator):
    def __init__(self, raw_intervals_from_config: RawIntervalsFromConfig) -> None:
        super().__init__()
        self._from_config = _get_intervals_from_config(raw_intervals_from_config)
        self._retention_infos: RetentionInfos = {}
        self._status_data_tree = StructuredDataNode()
        self._class_mutex: dict[tuple, str] = {}

    @property
    def status_data_tree(self) -> StructuredDataNode:
        return self._status_data_tree

    # ---from inventory plugins---------------------------------------------

    def aggregate_results(
        self,
        *,
        inventory_generator: InventoryResult,
        raw_cache_info: RawCacheInfo | None,
        is_legacy_plugin: bool,
    ) -> Exception | None:

        try:
            table_rows, attributes = self._dispatch(inventory_generator)
        except Exception as exc:
            # TODO(ml): Returning the error is one possibly valid way to
            #           handle it.  What is the `if cmk.utils.debug.enabled()`
            #           actually good for?
            if cmk.utils.debug.enabled():
                raise
            return exc

        now = int(time.time())
        for tabr in table_rows:
            self._integrate_table_row(tabr)

            if is_legacy_plugin:
                # For old, legacy table plugins the retention intervals feature for HW/SW entries
                # is not supported because we do not have a clear, defined row identifier.
                # The consequences would be incomprehensible and non-transparent, eg. additional
                # history entries, delta tree calculation, filtering or merging does not work
                # reliable.
                continue

            self._may_add_cache_info(
                now=now,
                node_name=TABLE_KEY,
                path=tuple(tabr.path),
                raw_cache_info=raw_cache_info,
            )

        for attr in attributes:
            self._integrate_attributes(attr)
            self._may_add_cache_info(
                now=now,
                node_name=ATTRIBUTES_KEY,
                path=tuple(attr.path),
                raw_cache_info=raw_cache_info,
            )

        return None

    def _dispatch(
        self,
        intentory_items: Iterable[TableRow | Attributes],
    ) -> tuple[Sequence[TableRow], Sequence[Attributes]]:
        attributes = []
        table_rows = []
        for item in intentory_items:
            expected_class_name = self._class_mutex.setdefault(
                tuple(item.path), item.__class__.__name__
            )
            if item.__class__.__name__ != expected_class_name:
                raise TypeError(
                    f"Cannot create {item.__class__.__name__} at path {item.path}:"
                    f" this is a {expected_class_name} node."
                )
            if isinstance(item, Attributes):
                attributes.append(item)
            elif isinstance(item, TableRow):
                table_rows.append(item)
            else:
                raise NotImplementedError()  # can't happen, inventory results are filtered

        return table_rows, attributes

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

    def _may_add_cache_info(
        self,
        *,
        now: int,
        node_name: str,
        path: SDPath,
        raw_cache_info: RawCacheInfo | None,
    ) -> None:
        retention_key = (tuple(path), node_name)

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
        node_path, node_name = retention_key

        inv_node = self._inventory_tree.get_node(node_path)
        previous_node = previous_tree.get_node(node_path)

        if previous_node is None:
            previous_node = StructuredDataNode()

        if inv_node is None:
            inv_node = self._inventory_tree.setdefault_node(node_path)

        if node_name == ATTRIBUTES_KEY:
            return AttributesUpdater(
                retention_info,
                inv_node,
                previous_node,
            )

        if node_name == TABLE_KEY:
            return TableUpdater(
                retention_info,
                inv_node,
                previous_node,
            )

        raise NotImplementedError()

    # ---static data from config--------------------------------------------

    def add_cluster_property(self) -> None:
        self._add_cluster_property(is_cluster=False)


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
