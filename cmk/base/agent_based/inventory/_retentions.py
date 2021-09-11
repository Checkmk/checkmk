#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Data for the HW/SW Inventory has a validity period (live data or persisted).
With the retention intervals configuration you can keep specific attributes or
table columns longer than their validity period.

1.) RetentionsTracker: Collect cache infos from plugins if and only if there
    is a configured 'path-to-node' + attributes/table keys entry in the ruleset
    'Retention intervals for HW/SW inventory entities'.

2.) Retentions: Process collected cache infos - handle the following four cases via
    AttributesUpdater, TableUpdater:

      previous node | inv node | retention intervals from
    -----------------------------------------------------------------------------------
      no            | no       | None
      no            | yes      | inv_node keys
      yes           | no       | previous_node keys
      yes           | yes      | previous_node keys + inv_node keys

    - If there's no previous node then filtered keys + intervals of current node is stored
      (like a first run) and will be checked against the future node in the next run.
    - if there's a previous node then check if the data is recent enough and merge
      attributes/tables data from the previous node with the current one.
      'Recent enough' means: now <= cache_at + cache_interval + retention_interval
      where cache_at, cache_interval: from agent data (or set to (now, 0) if not persisted),
            retention_interval: configured in the above ruleset
"""

# TODO
# - GUI: differentiate between taken over values (from previous node) and avail values
#        from plugins: In later case: do not show 'x left'.

from __future__ import annotations

from typing import Dict, List, NamedTuple, Optional, Tuple, Union

from cmk.utils.structured_data import (
    ATTRIBUTES_KEY,
    make_filter_from_choice,
    parse_visible_raw_path,
    RawIntervalsFromConfig,
    RetentionIntervals,
    SDFilterFunc,
    SDNodePath,
    SDPath,
    StructuredDataNode,
    TABLE_KEY,
    UpdateResult,
)

RawCacheInfo = Tuple[int, int]
RawChoicesFromConfig = Union[Tuple[str, List[str]], str]


class IntervalFromConfig(NamedTuple):
    choices: RawChoicesFromConfig
    interval: int


class RetentionInfo(NamedTuple):
    filter_func: SDFilterFunc
    intervals: RetentionIntervals


RetentionKey = Tuple[SDNodePath, str]
RetentionInfos = Dict[RetentionKey, RetentionInfo]
IntervalsFromConfig = Dict[RetentionKey, IntervalFromConfig]

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
#   .--Retentions----------------------------------------------------------.
#   |            ____      _             _   _                             |
#   |           |  _ \ ___| |_ ___ _ __ | |_(_) ___  _ __  ___             |
#   |           | |_) / _ \ __/ _ \ '_ \| __| |/ _ \| '_ \/ __|            |
#   |           |  _ <  __/ ||  __/ | | | |_| | (_) | | | \__ \            |
#   |           |_| \_\___|\__\___|_| |_|\__|_|\___/|_| |_|___/            |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class RetentionsTracker:
    def __init__(self, raw_intervals_from_config: RawIntervalsFromConfig) -> None:
        self._from_config = _get_intervals_from_config(raw_intervals_from_config)
        self.retention_infos: RetentionInfos = {}

    def may_add_cache_info(
        self,
        *,
        now: int,
        node_name: str,
        path: SDPath,
        raw_cache_info: Optional[RawCacheInfo],
    ) -> None:
        retention_key = (tuple(path), node_name)

        if (from_config := self._from_config.get(retention_key)) is None:
            return

        intervals = self._make_intervals(now, raw_cache_info, from_config.interval)
        filter_func = make_filter_from_choice(from_config.choices)

        self.retention_infos.setdefault(retention_key, RetentionInfo(filter_func, intervals))

    @staticmethod
    def _make_intervals(
        now: int,
        raw_cache_info: Optional[RawCacheInfo],
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


class Retentions:
    def __init__(
        self,
        tracker: RetentionsTracker,
        inv_tree: StructuredDataNode,
        do_update: bool,
    ) -> None:
        self._tracker = tracker
        self._inv_tree = inv_tree
        self._do_update = do_update

    def may_update(self, now: int, previous_tree: StructuredDataNode) -> UpdateResult:
        if not self._do_update:
            self._inv_tree.remove_retentions()
            return UpdateResult(save_tree=False, reason="No retention intervals found.")

        results = []
        for retention_key, retention_info in self._tracker.retention_infos.items():
            updater = self._make_updater(retention_key, retention_info, previous_tree)
            results.append(updater.filter_and_merge(now))

        return UpdateResult(
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
        path = list(node_path)

        inv_node = self._inv_tree.get_node(path)
        previous_node = previous_tree.get_node(path)

        if previous_node is None:
            previous_node = StructuredDataNode()

        if inv_node is None:
            inv_node = self._inv_tree.setdefault_node(path)

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


#   ---Updater--------------------------------------------------------------


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
