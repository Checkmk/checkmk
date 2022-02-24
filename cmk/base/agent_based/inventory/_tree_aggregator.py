#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from typing import Iterable, List, Literal, NamedTuple, Optional, Sequence, Tuple, Union

import cmk.utils.debug
from cmk.utils.structured_data import ATTRIBUTES_KEY, StructuredDataNode, TABLE_KEY

from cmk.base.api.agent_based.inventory_classes import (
    AttrDict,
    Attributes,
    InventoryResult,
    TableRow,
)

from ._retentions import RawCacheInfo, RetentionsTracker


class InventoryTrees(NamedTuple):
    inventory: StructuredDataNode
    status_data: StructuredDataNode


class TreeAggregator:
    def __init__(self):
        self.trees = InventoryTrees(
            inventory=StructuredDataNode(),
            status_data=StructuredDataNode(),
        )
        self._class_mutex = {}

    def aggregate_results(
        self,
        *,
        inventory_generator: InventoryResult,
        retentions_tracker: RetentionsTracker,
        raw_cache_info: Optional[RawCacheInfo],
        is_legacy_plugin: bool,
    ) -> Optional[Exception]:

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

            retentions_tracker.may_add_cache_info(
                now=now,
                node_name=TABLE_KEY,
                path=tabr.path,
                raw_cache_info=raw_cache_info,
            )

        for attr in attributes:
            self._integrate_attributes(attr)
            retentions_tracker.may_add_cache_info(
                now=now,
                node_name=ATTRIBUTES_KEY,
                path=attr.path,
                raw_cache_info=raw_cache_info,
            )

        return None

    def _dispatch(
        self,
        intentory_items: Iterable[Union[TableRow, Attributes]],
    ) -> Tuple[Sequence[TableRow], Sequence[Attributes]]:
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
            node = self.trees.inventory.setdefault_node(attributes.path)
            node.attributes.add_pairs(attributes.inventory_attributes)

        if attributes.status_attributes:
            node = self.trees.status_data.setdefault_node(attributes.path)
            node.attributes.add_pairs(attributes.status_attributes)

    def _add_row(
        self,
        path: List[str],
        tree_name: Literal["inventory", "status_data"],
        key_columns: AttrDict,
        columns: AttrDict,
    ) -> None:
        table = getattr(self.trees, tree_name).setdefault_node(path).table
        table.add_key_columns(sorted(key_columns))
        table.add_rows([{**key_columns, **columns}])

    def _integrate_table_row(self, table_row: TableRow) -> None:
        # do this always, it sets key_columns!
        self._add_row(
            table_row.path,
            "inventory",
            table_row.key_columns,
            table_row.inventory_columns,
        )

        # do this only if not empty:
        if table_row.status_columns:
            self._add_row(
                table_row.path,
                "status_data",
                table_row.key_columns,
                table_row.status_columns,
            )
