#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
This module handles tree structures for HW/SW Inventory system and
structured monitoring data of Check_MK.
"""

from __future__ import annotations

import gzip
import io
import pprint
from collections import Counter
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final, Literal, NamedTuple, TypedDict

from cmk.utils import store
from cmk.utils.type_defs import HostName

# TODO key_columns should be a tuple[SDKey, ...]
# TODO Cleanup path in utils, base, gui, find ONE place (type defs or similar)

SDNodeName = str
SDPath = tuple[SDNodeName, ...]

SDKey = str
# TODO be more specific (None, str, float, int, DeltaValue:Tuple of previous)
SDValue = Any  # needs only to support __eq__
SDRowIdent = tuple[SDValue, ...]


class SDRawAttributes(TypedDict, total=False):
    Pairs: Mapping[SDKey, SDValue]
    Retentions: Mapping[SDKey, tuple[int, int, int]]


class SDRawTable(TypedDict, total=False):
    KeyColumns: Sequence[SDKey]
    Rows: Sequence[Mapping[SDKey, SDValue]]
    Retentions: Mapping[SDRowIdent, Mapping[SDKey, tuple[int, int, int]]]


class SDRawTree(TypedDict):
    Attributes: SDRawAttributes
    Table: SDRawTable
    Nodes: Mapping[SDNodeName, SDRawTree]


class SDRawDeltaAttributes(TypedDict, total=False):
    Pairs: Mapping[SDKey, tuple[SDValue, SDValue]]


class SDRawDeltaTable(TypedDict, total=False):
    KeyColumns: Sequence[SDKey]
    Rows: Sequence[Mapping[SDKey, tuple[SDValue, SDValue]]]


class SDRawDeltaTree(TypedDict):
    Attributes: SDRawDeltaAttributes
    Table: SDRawDeltaTable
    Nodes: Mapping[SDNodeName, SDRawDeltaTree]


class _RawIntervalFromConfigMandatory(TypedDict):
    interval: int
    visible_raw_path: str


class _RawIntervalFromConfig(_RawIntervalFromConfigMandatory, total=False):
    attributes: Literal["all"] | tuple[str, list[str]]
    columns: Literal["all"] | tuple[str, list[str]]


RawIntervalsFromConfig = Sequence[_RawIntervalFromConfig]


class RetentionIntervals(NamedTuple):
    cached_at: int
    cache_interval: int
    retention_interval: int

    @classmethod
    def make(cls, cache_info: tuple[int, int], interval: int) -> RetentionIntervals:
        return cls(cache_info[0], cache_info[1], interval)

    @property
    def valid_until(self) -> int:
        return self.cached_at + self.cache_interval

    @property
    def keep_until(self) -> int:
        return self.cached_at + self.cache_interval + self.retention_interval

    def serialize(self) -> tuple[int, int, int]:
        return self.cached_at, self.cache_interval, self.retention_interval

    @classmethod
    def deserialize(cls, raw_intervals: tuple[int, int, int]) -> RetentionIntervals:
        return cls(*raw_intervals)


RetentionIntervalsByKeys = dict[SDKey, RetentionIntervals]


@dataclass(frozen=True)
class UpdateResult:
    reasons_by_path: dict[SDPath, list[str]] = field(default_factory=dict)

    @property
    def save_tree(self) -> bool:
        return bool(self.reasons_by_path)

    @classmethod
    def from_results(cls, results: Iterable[UpdateResult]) -> UpdateResult:
        update_result = cls()
        for result in results:
            for path, reasons in result.reasons_by_path.items():
                update_result.reasons_by_path.setdefault(path, []).extend(reasons)
        return update_result

    def add_attr_reason(self, path: SDPath, name: str, iterable: Iterable[str]) -> None:
        self.reasons_by_path.setdefault(path, []).append(
            f"[Attributes] Added {name}: {', '.join(iterable)}"
        )

    def add_row_reason(
        self, path: SDPath, ident: SDRowIdent, name: str, iterable: Iterable[str]
    ) -> None:
        self.reasons_by_path.setdefault(path, []).append(
            f"[Table] '{', '.join(ident)}': Added {name}: {', '.join(iterable)}"
        )

    def __repr__(self) -> str:
        if not self.reasons_by_path:
            return "No tree update.\n"

        lines = ["Updated inventory tree:"]
        for path, reasons in self.reasons_by_path.items():
            lines.append(f"  Path '{' > '.join(path)}':")
            lines.extend(f"    {r}" for r in reasons)
        return "\n".join(lines) + "\n"


def parse_visible_raw_path(raw_path: str) -> SDPath:
    return tuple(part for part in raw_path.split(".") if part)


#   .--filters-------------------------------------------------------------.
#   |                       __ _ _ _                                       |
#   |                      / _(_) | |_ ___ _ __ ___                        |
#   |                     | |_| | | __/ _ \ '__/ __|                       |
#   |                     |  _| | | ||  __/ |  \__ \                       |
#   |                     |_| |_|_|\__\___|_|  |___/                       |
#   |                                                                      |
#   '----------------------------------------------------------------------'

# TODO filter table rows?


SDFilterFunc = Callable[[SDKey], bool]


class SDFilter(NamedTuple):
    path: SDPath
    filter_pairs: SDFilterFunc
    filter_columns: SDFilterFunc
    filter_nodes: SDFilterFunc


def make_filter_from_choice(choice: Literal["nothing", "all"] | Sequence[str]) -> SDFilterFunc:
    # TODO Improve:
    # For contact groups (via make_filter)
    #   - ('choices', ['some', 'keys'])
    #   - 'nothing' -> _use_nothing
    #   - None -> _use_all
    # For retention intervals (directly)
    #   - ('choices', ['some', 'keys'])
    #   - MISSING (see mk/base/agent_based/inventory.py::_get_intervals_from_config) -> _use_nothing
    #   - 'all' -> _use_all
    if choice == "nothing":
        return lambda k: False
    if choice == "all":
        return lambda k: True
    return lambda k: k in choice


# .
#   .--mutable tree--------------------------------------------------------.
#   |                      _        _     _        _                       |
#   |      _ __ ___  _   _| |_ __ _| |__ | | ___  | |_ _ __ ___  ___       |
#   |     | '_ ` _ \| | | | __/ _` | '_ \| |/ _ \ | __| '__/ _ \/ _ \      |
#   |     | | | | | | |_| | || (_| | |_) | |  __/ | |_| | |  __/  __/      |
#   |     |_| |_| |_|\__,_|\__\__,_|_.__/|_|\___|  \__|_|  \___|\___|      |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class MutableTree:
    def __init__(self, tree: StructuredDataNode | None = None) -> None:
        self.tree: Final = StructuredDataNode() if tree is None else tree

    def serialize(self) -> SDRawTree:
        return self.tree.serialize()

    def __bool__(self) -> bool:
        return bool(self.tree)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, (MutableTree, ImmutableTree)):
            raise TypeError(type(other))
        return self.tree == other.tree

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def add_pairs(
        self,
        *,
        path: list[str],
        pairs: Mapping[str, int | float | str | None],
    ) -> None:
        self.tree.setdefault_node(tuple(path)).attributes.add_pairs(pairs)

    def add_rows(
        self,
        *,
        path: list[str],
        key_columns: list[str],
        rows: Sequence[Mapping[str, int | float | str | None]],
    ) -> None:
        node = self.tree.setdefault_node(tuple(path))
        node.table.add_key_columns(sorted(key_columns))
        node.table.add_rows(rows)

    def update_pairs(
        self,
        now: int,
        path: SDPath,
        tree: ImmutableTree,
        filter_func: SDFilterFunc,
        inv_intervals: RetentionIntervals,
    ) -> UpdateResult:
        return self.tree.setdefault_node(path).attributes.update_from_previous(
            now,
            path,
            tree.get_tree(path).tree.attributes,
            filter_func,
            inv_intervals,
        )

    def update_rows(
        self,
        now: int,
        path: SDPath,
        tree: ImmutableTree,
        filter_func: SDFilterFunc,
        inv_intervals: RetentionIntervals,
    ) -> UpdateResult:
        return self.tree.setdefault_node(path).table.update_from_previous(
            now,
            path,
            tree.get_tree(path).tree.table,
            filter_func,
            inv_intervals,
        )

    def count_entries(self) -> int:
        return self.tree.count_entries()

    def get_attribute(self, path: SDPath, key: str) -> int | float | str | None:
        return (
            None if (node := self.tree.get_node(path)) is None else node.attributes.pairs.get(key)
        )

    def get_tree(self, path: SDPath) -> MutableTree:
        return MutableTree(self.tree.get_node(path))

    def has_table(self, path: SDPath) -> bool:
        return bool(self.tree.get_table(path))


# .
#   .--immutable tree------------------------------------------------------.
#   |          _                           _        _     _                |
#   |         (_)_ __ ___  _ __ ___  _   _| |_ __ _| |__ | | ___           |
#   |         | | '_ ` _ \| '_ ` _ \| | | | __/ _` | '_ \| |/ _ \          |
#   |         | | | | | | | | | | | | |_| | || (_| | |_) | |  __/          |
#   |         |_|_| |_| |_|_| |_| |_|\__,_|\__\__,_|_.__/|_|\___|          |
#   |                                                                      |
#   |                          _                                           |
#   |                         | |_ _ __ ___  ___                           |
#   |                         | __| '__/ _ \/ _ \                          |
#   |                         | |_| | |  __/  __/                          |
#   |                          \__|_|  \___|\___|                          |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def _deserialize_legacy_attributes(raw_pairs: Mapping[SDKey, SDValue]) -> Attributes:
    attributes = Attributes()
    attributes.add_pairs(raw_pairs)
    return attributes


def _get_default_key_columns(rows: Sequence[Mapping[SDKey, SDValue]]) -> Sequence[SDKey]:
    return sorted({k for r in rows for k in r})


def _deserialize_legacy_table(raw_rows: Sequence[Mapping[SDKey, SDValue]]) -> Table:
    table = Table(key_columns=list(_get_default_key_columns(raw_rows)))
    table.add_rows(raw_rows)
    return table


def _deserialize_legacy_node(path: SDPath, raw_tree: Mapping[str, object]) -> StructuredDataNode:
    raw_pairs: dict[SDKey, SDValue] = {}
    raw_tables: dict[SDPath, list[dict]] = {}
    raw_nodes: dict[SDPath, dict] = {}

    for key, value in raw_tree.items():
        if isinstance(value, dict):
            if not value:
                continue
            raw_nodes.setdefault((str(key),), value)

        elif isinstance(value, list):
            if not value:
                continue

            if all(not isinstance(v, (list, dict)) for row in value for v in row.values()):
                # Either we get:
                #   [
                #       {"column1": "value 11", "column2": "value 12",...},
                #       {"column1": "value 11", "column2": "value 12",...},
                #       ...
                #   ]
                # Or:
                #   [
                #       {"attr": "attr1", "table": [...], "node": {...}, "idx-node": [...]},
                #       ...
                #   ]
                raw_tables.setdefault((str(key),), value)
                continue

            for idx, entry in enumerate(value):
                raw_nodes.setdefault((str(key), str(idx)), entry)

        else:
            raw_pairs.setdefault(key, value)

    node = StructuredDataNode(
        path=path,
        attributes=_deserialize_legacy_attributes(raw_pairs),
    )

    for child_path, raw_rows in raw_tables.items():
        node.add_node(
            child_path,
            StructuredDataNode(table=_deserialize_legacy_table(raw_rows)),
        )

    for child_path, raw_node in raw_nodes.items():
        node.add_node(
            child_path,
            _deserialize_legacy_node(path + child_path, raw_node),
        )

    return node


def _filter_pairs(attributes: Attributes, filter_func: SDFilterFunc) -> Attributes:
    filtered = Attributes(retentions=attributes.retentions)
    filtered.add_pairs(_get_filtered_dict(attributes.pairs, filter_func))
    return filtered


def _filter_table(table: Table, filter_func: SDFilterFunc) -> Table:
    filtered = Table(key_columns=table.key_columns, retentions=table.retentions)
    for ident, row in table.rows_by_ident.items():
        filtered.add_row(ident, _get_filtered_dict(row, filter_func))
    return filtered


def _filter_node(node: StructuredDataNode, filters: Iterable[SDFilter]) -> StructuredDataNode:
    filtered = StructuredDataNode(path=node.path)

    for f in filters:
        # First check if node exists
        if (child := node.get_node(f.path)) is None:
            continue

        filtered_node = StructuredDataNode(
            path=f.path,
            attributes=_filter_pairs(child.attributes, f.filter_pairs),
            table=_filter_table(child.table, f.filter_columns),
        )
        for name, sub_node in child.nodes_by_name.items():
            # From GUI::permitted_paths: We always get a list of strs.
            if f.filter_nodes(str(name)):
                filtered_node.add_node((str(name),), sub_node)

        if filtered_node:
            filtered.add_node(f.path, filtered_node)

    return filtered


def _merge_attributes(left: Attributes, right: Attributes) -> Attributes:
    attributes = Attributes(retentions={**left.retentions, **right.retentions})
    attributes.add_pairs(left.pairs)
    attributes.add_pairs(right.pairs)
    return attributes


def _merge_tables_by_same_or_empty_key_columns(
    key_columns: Sequence[SDKey], left: Table, right: Table
) -> Table:
    table = Table(
        key_columns=list(key_columns),
        retentions={**left.retentions, **right.retentions},
    )

    compared_keys = _compare_dict_keys(old_dict=right.rows_by_ident, new_dict=left.rows_by_ident)

    for key in compared_keys.only_old:
        table.add_row(key, right.rows_by_ident[key])

    for key in compared_keys.both:
        table.add_row(key, {**left.rows_by_ident[key], **right.rows_by_ident[key]})

    for key in compared_keys.only_new:
        table.add_row(key, left.rows_by_ident[key])

    return table


def _merge_tables(left: Table, right: Table) -> Table:
    if left.key_columns and not right.key_columns:
        return _merge_tables_by_same_or_empty_key_columns(left.key_columns, left, right)

    if not left.key_columns and right.key_columns:
        return _merge_tables_by_same_or_empty_key_columns(right.key_columns, left, right)

    if left.key_columns == right.key_columns:
        return _merge_tables_by_same_or_empty_key_columns(left.key_columns, left, right)

    # Re-calculate row identifiers for legacy tables or inventory and status tables
    table = Table(
        key_columns=sorted(set(left.key_columns).intersection(right.key_columns)),
        retentions={**left.retentions, **right.retentions},
    )
    table.add_rows(list(left.rows_by_ident.values()))
    table.add_rows(list(right.rows_by_ident.values()))
    return table


def _merge_nodes(left: StructuredDataNode, right: StructuredDataNode) -> StructuredDataNode:
    node = StructuredDataNode(
        path=left.path,
        attributes=_merge_attributes(left.attributes, right.attributes),
        table=_merge_tables(left.table, right.table),
    )

    compared_keys = _compare_dict_keys(old_dict=right.nodes_by_name, new_dict=left.nodes_by_name)

    for key in compared_keys.only_old:
        node.add_node((key,), right.nodes_by_name[key])

    for key in compared_keys.both:
        node.add_node(
            (key,),
            _merge_nodes(left=left.nodes_by_name[key], right=right.nodes_by_name[key]),
        )

    for key in compared_keys.only_new:
        node.add_node((key,), left.nodes_by_name[key])

    return node


def _new_delta_tree_node(value: SDValue) -> tuple[None, SDValue]:
    return (None, value)


def _removed_delta_tree_node(value: SDValue) -> tuple[SDValue, None]:
    return (value, None)


def _changed_delta_tree_node(old_value: SDValue, new_value: SDValue) -> tuple[SDValue, SDValue]:
    return (old_value, new_value)


def _identical_delta_tree_node(value: SDValue) -> tuple[SDValue, SDValue]:
    return (value, value)


class ComparedDictResult(NamedTuple):
    result_dict: dict[SDKey, tuple[SDValue | None, SDValue | None]]
    has_changes: bool


def _compare_dicts(
    *, old_dict: Mapping, new_dict: Mapping, keep_identical: bool
) -> ComparedDictResult:
    """
    Format of compared entries:
      new:          {k: (None, new_value), ...}
      changed:      {k: (old_value, new_value), ...}
      removed:      {k: (old_value, None), ...}
      identical:    {k: (value, value), ...}
    """
    compared_keys = _compare_dict_keys(old_dict=old_dict, new_dict=new_dict)
    compared_dict: dict[SDKey, tuple[SDValue | None, SDValue | None]] = {}

    has_changes = False
    for k in compared_keys.both:
        if (new_value := new_dict[k]) != (old_value := old_dict[k]):
            compared_dict.setdefault(k, _changed_delta_tree_node(old_value, new_value))
            has_changes = True
        elif keep_identical:
            compared_dict.setdefault(k, _identical_delta_tree_node(old_value))

    compared_dict.update({k: _new_delta_tree_node(new_dict[k]) for k in compared_keys.only_new})
    compared_dict.update({k: _removed_delta_tree_node(old_dict[k]) for k in compared_keys.only_old})

    return ComparedDictResult(
        result_dict=compared_dict,
        has_changes=bool(has_changes or compared_keys.only_new or compared_keys.only_old),
    )


def _compare_attributes(left: Attributes, right: Attributes) -> DeltaAttributes:
    return DeltaAttributes(
        pairs=_compare_dicts(
            old_dict=right.pairs,
            new_dict=left.pairs,
            keep_identical=False,
        ).result_dict,
    )


def _compare_tables(left: Table, right: Table) -> DeltaTable:
    key_columns = sorted(set(left.key_columns).union(right.key_columns))
    compared_keys = _compare_dict_keys(old_dict=right._rows, new_dict=left._rows)

    delta_rows: list[dict[SDKey, tuple[SDValue | None, SDValue | None]]] = []

    for key in compared_keys.only_old:
        delta_rows.append({k: _removed_delta_tree_node(v) for k, v in right._rows[key].items()})

    for key in compared_keys.both:
        # Note: Rows which have at least one change also provide all table fields.
        # Example:
        # If the version of a package (below "Software > Packages") has changed from 1.0 to 2.0
        # then it would be very annoying if the rest of the row is not shown.
        if (
            compared_dict_result := _compare_dicts(
                old_dict=right._rows[key],
                new_dict=left._rows[key],
                keep_identical=True,
            )
        ).has_changes:
            delta_rows.append(compared_dict_result.result_dict)

    for key in compared_keys.only_new:
        delta_rows.append({k: _new_delta_tree_node(v) for k, v in left._rows[key].items()})

    return DeltaTable(
        key_columns=key_columns,
        rows=delta_rows,
    )


def _compare_nodes(left: StructuredDataNode, right: StructuredDataNode) -> DeltaStructuredDataNode:
    delta_nodes: dict[SDNodeName, DeltaStructuredDataNode] = {}

    compared_keys = _compare_dict_keys(old_dict=right.nodes_by_name, new_dict=left.nodes_by_name)

    for key in compared_keys.only_new:
        child_left = left.nodes_by_name[key]
        if child_left.count_entries():
            delta_nodes[key] = DeltaStructuredDataNode.make_from_node(
                node=child_left,
                encode_as=_new_delta_tree_node,
            )

    for key in compared_keys.both:
        child_left = left.nodes_by_name[key]
        child_right = right.nodes_by_name[key]
        if child_left == child_right:
            continue

        delta_node = _compare_nodes(child_left, child_right)
        if delta_node.get_stats():
            delta_nodes[key] = delta_node

    for key in compared_keys.only_old:
        child_right = right.nodes_by_name[key]
        if child_right.count_entries():
            delta_nodes[key] = DeltaStructuredDataNode.make_from_node(
                node=child_right,
                encode_as=_removed_delta_tree_node,
            )

    return DeltaStructuredDataNode(
        path=left.path,
        attributes=_compare_attributes(left.attributes, right.attributes),
        table=_compare_tables(left.table, right.table),
        nodes=delta_nodes,
    )


class ImmutableTree:
    def __init__(self, tree: StructuredDataNode | None = None) -> None:
        self.tree: Final = StructuredDataNode() if tree is None else tree

    @classmethod
    def deserialize(cls, raw_tree: Mapping) -> ImmutableTree:
        try:
            raw_attributes = raw_tree["Attributes"]
            raw_table = raw_tree["Table"]
            raw_nodes = raw_tree["Nodes"]
        except KeyError:
            return cls(_deserialize_legacy_node(path=tuple(), raw_tree=raw_tree))

        return cls(
            tree=StructuredDataNode.deserialize(
                path=tuple(),
                raw_attributes=raw_attributes,
                raw_table=raw_table,
                raw_nodes=raw_nodes,
            )
        )

    def serialize(self) -> SDRawTree:
        return self.tree.serialize()

    def __bool__(self) -> bool:
        return bool(self.tree)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, (MutableTree, ImmutableTree)):
            raise TypeError(type(other))
        return self.tree == other.tree

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def filter(self, filters: Iterable[SDFilter]) -> ImmutableTree:
        return ImmutableTree(_filter_node(self.tree, filters))

    def merge(self, rhs: ImmutableTree) -> ImmutableTree:
        return ImmutableTree(_merge_nodes(self.tree, rhs.tree))

    def difference(self, rhs: ImmutableTree) -> ImmutableDeltaTree:
        return ImmutableDeltaTree(_compare_nodes(self.tree, rhs.tree))

    def get_attribute(self, path: SDPath, key: str) -> int | float | str | None:
        return (
            None if (node := self.tree.get_node(path)) is None else node.attributes.pairs.get(key)
        )

    def get_rows(self, path: SDPath) -> Sequence[Mapping[SDKey, SDValue]]:
        return [] if (node := self.tree.get_node(path)) is None else node.table.rows

    def get_tree(self, path: SDPath) -> ImmutableTree:
        return ImmutableTree(self.tree.get_node(path))


# .
#   .--immutable delta tree------------------------------------------------.
#   |          _                           _        _     _                |
#   |         (_)_ __ ___  _ __ ___  _   _| |_ __ _| |__ | | ___           |
#   |         | | '_ ` _ \| '_ ` _ \| | | | __/ _` | '_ \| |/ _ \          |
#   |         | | | | | | | | | | | | |_| | || (_| | |_) | |  __/          |
#   |         |_|_| |_| |_|_| |_| |_|\__,_|\__\__,_|_.__/|_|\___|          |
#   |                                                                      |
#   |                  _      _ _          _                               |
#   |               __| | ___| | |_ __ _  | |_ _ __ ___  ___               |
#   |              / _` |/ _ \ | __/ _` | | __| '__/ _ \/ _ \              |
#   |             | (_| |  __/ | || (_| | | |_| | |  __/  __/              |
#   |              \__,_|\___|_|\__\__,_|  \__|_|  \___|\___|              |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def _filter_delta_attributes(
    delta_attributes: DeltaAttributes, filter_func: SDFilterFunc
) -> DeltaAttributes:
    return DeltaAttributes(pairs=_get_filtered_dict(delta_attributes.pairs, filter_func))


def _filter_delta_table(delta_table: DeltaTable, filter_func: SDFilterFunc) -> DeltaTable:
    return DeltaTable(
        key_columns=delta_table.key_columns,
        rows=[
            filtered_row
            for row in delta_table.rows
            if (filtered_row := _get_filtered_dict(row, filter_func))
        ],
    )


def _filter_delta_node(
    delta_tree: DeltaStructuredDataNode, filters: Iterable[SDFilter]
) -> DeltaStructuredDataNode:
    filtered = DeltaStructuredDataNode(path=delta_tree.path)

    for f in filters:
        # First check if node exists
        node = delta_tree.get_node(f.path)
        if node is None:
            continue

        if filtered_delta_node := DeltaStructuredDataNode(
            path=node.path,
            attributes=_filter_delta_attributes(node.attributes, f.filter_pairs),
            table=_filter_delta_table(node.table, f.filter_columns),
            nodes={
                name: child for name, child in node.nodes_by_name.items() if f.filter_nodes(name)
            },
        ):
            filtered.add_node(node.path, filtered_delta_node)

    return filtered


class ImmutableDeltaTree:
    def __init__(self, tree: DeltaStructuredDataNode | None = None) -> None:
        self.tree: Final = tree or DeltaStructuredDataNode()

    @classmethod
    def deserialize(cls, raw_tree: SDRawDeltaTree) -> ImmutableDeltaTree:
        return cls(DeltaStructuredDataNode.deserialize(path=tuple(), raw_tree=raw_tree))

    def serialize(self) -> SDRawDeltaTree:
        return self.tree.serialize()

    def __bool__(self) -> bool:
        return bool(self.tree)

    def filter(self, filters: Iterable[SDFilter]) -> ImmutableDeltaTree:
        return ImmutableDeltaTree(_filter_delta_node(self.tree, filters))

    def get_stats(self) -> _SDDeltaCounter:
        return self.tree.get_stats()

    def get_tree(self, path: SDPath) -> ImmutableDeltaTree:
        return ImmutableDeltaTree(self.tree.get_node(path))


# .
#   .--IO------------------------------------------------------------------.
#   |                              ___ ___                                 |
#   |                             |_ _/ _ \                                |
#   |                              | | | | |                               |
#   |                              | | |_| |                               |
#   |                             |___\___/                                |
#   |                                                                      |
#   '----------------------------------------------------------------------'


# TODO Centralize different stores and loaders of tree files:
#   - inventory/HOSTNAME, inventory/HOSTNAME.gz, inventory/.last
#   - inventory_archive/HOSTNAME/TIMESTAMP,
#   - inventory_delta_cache/HOSTNAME/TIMESTAMP_{TIMESTAMP,None}
#   - status_data/HOSTNAME, status_data/HOSTNAME.gz


def load_tree(filepath: Path) -> ImmutableTree:
    if raw_tree := store.load_object_from_file(filepath, default=None):
        return ImmutableTree.deserialize(raw_tree)
    return ImmutableTree()


class TreeStore:
    def __init__(self, tree_dir: Path | str) -> None:
        self._tree_dir = Path(tree_dir)
        self._last_filepath = Path(tree_dir) / ".last"

    def load(self, *, host_name: HostName) -> ImmutableTree:
        return load_tree(self._tree_file(host_name))

    def save(self, *, host_name: HostName, tree: MutableTree, pretty: bool = False) -> None:
        self._tree_dir.mkdir(parents=True, exist_ok=True)

        tree_file = self._tree_file(host_name)

        output = tree.serialize()
        store.save_object_to_file(tree_file, output, pretty=pretty)

        buf = io.BytesIO()
        with gzip.GzipFile(fileobj=buf, mode="wb") as f:
            f.write((repr(output) + "\n").encode("utf-8"))
        store.save_bytes_to_file(self._gz_file(host_name), buf.getvalue())

        # Inform Livestatus about the latest inventory update
        self._last_filepath.touch()

    def remove(self, *, host_name: HostName) -> None:
        self._tree_file(host_name).unlink(missing_ok=True)
        self._gz_file(host_name).unlink(missing_ok=True)

    def _tree_file(self, host_name: HostName) -> Path:
        return self._tree_dir / str(host_name)

    def _gz_file(self, host_name: HostName) -> Path:
        return self._tree_dir / f"{host_name}.gz"


class TreeOrArchiveStore(TreeStore):
    def __init__(self, tree_dir: Path | str, archive: Path | str) -> None:
        super().__init__(tree_dir)
        self._archive_dir = Path(archive)

    def load_previous(self, *, host_name: HostName) -> ImmutableTree:
        if (tree_file := self._tree_file(host_name=host_name)).exists():
            return load_tree(tree_file)

        try:
            latest_archive_tree_file = max(
                self._archive_host_dir(host_name).iterdir(), key=lambda tp: int(tp.name)
            )
        except (FileNotFoundError, ValueError):
            return ImmutableTree()

        return load_tree(latest_archive_tree_file)

    def _archive_host_dir(self, host_name: HostName) -> Path:
        return self._archive_dir / str(host_name)

    def archive(self, *, host_name: HostName) -> None:
        if not (tree_file := self._tree_file(host_name)).exists():
            return
        target_dir = self._archive_host_dir(host_name)
        target_dir.mkdir(parents=True, exist_ok=True)
        tree_file.rename(target_dir / str(int(tree_file.stat().st_mtime)))
        self._gz_file(host_name).unlink(missing_ok=True)


# .
#   .--tree----------------------------------------------------------------.
#   |                          _                                           |
#   |                         | |_ _ __ ___  ___                           |
#   |                         | __| '__/ _ \/ _ \                          |
#   |                         | |_| | |  __/  __/                          |
#   |                          \__|_|  \___|\___|                          |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class Attributes:
    def __init__(
        self,
        *,
        retentions: RetentionIntervalsByKeys | None = None,
    ) -> None:
        self.retentions = retentions if retentions else {}
        self._pairs: dict[SDKey, SDValue] = {}

    @property
    def pairs(self) -> Mapping[SDKey, SDValue]:
        return self._pairs

    #   ---common methods-------------------------------------------------------

    def __bool__(self) -> bool:
        return bool(self.pairs)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Attributes):
            raise TypeError(type(other))
        return self.pairs == other.pairs

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def count_entries(self) -> int:
        return len(self.pairs)

    #   ---attributes methods---------------------------------------------------

    def add_pairs(self, pairs: Mapping[SDKey, SDValue]) -> None:
        self._pairs.update(pairs)

    #   ---retentions-----------------------------------------------------------

    def update_from_previous(
        self,
        now: int,
        path: SDPath,
        other: Attributes,
        filter_func: SDFilterFunc,
        inv_intervals: RetentionIntervals,
    ) -> UpdateResult:
        compared_filtered_keys = _compare_dict_keys(
            old_dict=_get_filtered_dict(
                other.pairs,
                _make_retentions_filter_func(
                    filter_func=filter_func,
                    intervals_by_keys=other.retentions,
                    now=now,
                ),
            ),
            new_dict=_get_filtered_dict(self.pairs, filter_func),
        )

        pairs: dict[SDKey, SDValue] = {}
        retentions: RetentionIntervalsByKeys = {}
        for key in compared_filtered_keys.only_old:
            pairs.setdefault(key, other.pairs[key])
            retentions[key] = other.retentions[key]

        for key in compared_filtered_keys.both.union(compared_filtered_keys.only_new):
            retentions[key] = inv_intervals

        update_result = UpdateResult()
        if pairs:
            self.add_pairs(pairs)
            update_result.add_attr_reason(path, "pairs", pairs)

        if retentions:
            self.set_retentions(retentions)
            update_result.add_attr_reason(path, "intervals", retentions)

        return update_result

    def set_retentions(self, intervals_by_keys: RetentionIntervalsByKeys) -> None:
        self.retentions = intervals_by_keys

    def get_retention_intervals(self, key: SDKey) -> RetentionIntervals | None:
        return self.retentions.get(key)

    #   ---representation-------------------------------------------------------

    def __repr__(self) -> str:
        # Only used for repr/debug purposes
        return f"{self.__class__.__name__}({pprint.pformat(self.serialize())})"

    #   ---de/serializing-------------------------------------------------------

    def serialize(self) -> SDRawAttributes:
        raw_attributes: SDRawAttributes = {}
        if self._pairs:
            raw_attributes["Pairs"] = self._pairs

        if self.retentions:
            raw_attributes["Retentions"] = _serialize_retentions(self.retentions)
        return raw_attributes

    @classmethod
    def deserialize(cls, raw_attributes: SDRawAttributes) -> Attributes:
        attributes = cls(retentions=_deserialize_retentions(raw_attributes.get("Retentions")))
        attributes.add_pairs(raw_attributes.get("Pairs", {}))
        return attributes


# TODO Table: {IDENT: Attributes}?

TableRetentions = dict[SDRowIdent, RetentionIntervalsByKeys]


class Table:
    def __init__(
        self,
        *,
        key_columns: list[SDKey] | None = None,
        retentions: TableRetentions | None = None,
    ) -> None:
        self.key_columns = key_columns if key_columns else []
        self.retentions = retentions if retentions else {}
        self._rows: dict[SDRowIdent, dict[SDKey, SDValue]] = {}

    def add_key_columns(self, key_columns: Sequence[SDKey]) -> None:
        for key in key_columns:
            if key not in self.key_columns:
                self.key_columns.append(key)

    @property
    def rows(self) -> Sequence[Mapping[SDKey, SDValue]]:
        return list(self._rows.values())

    @property
    def rows_by_ident(self) -> Mapping[SDRowIdent, Mapping[SDKey, SDValue]]:
        return self._rows

    #   ---common methods-------------------------------------------------------

    def __bool__(self) -> bool:
        return bool(self._rows)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Table):
            raise TypeError(type(other))

        compared_keys = _compare_dict_keys(old_dict=other._rows, new_dict=self._rows)
        if compared_keys.only_old or compared_keys.only_new:
            return False

        for key in compared_keys.both:
            if self._rows[key] != other._rows[key]:
                return False

        return True

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def count_entries(self) -> int:
        return sum(map(len, self._rows.values()))

    #   ---table methods--------------------------------------------------------

    def add_rows(self, rows: Sequence[Mapping[str, int | float | str | None]]) -> None:
        for row in rows:
            self.add_row(self._make_row_ident(row), row)

    def _make_row_ident(self, row: Mapping[str, int | float | str | None]) -> SDRowIdent:
        return tuple(row[k] for k in self.key_columns if k in row)

    def add_row(self, ident: SDRowIdent, row: Mapping[str, int | float | str | None]) -> None:
        if row:
            self._rows.setdefault(ident, {}).update(row)

    #   ---retentions-----------------------------------------------------------

    def update_from_previous(  # pylint: disable=too-many-branches
        self,
        now: int,
        path: SDPath,
        other: Table,
        filter_func: SDFilterFunc,
        inv_intervals: RetentionIntervals,
    ) -> UpdateResult:
        self.add_key_columns(other.key_columns)

        old_filtered_rows = {
            ident: filtered_row
            for ident, row in other._rows.items()
            if (
                filtered_row := _get_filtered_dict(
                    row,
                    _make_retentions_filter_func(
                        filter_func=filter_func,
                        intervals_by_keys=other.retentions.get(ident),
                        now=now,
                    ),
                )
            )
        }
        self_filtered_rows = {
            ident: filtered_row
            for ident, row in self._rows.items()
            if (filtered_row := _get_filtered_dict(row, filter_func))
        }
        compared_filtered_idents = _compare_dict_keys(
            old_dict=old_filtered_rows,
            new_dict=self_filtered_rows,
        )

        retentions: TableRetentions = {}
        update_result = UpdateResult()
        for ident in compared_filtered_idents.only_old:
            old_row: dict[SDKey, SDValue] = {}
            for key, value in old_filtered_rows[ident].items():
                old_row.setdefault(key, value)
                retentions.setdefault(ident, {})[key] = other.retentions[ident][key]

            if old_row:
                # Update row with key column entries
                old_row.update({k: other._rows[ident][k] for k in other.key_columns})
                self.add_row(ident, old_row)
                update_result.add_row_reason(path, ident, "row", old_row)

        for ident in compared_filtered_idents.both:
            compared_filtered_keys = _compare_dict_keys(
                old_dict=old_filtered_rows[ident],
                new_dict=self_filtered_rows[ident],
            )
            row: dict[SDKey, SDValue] = {}
            for key in compared_filtered_keys.only_old:
                row.setdefault(key, other._rows[ident][key])
                retentions.setdefault(ident, {})[key] = other.retentions[ident][key]

            for key in compared_filtered_keys.both.union(compared_filtered_keys.only_new):
                retentions.setdefault(ident, {})[key] = inv_intervals

            if row:
                # Update row with key column entries
                row.update(
                    {
                        **{k: other._rows[ident][k] for k in other.key_columns},
                        **{k: self._rows[ident][k] for k in self.key_columns},
                    }
                )
                self.add_row(ident, row)
                update_result.add_row_reason(path, ident, "row", row)

        for ident in compared_filtered_idents.only_new:
            for key in self_filtered_rows[ident]:
                retentions.setdefault(ident, {})[key] = inv_intervals

        if retentions:
            self.set_retentions(retentions)
            for ident, intervals in retentions.items():
                update_result.add_row_reason(path, ident, "intervals", intervals)

        return update_result

    def set_retentions(self, table_retentions: TableRetentions) -> None:
        self.retentions = table_retentions

    def get_retention_intervals(
        self, key: SDKey, row: Mapping[SDKey, SDValue]
    ) -> RetentionIntervals | None:
        return self.retentions.get(self._make_row_ident(row), {}).get(key)

    #   ---representation-------------------------------------------------------

    def __repr__(self) -> str:
        # Only used for repr/debug purposes
        return f"{self.__class__.__name__}({pprint.pformat(self.serialize())})"

    #   ---de/serializing-------------------------------------------------------

    def serialize(self) -> SDRawTable:
        raw_table: SDRawTable = {}
        if self._rows:
            raw_table.update(
                {
                    "KeyColumns": self.key_columns,
                    "Rows": list(self._rows.values()),
                }
            )

        if self.retentions:
            raw_table["Retentions"] = {
                ident: _serialize_retentions(intervals)
                for ident, intervals in self.retentions.items()
            }
        return raw_table

    @classmethod
    def deserialize(cls, raw_table: SDRawTable) -> Table:
        rows = raw_table.get("Rows", [])
        if "KeyColumns" in raw_table:
            key_columns = raw_table["KeyColumns"]
        else:
            key_columns = _get_default_key_columns(rows)

        table = cls(
            key_columns=list(key_columns),
            retentions={
                ident: _deserialize_retentions(raw_intervals)
                for ident, raw_intervals in raw_table.get("Retentions", {}).items()
            },
        )
        table.add_rows(rows)
        return table


class StructuredDataNode:
    def __init__(
        self,
        *,
        path: SDPath | None = None,
        attributes: Attributes | None = None,
        table: Table | None = None,
    ) -> None:
        self.path = path if path else tuple()
        self.attributes = attributes or Attributes()
        self.table = table or Table()
        self._nodes: dict[SDNodeName, StructuredDataNode] = {}

    @property
    def nodes(self) -> Iterator[StructuredDataNode]:
        yield from self._nodes.values()

    @property
    def nodes_by_name(self) -> Mapping[SDNodeName, StructuredDataNode]:
        return self._nodes

    #   ---common methods-------------------------------------------------------

    def __bool__(self) -> bool:
        if self.attributes or self.table:
            return True

        for node in self._nodes.values():
            if node:
                return True

        return False

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, StructuredDataNode):
            raise TypeError(type(other))

        if self.attributes != other.attributes or self.table != other.table:
            return False

        compared_keys = _compare_dict_keys(old_dict=other._nodes, new_dict=self._nodes)
        if compared_keys.only_old or compared_keys.only_new:
            return False

        for key in compared_keys.both:
            if self._nodes[key] != other._nodes[key]:
                return False

        return True

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def count_entries(self) -> int:
        return sum(
            [
                self.attributes.count_entries(),
                self.table.count_entries(),
            ]
            + [node.count_entries() for node in self._nodes.values()]
        )

    #   ---node methods---------------------------------------------------------

    def setdefault_node(self, path: SDPath) -> StructuredDataNode:
        if not path:
            return self

        name = path[0]
        node = self._nodes.setdefault(name, StructuredDataNode(path=self.path + (name,)))
        return node.setdefault_node(path[1:])

    def add_node(self, path: SDPath, node: StructuredDataNode) -> None:
        if not path:
            return

        node_name = path[0]
        node_path = self.path + (path[0],)
        if len(path) == 1:
            if node_name in self._nodes:
                merge_node = self._nodes[node_name]
            else:
                merge_node = StructuredDataNode(path=node_path)
            self._nodes[node_name] = _merge_nodes(merge_node, node)
            return

        self._nodes.setdefault(node_name, StructuredDataNode(path=node_path)).add_node(
            path[1:], node
        )

    def get_node(self, path: SDPath) -> StructuredDataNode | None:
        if not path:
            return self
        return None if (node := self._nodes.get(path[0])) is None else node.get_node(path[1:])

    def get_table(self, path: SDPath) -> Table | None:
        return None if (node := self.get_node(path)) is None else node.table

    def get_attributes(self, path: SDPath) -> Attributes | None:
        return None if (node := self.get_node(path)) is None else node.attributes

    #   ---representation-------------------------------------------------------

    def __repr__(self) -> str:
        # Only used for repr/debug purposes
        return f"{self.__class__.__name__}({pprint.pformat(self.serialize())})"

    #   ---de/serializing-------------------------------------------------------

    def serialize(self) -> SDRawTree:
        return {
            "Attributes": self.attributes.serialize(),
            "Table": self.table.serialize(),
            "Nodes": {name: node.serialize() for name, node in self._nodes.items() if node},
        }

    @classmethod
    def deserialize(
        cls,
        *,
        path: SDPath,
        raw_attributes: SDRawAttributes,
        raw_table: SDRawTable,
        raw_nodes: Mapping[SDNodeName, SDRawTree],
    ) -> StructuredDataNode:
        node = cls(
            path=path,
            attributes=Attributes.deserialize(raw_attributes),
            table=Table.deserialize(raw_table),
        )

        for raw_name, raw_node in raw_nodes.items():
            node.add_node(
                (raw_name,),
                cls.deserialize(
                    path=path + (raw_name,),
                    raw_attributes=raw_node["Attributes"],
                    raw_table=raw_node["Table"],
                    raw_nodes=raw_node["Nodes"],
                ),
            )

        return node


# .
#   .--delta tree----------------------------------------------------------.
#   |                  _      _ _          _                               |
#   |               __| | ___| | |_ __ _  | |_ _ __ ___  ___               |
#   |              / _` |/ _ \ | __/ _` | | __| '__/ _ \/ _ \              |
#   |             | (_| |  __/ | || (_| | | |_| | |  __/  __/              |
#   |              \__,_|\___|_|\__\__,_|  \__|_|  \___|\___|              |
#   |                                                                      |
#   '----------------------------------------------------------------------'


_SDEncodeAs = Callable[[SDValue], tuple[SDValue | None, SDValue | None]]
_SDDeltaCounter = Counter[Literal["new", "changed", "removed"]]


def _merge_delta_attributes(left: DeltaAttributes, right: DeltaAttributes) -> DeltaAttributes:
    return DeltaAttributes(pairs={**left.pairs, **right.pairs})


def _merge_delta_table(left: DeltaTable, right: DeltaTable) -> DeltaTable:
    delta_key_columns = []
    for key_column in left.key_columns:
        if key_column not in delta_key_columns:
            delta_key_columns.append(key_column)
    for key_column in right.key_columns:
        if key_column not in delta_key_columns:
            delta_key_columns.append(key_column)

    delta_rows = []
    for row in left.rows:
        if row not in delta_rows:
            delta_rows.append(row)
    for row in right.rows:
        if row not in delta_rows:
            delta_rows.append(row)

    return DeltaTable(key_columns=delta_key_columns, rows=delta_rows)


def _merge_delta_nodes(
    left: DeltaStructuredDataNode, right: DeltaStructuredDataNode
) -> DeltaStructuredDataNode:
    delta_nodes = {}

    compared_keys = _compare_dict_keys(
        old_dict=left.nodes_by_name,
        new_dict=right.nodes_by_name,
    )

    for key in compared_keys.only_old:
        delta_nodes[key] = left.nodes_by_name[key]

    for key in compared_keys.both:
        delta_nodes[key] = _merge_delta_nodes(
            left.nodes_by_name[key],
            right.nodes_by_name[key],
        )

    for key in compared_keys.only_new:
        delta_nodes[key] = right.nodes_by_name[key]

    return DeltaStructuredDataNode(
        path=left.path,
        attributes=_merge_delta_attributes(left.attributes, right.attributes),
        table=_merge_delta_table(left.table, right.table),
        nodes=delta_nodes,
    )


def _count_dict_entries(dict_: Mapping[SDKey, tuple[SDValue, SDValue]]) -> _SDDeltaCounter:
    counter: _SDDeltaCounter = Counter()
    for value0, value1 in dict_.values():
        match [value0 is None, value1 is None]:
            case [True, False]:
                counter["new"] += 1
            case [False, True]:
                counter["removed"] += 1
            case [False, False] if value0 != value1:
                counter["changed"] += 1
    return counter


@dataclass(frozen=True, kw_only=True)
class DeltaAttributes:
    pairs: Mapping[SDKey, tuple[SDValue, SDValue]] = field(default_factory=dict)

    @classmethod
    def make_from_attributes(
        cls, *, attributes: Attributes, encode_as: _SDEncodeAs
    ) -> DeltaAttributes:
        return cls(pairs={key: encode_as(value) for key, value in attributes.pairs.items()})

    def __bool__(self) -> bool:
        return bool(self.pairs)

    def serialize(self) -> SDRawDeltaAttributes:
        return {"Pairs": self.pairs} if self.pairs else {}

    @classmethod
    def deserialize(cls, raw_attributes: SDRawDeltaAttributes) -> DeltaAttributes:
        return cls(pairs=raw_attributes.get("Pairs", {}))

    def get_stats(self) -> _SDDeltaCounter:
        return _count_dict_entries(self.pairs)


@dataclass(frozen=True, kw_only=True)
class DeltaTable:
    key_columns: Sequence[SDKey] = field(default_factory=list)
    rows: Sequence[Mapping[SDKey, tuple[SDValue, SDValue]]] = field(default_factory=list)

    @classmethod
    def make_from_table(cls, *, table: Table, encode_as: _SDEncodeAs) -> DeltaTable:
        return cls(
            key_columns=table.key_columns,
            rows=[{key: encode_as(value) for key, value in row.items()} for row in table.rows],
        )

    def __bool__(self) -> bool:
        return bool(self.rows)

    def serialize(self) -> SDRawDeltaTable:
        return {"KeyColumns": self.key_columns, "Rows": self.rows} if self.rows else {}

    @classmethod
    def deserialize(cls, raw_table: SDRawDeltaTable) -> DeltaTable:
        return cls(key_columns=raw_table.get("KeyColumns", []), rows=raw_table.get("Rows", []))

    def get_stats(self) -> _SDDeltaCounter:
        counter: _SDDeltaCounter = Counter()
        for row in self.rows:
            counter.update(_count_dict_entries(row))
        return counter


@dataclass(frozen=True, kw_only=True)
class DeltaStructuredDataNode:
    path: SDPath = ()
    attributes: DeltaAttributes = DeltaAttributes()
    table: DeltaTable = DeltaTable()
    # TODO Make nodes immutable
    nodes: dict[SDNodeName, DeltaStructuredDataNode] = field(default_factory=dict)

    @classmethod
    def make_from_node(
        cls, *, node: StructuredDataNode, encode_as: _SDEncodeAs
    ) -> DeltaStructuredDataNode:
        return cls(
            path=node.path,
            attributes=DeltaAttributes.make_from_attributes(
                attributes=node.attributes,
                encode_as=encode_as,
            ),
            table=DeltaTable.make_from_table(
                table=node.table,
                encode_as=encode_as,
            ),
            nodes={
                name: cls.make_from_node(
                    node=child,
                    encode_as=encode_as,
                )
                for name, child in node.nodes_by_name.items()
            },
        )

    def __bool__(self) -> bool:
        if self.attributes or self.table:
            return True

        for node in self.nodes.values():
            if node:
                return True

        return False

    def add_node(self, path: SDPath, node: DeltaStructuredDataNode) -> None:
        if not path:
            return

        node_name = path[0]
        node_path = self.path + (path[0],)
        if len(path) == 1:
            if node_name in self.nodes:
                merge_node = self.nodes[node_name]
            else:
                merge_node = DeltaStructuredDataNode(path=node_path)
            self.nodes[node_name] = _merge_delta_nodes(merge_node, node)
            return

        self.nodes.setdefault(node_name, DeltaStructuredDataNode(path=node_path)).add_node(
            path[1:], node
        )

    def get_node(self, path: SDPath) -> DeltaStructuredDataNode | None:
        if not path:
            return self
        node = self.nodes.get(path[0])
        return None if node is None else node.get_node(path[1:])

    @property
    def nodes_by_name(self) -> Mapping[SDNodeName, DeltaStructuredDataNode]:
        return self.nodes

    def serialize(self) -> SDRawDeltaTree:
        return {
            "Attributes": self.attributes.serialize(),
            "Table": self.table.serialize(),
            "Nodes": {edge: node.serialize() for edge, node in self.nodes.items() if node},
        }

    @classmethod
    def deserialize(cls, *, path: SDPath, raw_tree: SDRawDeltaTree) -> DeltaStructuredDataNode:
        return cls(
            path=path,
            attributes=DeltaAttributes.deserialize(raw_attributes=raw_tree["Attributes"]),
            table=DeltaTable.deserialize(raw_table=raw_tree["Table"]),
            nodes={
                raw_node_name: cls.deserialize(
                    path=path + (raw_node_name,),
                    raw_tree=raw_node,
                )
                for raw_node_name, raw_node in raw_tree["Nodes"].items()
            },
        )

    def get_stats(self) -> _SDDeltaCounter:
        counter: _SDDeltaCounter = Counter()
        counter.update(self.attributes.get_stats())
        counter.update(self.table.get_stats())
        for node in self.nodes.values():
            counter.update(node.get_stats())
        return counter


# .
#   .--helpers-------------------------------------------------------------.
#   |                  _          _                                        |
#   |                 | |__   ___| |_ __   ___ _ __ ___                    |
#   |                 | '_ \ / _ \ | '_ \ / _ \ '__/ __|                   |
#   |                 | | | |  __/ | |_) |  __/ |  \__ \                   |
#   |                 |_| |_|\___|_| .__/ \___|_|  |___/                   |
#   |                              |_|                                     |
#   '----------------------------------------------------------------------'


class ComparedDictKeys(NamedTuple):
    only_old: set
    both: set
    only_new: set


def _compare_dict_keys(*, old_dict: Mapping, new_dict: Mapping) -> ComparedDictKeys:
    """
    Returns the set relationships of the keys between two dictionaries:
    - relative complement of new_dict in old_dict
    - intersection of both
    - relative complement of old_dict in new_dict
    """
    old_keys, new_keys = set(old_dict), set(new_dict)
    return ComparedDictKeys(
        only_old=old_keys - new_keys,
        both=old_keys.intersection(new_keys),
        only_new=new_keys - old_keys,
    )


def _make_retentions_filter_func(
    *,
    filter_func: SDFilterFunc,
    intervals_by_keys: RetentionIntervalsByKeys | None,
    now: int,
) -> SDFilterFunc:
    return lambda k: bool(
        filter_func(k)
        and intervals_by_keys
        and (intervals := intervals_by_keys.get(k))
        and now <= intervals.keep_until
    )


def _get_filtered_dict(dict_: Mapping, filter_func: SDFilterFunc) -> dict:
    return {k: v for k, v in dict_.items() if filter_func(k)}


def _serialize_retentions(
    intervals_by_keys: RetentionIntervalsByKeys,
) -> Mapping[SDKey, tuple[int, int, int]]:
    return {key: intervals.serialize() for key, intervals in intervals_by_keys.items()}


def _deserialize_retentions(
    raw_intervals_by_keys: Mapping[SDKey, tuple[int, int, int]] | None,
) -> RetentionIntervalsByKeys:
    if not raw_intervals_by_keys:
        return {}
    return {
        key: RetentionIntervals.deserialize(intervals)
        for key, intervals in raw_intervals_by_keys.items()
    }
