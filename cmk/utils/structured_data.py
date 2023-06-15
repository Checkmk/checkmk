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
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final, Literal, NamedTuple, overload, TypedDict

from cmk.utils import store
from cmk.utils.hostaddress import HostName

# TODO key_columns should be a tuple[SDKey, ...]
# TODO Cleanup path in utils, base, gui, find ONE place (type defs or similar)

SDNodeName = str
SDPath = tuple[SDNodeName, ...]

SDKey = str
SDValue = int | float | str | bool | None
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


class RetentionInterval(NamedTuple):
    cached_at: int
    cache_interval: int
    retention_interval: int

    @classmethod
    def make(cls, cache_info: tuple[int, int], interval: int) -> RetentionInterval:
        return cls(cache_info[0], cache_info[1], interval)

    @property
    def keep_until(self) -> int:
        return self.cached_at + self.cache_interval + self.retention_interval

    def serialize(self) -> tuple[int, int, int]:
        return self.cached_at, self.cache_interval, self.retention_interval

    @classmethod
    def deserialize(cls, raw_interval: tuple[int, int, int]) -> RetentionInterval:
        return cls(*raw_interval)


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
            f"[Table] '{', '.join(map(str, ident))}': Added {name}: {', '.join(iterable)}"
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


def make_filter_func(choice: Literal["nothing", "all"] | Sequence[str]) -> SDFilterFunc:
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


class SDFilter(NamedTuple):
    path: SDPath
    filter_pairs: SDFilterFunc
    filter_columns: SDFilterFunc
    filter_nodes: SDFilterFunc

    @classmethod
    def from_choices(
        cls,
        *,
        path: SDPath,
        choice_pairs: Literal["nothing", "all"] | Sequence[str],
        choice_columns: Literal["nothing", "all"] | Sequence[str],
        choice_nodes: Literal["nothing", "all"] | Sequence[str],
    ) -> SDFilter:
        return cls(
            path=path,
            filter_pairs=make_filter_func(choice_pairs),
            filter_columns=make_filter_func(choice_columns),
            filter_nodes=make_filter_func(choice_nodes),
        )


@dataclass(frozen=True, kw_only=True)
class _FilterTree:
    nodes: dict[SDNodeName, _FilterTree] = field(default_factory=dict)
    filters: list[SDFilter] = field(default_factory=list)


def _make_filter_tree(filters: Iterable[SDFilter]) -> _FilterTree:
    filter_tree = _FilterTree()
    for f in filters:
        if not f.path:
            filter_tree.filters.append(f)
            continue

        node = filter_tree.nodes.setdefault(f.path[0], _FilterTree())
        for name in f.path[1:]:
            node = node.nodes.setdefault(name, _FilterTree())

        node.filters.append(f)
    return filter_tree


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
    def __init__(self, node: StructuredDataNode | None = None) -> None:
        self.node: Final = StructuredDataNode() if node is None else node

    def __len__(self) -> int:
        return len(self.node)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, (MutableTree, ImmutableTree)):
            raise TypeError(type(other))
        return self.node == other.node

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def add_pairs(self, *, path: SDPath, pairs: Mapping[SDKey, SDValue]) -> None:
        self.node.setdefault_node(tuple(path)).attributes.add_pairs(pairs)

    def add_rows(
        self, *, path: SDPath, key_columns: Sequence[SDKey], rows: Sequence[Mapping[SDKey, SDValue]]
    ) -> None:
        node = self.node.setdefault_node(tuple(path))
        node.table.add_key_columns(sorted(key_columns))
        node.table.add_rows(rows)

    def update_pairs(
        self,
        now: int,
        path: SDPath,
        previous_tree: ImmutableTree,
        filter_func: SDFilterFunc,
        retention_interval: RetentionInterval,
    ) -> UpdateResult:
        return self.node.setdefault_node(path).attributes.update_pairs(
            now,
            path,
            previous_tree.get_tree(path).node.attributes,
            filter_func,
            retention_interval,
        )

    def update_rows(
        self,
        now: int,
        path: SDPath,
        previous_tree: ImmutableTree,
        filter_func: SDFilterFunc,
        retention_interval: RetentionInterval,
    ) -> UpdateResult:
        return self.node.setdefault_node(path).table.update_rows(
            now,
            path,
            previous_tree.get_tree(path).node.table,
            filter_func,
            retention_interval,
        )

    def get_attribute(self, path: SDPath, key: SDKey) -> SDValue:
        return (
            None if (node := self.node.get_node(path)) is None else node.attributes.pairs.get(key)
        )

    def get_tree(self, path: SDPath) -> MutableTree:
        return MutableTree(self.node.get_node(path))

    def has_table(self, path: SDPath) -> bool:
        return bool(MutableTree(self.node.get_node(path)).node.table)

    def serialize(self) -> SDRawTree:
        return self.node.serialize()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({pprint.pformat(self.node.to_raw())})"


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


def _deserialize_legacy_node(  # pylint: disable=too-many-branches
    path: SDPath,
    raw_tree: Mapping[str, object],
    raw_rows: Sequence[Mapping] | None = None,
) -> StructuredDataNode:
    raw_pairs: dict[SDKey, SDValue] = {}
    raw_tables: dict[SDNodeName, list[dict]] = {}
    raw_nodes: dict[SDNodeName, dict] = {}

    for key, value in raw_tree.items():
        if isinstance(value, dict):
            if not value:
                continue
            raw_nodes.setdefault(key, value)

        elif isinstance(value, list):
            if not value:
                continue

            if all(isinstance(v, (int, float, str, bool)) or v is None for v in value):
                if w := ", ".join(str(v) for v in value if v):
                    raw_pairs.setdefault(key, w)
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
                raw_tables.setdefault(key, value)
                continue

            for idx, entry in enumerate(value):
                raw_nodes.setdefault(key, {}).setdefault(str(idx), entry)

        elif isinstance(value, (int, float, str, bool)) or value is None:
            raw_pairs.setdefault(key, value)

        else:
            raise TypeError(value)

    return StructuredDataNode(
        path=path,
        attributes=_deserialize_legacy_attributes(raw_pairs),
        table=_deserialize_legacy_table(raw_rows) if raw_rows else Table(),
        nodes={
            **{
                name: _deserialize_legacy_node(
                    path + (name,),
                    raw_node,
                    raw_tables.get(name),
                )
                for name, raw_node in raw_nodes.items()
            },
            **{
                name: StructuredDataNode(
                    path=path + (name,),
                    table=_deserialize_legacy_table(raw_rows),
                )
                for name in set(raw_tables) - set(raw_nodes)
                if (raw_rows := raw_tables[name])
            },
        },
    )


def _filter_attributes(attributes: Attributes, filter_funcs: Sequence[SDFilterFunc]) -> Attributes:
    filtered = Attributes(retentions=attributes.retentions)
    if not filter_funcs:
        filtered.add_pairs(attributes.pairs)
        return filtered

    for filter_func in filter_funcs:
        filtered.add_pairs(_get_filtered_dict(attributes.pairs, filter_func))
    return filtered


def _filter_table(table: Table, filter_funcs: Sequence[SDFilterFunc]) -> Table:
    filtered = Table(key_columns=table.key_columns, retentions=table.retentions)
    for ident, row in table.rows_by_ident.items():
        if not filter_funcs:
            filtered.add_row(ident, row)
            continue

        for filter_func in filter_funcs:
            filtered.add_row(ident, _get_filtered_dict(row, filter_func))
    return filtered


def _filter_node(node: StructuredDataNode, filter_tree: _FilterTree) -> StructuredDataNode:
    filtered_nodes: dict[SDNodeName, StructuredDataNode] = {}
    for name in set(
        name for name in node.nodes_by_name for f in filter_tree.filters if f.filter_nodes(name)
    ).union(filter_tree.nodes):
        if filtered_node := _filter_node(
            node.nodes_by_name.get(name, StructuredDataNode(path=node.path + (name,))),
            filter_tree.nodes.get(name, _FilterTree()),
        ):
            filtered_nodes.setdefault(name, filtered_node)

    return StructuredDataNode(
        path=node.path,
        attributes=(
            _filter_attributes(node.attributes, [f.filter_pairs for f in filter_tree.filters])
        ),
        table=_filter_table(node.table, [f.filter_columns for f in filter_tree.filters]),
        nodes=filtered_nodes,
    )


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

    compared_keys = _compare_dict_keys(
        left=set(right.rows_by_ident),
        right=set(left.rows_by_ident),
    )

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
    compared_keys = _compare_dict_keys(
        left=set(right.nodes_by_name),
        right=set(left.nodes_by_name),
    )

    nodes: dict[SDNodeName, StructuredDataNode] = {}
    for key in compared_keys.only_old:
        nodes[key] = right.nodes_by_name[key]

    for key in compared_keys.both:
        nodes[key] = _merge_nodes(left=left.nodes_by_name[key], right=right.nodes_by_name[key])

    for key in compared_keys.only_new:
        nodes[key] = left.nodes_by_name[key]

    return StructuredDataNode(
        path=left.path,
        attributes=_merge_attributes(left.attributes, right.attributes),
        table=_merge_tables(left.table, right.table),
        nodes=nodes,
    )


def _encode_as_new(value: SDValue) -> tuple[None, SDValue]:
    return (None, value)


def _encode_as_removed(value: SDValue) -> tuple[SDValue, None]:
    return (value, None)


class ComparedDictResult(NamedTuple):
    result_dict: dict[SDKey, tuple[SDValue, SDValue]]
    has_changes: bool


def _compare_dicts(*, left: Mapping, right: Mapping, keep_identical: bool) -> ComparedDictResult:
    """
    Format of compared entries:
      new:          {k: (None, new_value), ...}
      changed:      {k: (old_value, new_value), ...}
      removed:      {k: (old_value, None), ...}
      identical:    {k: (value, value), ...}
    """
    compared_keys = _compare_dict_keys(left=set(left), right=set(right))
    compared_dict: dict[SDKey, tuple[SDValue, SDValue]] = {}

    has_changes = False
    for k in compared_keys.both:
        if (new_value := right[k]) != (old_value := left[k]):
            compared_dict.setdefault(k, (old_value, new_value))
            has_changes = True
        elif keep_identical:
            compared_dict.setdefault(k, (old_value, old_value))

    compared_dict.update({k: _encode_as_new(right[k]) for k in compared_keys.only_new})
    compared_dict.update({k: _encode_as_removed(left[k]) for k in compared_keys.only_old})

    return ComparedDictResult(
        result_dict=compared_dict,
        has_changes=bool(has_changes or compared_keys.only_new or compared_keys.only_old),
    )


def _compare_attributes(left: Attributes, right: Attributes) -> DeltaAttributes:
    return DeltaAttributes(
        pairs=_compare_dicts(
            left=right.pairs,
            right=left.pairs,
            keep_identical=False,
        ).result_dict,
    )


def _compare_tables(left: Table, right: Table) -> DeltaTable:
    key_columns = sorted(set(left.key_columns).union(right.key_columns))
    compared_keys = _compare_dict_keys(
        left=set(right.rows_by_ident),
        right=set(left.rows_by_ident),
    )

    delta_rows: list[dict[SDKey, tuple[SDValue, SDValue]]] = []

    for key in compared_keys.only_old:
        delta_rows.append({k: _encode_as_removed(v) for k, v in right.rows_by_ident[key].items()})

    for key in compared_keys.both:
        # Note: Rows which have at least one change also provide all table fields.
        # Example:
        # If the version of a package (below "Software > Packages") has changed from 1.0 to 2.0
        # then it would be very annoying if the rest of the row is not shown.
        if (
            compared_dict_result := _compare_dicts(
                left=right.rows_by_ident[key],
                right=left.rows_by_ident[key],
                keep_identical=True,
            )
        ).has_changes:
            delta_rows.append(compared_dict_result.result_dict)

    for key in compared_keys.only_new:
        delta_rows.append({k: _encode_as_new(v) for k, v in left.rows_by_ident[key].items()})

    return DeltaTable(
        key_columns=key_columns,
        rows=delta_rows,
    )


def _compare_nodes(left: StructuredDataNode, right: StructuredDataNode) -> DeltaStructuredDataNode:
    delta_nodes: dict[SDNodeName, DeltaStructuredDataNode] = {}

    compared_keys = _compare_dict_keys(
        left=set(right.nodes_by_name),
        right=set(left.nodes_by_name),
    )

    for key in compared_keys.only_new:
        if child_left := left.nodes_by_name[key]:
            delta_nodes[key] = DeltaStructuredDataNode.make_from_node(
                node=child_left,
                encode_as=_encode_as_new,
            )

    for key in compared_keys.both:
        if (child_left := left.nodes_by_name[key]) == (child_right := right.nodes_by_name[key]):
            continue

        delta_node = _compare_nodes(child_left, child_right)
        if delta_node.get_stats():
            delta_nodes[key] = delta_node

    for key in compared_keys.only_old:
        if child_right := right.nodes_by_name[key]:
            delta_nodes[key] = DeltaStructuredDataNode.make_from_node(
                node=child_right,
                encode_as=_encode_as_removed,
            )

    return DeltaStructuredDataNode(
        path=left.path,
        attributes=_compare_attributes(left.attributes, right.attributes),
        table=_compare_tables(left.table, right.table),
        nodes_by_name=delta_nodes,
    )


@dataclass(frozen=True, kw_only=True)
class ImmutableAttributes:
    pairs: Mapping[SDKey, SDValue] = field(default_factory=dict)
    retentions: Mapping[SDKey, RetentionInterval] = field(default_factory=dict)

    def __len__(self) -> int:
        # The attribute 'pairs' is decisive. Other attributes like 'retentions' have no impact
        # if there are no pairs.
        return len(self.pairs)


@dataclass(frozen=True, kw_only=True)
class ImmutableTable:
    key_columns: Sequence[SDKey] = field(default_factory=list)
    rows_by_ident: Mapping[SDRowIdent, Mapping[SDKey, SDValue]] = field(default_factory=dict)
    retentions: Mapping[SDRowIdent, Mapping[SDKey, RetentionInterval]] = field(default_factory=dict)

    def __len__(self) -> int:
        # The attribute 'rows' is decisive. Other attributes like 'key_columns' or 'retentions'
        # have no impact if there are no rows.
        return sum(map(len, self.rows_by_ident.values()))

    @property
    def rows(self) -> Sequence[Mapping[SDKey, SDValue]]:
        return list(self.rows_by_ident.values())


class ImmutableTree:
    def __init__(self, node: StructuredDataNode | None = None) -> None:
        self.attributes: Final = (
            ImmutableAttributes()
            if node is None
            else ImmutableAttributes(
                pairs=node.attributes.pairs,
                retentions=node.attributes.retentions,
            )
        )
        self.table: Final = (
            ImmutableTable()
            if node is None
            else ImmutableTable(
                key_columns=node.table.key_columns,
                rows_by_ident=node.table.rows_by_ident,
                retentions=node.table.retentions,
            )
        )
        self.node: Final[StructuredDataNode] = StructuredDataNode() if node is None else node
        self.path: Final = () if node is None else node.path

    def __len__(self) -> int:
        return len(self.node)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, (MutableTree, ImmutableTree)):
            raise TypeError(type(other))
        return self.node == other.node

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    @property
    def nodes_by_name(self) -> Mapping[SDNodeName, ImmutableTree]:
        return {name: ImmutableTree(node) for name, node in self.node.nodes_by_name.items()}

    def filter(self, filters: Iterable[SDFilter]) -> ImmutableTree:
        return ImmutableTree(_filter_node(self.node, _make_filter_tree(filters)))

    def merge(self, rhs: ImmutableTree) -> ImmutableTree:
        return ImmutableTree(_merge_nodes(self.node, rhs.node))

    def difference(self, rhs: ImmutableTree) -> ImmutableDeltaTree:
        return ImmutableDeltaTree(_compare_nodes(self.node, rhs.node))

    def get_attribute(self, path: SDPath, key: SDKey) -> SDValue:
        return (
            None if (node := self.node.get_node(path)) is None else node.attributes.pairs.get(key)
        )

    def get_rows(self, path: SDPath) -> Sequence[Mapping[SDKey, SDValue]]:
        return [] if (node := self.node.get_node(path)) is None else node.table.rows

    def get_tree(self, path: SDPath) -> ImmutableTree:
        return ImmutableTree(self.node.get_node(path))

    @classmethod
    def deserialize(cls, raw_tree: Mapping) -> ImmutableTree:
        try:
            raw_attributes = raw_tree["Attributes"]
            raw_table = raw_tree["Table"]
            raw_nodes = raw_tree["Nodes"]
        except KeyError:
            return cls(_deserialize_legacy_node(path=tuple(), raw_tree=raw_tree))

        return cls(
            node=StructuredDataNode.deserialize(
                path=tuple(),
                raw_attributes=raw_attributes,
                raw_table=raw_table,
                raw_nodes=raw_nodes,
            )
        )

    def serialize(self) -> SDRawTree:
        return self.node.serialize()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({pprint.pformat(self.node.to_raw())})"


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
    delta_attributes: DeltaAttributes, filter_funcs: Sequence[SDFilterFunc]
) -> DeltaAttributes:
    if not filter_funcs:
        return DeltaAttributes(pairs=delta_attributes.pairs)

    filtered_pairs: dict[SDKey, tuple[SDValue, SDValue]] = {}
    for filter_func in filter_funcs:
        filtered_pairs.update(_get_filtered_dict(delta_attributes.pairs, filter_func))
    return DeltaAttributes(pairs=filtered_pairs)


def _filter_delta_table(
    delta_table: DeltaTable, filter_funcs: Sequence[SDFilterFunc]
) -> DeltaTable:
    if not filter_funcs:
        return DeltaTable(key_columns=delta_table.key_columns, rows=delta_table.rows)

    filtered_rows: list[dict[SDKey, tuple[SDValue, SDValue]]] = []
    for row in delta_table.rows:
        filtered_row: dict[SDKey, tuple[SDValue, SDValue]] = {}
        for filter_func in filter_funcs:
            filtered_row.update(_get_filtered_dict(row, filter_func))
        if filtered_row:
            filtered_rows.append(filtered_row)
    return DeltaTable(key_columns=delta_table.key_columns, rows=filtered_rows)


def _filter_delta_node(
    delta_node: DeltaStructuredDataNode, filter_tree: _FilterTree
) -> DeltaStructuredDataNode:
    filtered_nodes: dict[SDNodeName, DeltaStructuredDataNode] = {}
    for name in set(
        name
        for name in delta_node.nodes_by_name
        for f in filter_tree.filters
        if f.filter_nodes(name)
    ).union(filter_tree.nodes):
        if filtered_node := _filter_delta_node(
            delta_node.nodes_by_name.get(
                name, DeltaStructuredDataNode(path=delta_node.path + (name,))
            ),
            filter_tree.nodes.get(name, _FilterTree()),
        ):
            filtered_nodes.setdefault(name, filtered_node)

    return DeltaStructuredDataNode(
        path=delta_node.path,
        attributes=(
            _filter_delta_attributes(
                delta_node.attributes, [f.filter_pairs for f in filter_tree.filters]
            )
        ),
        table=_filter_delta_table(
            delta_node.table, [f.filter_columns for f in filter_tree.filters]
        ),
        nodes_by_name=filtered_nodes,
    )


@dataclass(frozen=True, kw_only=True)
class ImmutableDeltaAttributes:
    pairs: Mapping[SDKey, tuple[SDValue, SDValue]] = field(default_factory=dict)


@dataclass(frozen=True, kw_only=True)
class ImmutableDeltaTable:
    key_columns: Sequence[SDKey] = field(default_factory=list)
    rows: Sequence[Mapping[SDKey, tuple[SDValue, SDValue]]] = field(default_factory=list)


class ImmutableDeltaTree:
    def __init__(self, node: DeltaStructuredDataNode | None = None) -> None:
        self.attributes: Final = (
            ImmutableDeltaAttributes()
            if node is None
            else ImmutableDeltaAttributes(pairs=node.attributes.pairs)
        )
        self.table: Final = (
            ImmutableDeltaTable()
            if node is None
            else ImmutableDeltaTable(key_columns=node.table.key_columns, rows=node.table.rows)
        )
        self.node: Final = DeltaStructuredDataNode() if node is None else node
        self.path: Final = () if node is None else node.path

    def __len__(self) -> int:
        return len(self.node)

    @property
    def nodes_by_name(self) -> Mapping[SDNodeName, ImmutableDeltaTree]:
        return {name: ImmutableDeltaTree(node) for name, node in self.node.nodes_by_name.items()}

    def filter(self, filters: Iterable[SDFilter]) -> ImmutableDeltaTree:
        return ImmutableDeltaTree(_filter_delta_node(self.node, _make_filter_tree(filters)))

    def get_stats(self) -> _SDDeltaCounter:
        return self.node.get_stats()

    def get_tree(self, path: SDPath) -> ImmutableDeltaTree:
        return ImmutableDeltaTree(self.node.get_node(path))

    @classmethod
    def deserialize(cls, raw_tree: SDRawDeltaTree) -> ImmutableDeltaTree:
        return cls(DeltaStructuredDataNode.deserialize(path=tuple(), raw_tree=raw_tree))

    def serialize(self) -> SDRawDeltaTree:
        return self.node.serialize()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({pprint.pformat(self.node.to_raw())})"


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
        retentions: Mapping[SDKey, RetentionInterval] | None = None,
    ) -> None:
        self.retentions = retentions if retentions else {}
        self._pairs: dict[SDKey, SDValue] = {}

    def __len__(self) -> int:
        # The attribute 'pairs' is decisive. Other attributes like 'retentions' have no impact
        # if there are no pairs.
        return len(self.pairs)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Attributes):
            raise TypeError(type(other))
        return self.pairs == other.pairs

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    @property
    def pairs(self) -> Mapping[SDKey, SDValue]:
        return self._pairs

    def add_pairs(self, pairs: Mapping[SDKey, SDValue]) -> None:
        self._pairs.update(pairs)

    def update_pairs(
        self,
        now: int,
        path: SDPath,
        other: Attributes,
        filter_func: SDFilterFunc,
        retention_interval: RetentionInterval,
    ) -> UpdateResult:
        compared_filtered_keys = _compare_dict_keys(
            left=set(
                _get_filtered_dict(
                    other.pairs,
                    _make_retentions_filter_func(
                        filter_func=filter_func,
                        intervals_by_key=other.retentions,
                        now=now,
                    ),
                )
            ),
            right=set(_get_filtered_dict(self.pairs, filter_func)),
        )

        pairs: dict[SDKey, SDValue] = {}
        retentions: dict[SDKey, RetentionInterval] = {}
        for key in compared_filtered_keys.only_old:
            pairs.setdefault(key, other.pairs[key])
            retentions[key] = other.retentions[key]

        for key in compared_filtered_keys.both.union(compared_filtered_keys.only_new):
            retentions[key] = retention_interval

        update_result = UpdateResult()
        if pairs:
            self.add_pairs(pairs)
            update_result.add_attr_reason(path, "pairs", pairs)

        if retentions:
            self.retentions = retentions
            update_result.add_attr_reason(path, "interval", retentions)

        return update_result

    @classmethod
    def deserialize(cls, raw_attributes: SDRawAttributes) -> Attributes:
        attributes = cls(
            retentions={
                key: RetentionInterval.deserialize(interval)
                for key, interval in raw_attributes.get("Retentions", {}).items()
            }
        )
        attributes.add_pairs(raw_attributes.get("Pairs", {}))
        return attributes

    def serialize(self) -> SDRawAttributes:
        raw_attributes: SDRawAttributes = {}
        if self._pairs:
            raw_attributes["Pairs"] = self._pairs

        if self.retentions:
            raw_attributes["Retentions"] = {
                key: interval.serialize() for key, interval in self.retentions.items()
            }
        return raw_attributes

    def to_raw(self) -> Mapping:
        # Useful for debugging; no restrictions
        return {"Pairs": self._pairs, "Retentions": self.retentions}


class Table:
    def __init__(
        self,
        *,
        key_columns: list[SDKey] | None = None,
        retentions: Mapping[SDRowIdent, Mapping[SDKey, RetentionInterval]] | None = None,
    ) -> None:
        self.key_columns = key_columns if key_columns else []
        self.retentions = retentions if retentions else {}
        self._rows_by_ident: dict[SDRowIdent, dict[SDKey, SDValue]] = {}

    def __len__(self) -> int:
        # The attribute 'rows' is decisive. Other attributes like 'key_columns' or 'retentions'
        # have no impact if there are no rows.
        return sum(map(len, self._rows_by_ident.values()))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Table):
            raise TypeError(type(other))

        compared_keys = _compare_dict_keys(
            left=set(other.rows_by_ident),
            right=set(self.rows_by_ident),
        )
        if compared_keys.only_old or compared_keys.only_new:
            return False

        for key in compared_keys.both:
            if self.rows_by_ident[key] != other.rows_by_ident[key]:
                return False

        return True

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    @property
    def rows(self) -> Sequence[Mapping[SDKey, SDValue]]:
        return list(self._rows_by_ident.values())

    @property
    def rows_by_ident(self) -> Mapping[SDRowIdent, Mapping[SDKey, SDValue]]:
        return self._rows_by_ident

    def add_key_columns(self, key_columns: Sequence[SDKey]) -> None:
        for key in key_columns:
            if key not in self.key_columns:
                self.key_columns.append(key)

    def add_rows(self, rows: Sequence[Mapping[SDKey, SDValue]]) -> None:
        for row in rows:
            self.add_row(self._make_row_ident(row), row)

    def _make_row_ident(self, row: Mapping[SDKey, SDValue]) -> SDRowIdent:
        return tuple(row[k] for k in self.key_columns if k in row)

    def add_row(self, ident: SDRowIdent, row: Mapping[SDKey, SDValue]) -> None:
        if row:
            self._rows_by_ident.setdefault(ident, {}).update(row)

    #   ---retentions-----------------------------------------------------------

    def update_rows(  # pylint: disable=too-many-branches
        self,
        now: int,
        path: SDPath,
        other: Table,
        filter_func: SDFilterFunc,
        retention_interval: RetentionInterval,
    ) -> UpdateResult:
        self.add_key_columns(other.key_columns)

        old_filtered_rows = {
            ident: filtered_row
            for ident, row in other._rows_by_ident.items()
            if (
                filtered_row := _get_filtered_dict(
                    row,
                    _make_retentions_filter_func(
                        filter_func=filter_func,
                        intervals_by_key=other.retentions.get(ident),
                        now=now,
                    ),
                )
            )
        }
        self_filtered_rows = {
            ident: filtered_row
            for ident, row in self._rows_by_ident.items()
            if (filtered_row := _get_filtered_dict(row, filter_func))
        }
        compared_filtered_idents = _compare_dict_keys(
            left=set(old_filtered_rows),
            right=set(self_filtered_rows),
        )

        retentions: dict[SDRowIdent, dict[SDKey, RetentionInterval]] = {}
        update_result = UpdateResult()
        for ident in compared_filtered_idents.only_old:
            old_row: dict[SDKey, SDValue] = {}
            for key, value in old_filtered_rows[ident].items():
                old_row.setdefault(key, value)
                retentions.setdefault(ident, {})[key] = other.retentions[ident][key]

            if old_row:
                # Update row with key column entries
                old_row.update({k: other._rows_by_ident[ident][k] for k in other.key_columns})
                self.add_row(ident, old_row)
                update_result.add_row_reason(path, ident, "row", old_row)

        for ident in compared_filtered_idents.both:
            compared_filtered_keys = _compare_dict_keys(
                left=set(old_filtered_rows[ident]),
                right=set(self_filtered_rows[ident]),
            )
            row: dict[SDKey, SDValue] = {}
            for key in compared_filtered_keys.only_old:
                row.setdefault(key, other._rows_by_ident[ident][key])
                retentions.setdefault(ident, {})[key] = other.retentions[ident][key]

            for key in compared_filtered_keys.both.union(compared_filtered_keys.only_new):
                retentions.setdefault(ident, {})[key] = retention_interval

            if row:
                # Update row with key column entries
                row.update(
                    {
                        **{k: other._rows_by_ident[ident][k] for k in other.key_columns},
                        **{k: self._rows_by_ident[ident][k] for k in self.key_columns},
                    }
                )
                self.add_row(ident, row)
                update_result.add_row_reason(path, ident, "row", row)

        for ident in compared_filtered_idents.only_new:
            for key in self_filtered_rows[ident]:
                retentions.setdefault(ident, {})[key] = retention_interval

        if retentions:
            self.retentions = retentions
            for ident, interval in retentions.items():
                update_result.add_row_reason(path, ident, "interval", interval)

        return update_result

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
                ident: {
                    key: RetentionInterval.deserialize(interval)
                    for key, interval in raw_intervals_by_key.items()
                }
                for ident, raw_intervals_by_key in raw_table.get("Retentions", {}).items()
            },
        )
        table.add_rows(rows)
        return table

    def serialize(self) -> SDRawTable:
        raw_table: SDRawTable = {}
        if self._rows_by_ident:
            raw_table.update(
                {
                    "KeyColumns": self.key_columns,
                    "Rows": list(self._rows_by_ident.values()),
                }
            )

        if self.retentions:
            raw_table["Retentions"] = {
                ident: {key: interval.serialize() for key, interval in intervals_by_key.items()}
                for ident, intervals_by_key in self.retentions.items()
            }
        return raw_table

    def to_raw(self) -> Mapping:
        # Useful for debugging; no restrictions
        return {
            "KeyColumns": self.key_columns,
            "RowsByIdent": self._rows_by_ident,
            "Retentions": self.retentions,
        }


class StructuredDataNode:
    def __init__(
        self,
        *,
        path: SDPath | None = None,
        attributes: Attributes | None = None,
        table: Table | None = None,
        nodes: dict[SDNodeName, StructuredDataNode] | None = None,
    ) -> None:
        self.path = path if path else tuple()
        self.attributes = attributes or Attributes()
        self.table = table or Table()
        self._nodes = nodes or {}

    def __len__(self) -> int:
        return sum(
            [
                len(self.attributes),
                len(self.table),
            ]
            + [len(node) for node in self._nodes.values()]
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, StructuredDataNode):
            raise TypeError(type(other))

        if self.attributes != other.attributes or self.table != other.table:
            return False

        compared_keys = _compare_dict_keys(
            left=set(other.nodes_by_name),
            right=set(self.nodes_by_name),
        )
        if compared_keys.only_old or compared_keys.only_new:
            return False

        for key in compared_keys.both:
            if self._nodes[key] != other._nodes[key]:
                return False

        return True

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    @property
    def nodes_by_name(self) -> Mapping[SDNodeName, StructuredDataNode]:
        return self._nodes

    def setdefault_node(self, path: SDPath) -> StructuredDataNode:
        if not path:
            return self

        name = path[0]
        node = self._nodes.setdefault(name, StructuredDataNode(path=self.path + (name,)))
        return node.setdefault_node(path[1:])

    def get_node(self, path: SDPath) -> StructuredDataNode | None:
        if not path:
            return self
        return None if (node := self._nodes.get(path[0])) is None else node.get_node(path[1:])

    @classmethod
    def deserialize(
        cls,
        *,
        path: SDPath,
        raw_attributes: SDRawAttributes,
        raw_table: SDRawTable,
        raw_nodes: Mapping[SDNodeName, SDRawTree],
    ) -> StructuredDataNode:
        return cls(
            path=path,
            attributes=Attributes.deserialize(raw_attributes),
            table=Table.deserialize(raw_table),
            nodes={
                name: cls.deserialize(
                    path=path + (name,),
                    raw_attributes=raw_node["Attributes"],
                    raw_table=raw_node["Table"],
                    raw_nodes=raw_node["Nodes"],
                )
                for name, raw_node in raw_nodes.items()
            },
        )

    def serialize(self) -> SDRawTree:
        return {
            "Attributes": self.attributes.serialize(),
            "Table": self.table.serialize(),
            "Nodes": {name: node.serialize() for name, node in self._nodes.items() if node},
        }

    def to_raw(self) -> Mapping:
        # Useful for debugging; no restrictions
        return {
            "Path": self.path,
            "Attributes": self.attributes.to_raw(),
            "Table": self.table.to_raw(),
            "Nodes": {name: node.to_raw() for name, node in self._nodes.items()},
        }


# .
#   .--delta tree----------------------------------------------------------.
#   |                  _      _ _          _                               |
#   |               __| | ___| | |_ __ _  | |_ _ __ ___  ___               |
#   |              / _` |/ _ \ | __/ _` | | __| '__/ _ \/ _ \              |
#   |             | (_| |  __/ | || (_| | | |_| | |  __/  __/              |
#   |              \__,_|\___|_|\__\__,_|  \__|_|  \___|\___|              |
#   |                                                                      |
#   '----------------------------------------------------------------------'


_SDEncodeAs = Callable[[SDValue], tuple[SDValue, SDValue]]
_SDDeltaCounter = Counter[Literal["new", "changed", "removed"]]


def _compute_delta_stats(dict_: Mapping[SDKey, tuple[SDValue, SDValue]]) -> _SDDeltaCounter:
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

    def __len__(self) -> int:
        return len(self.pairs)

    @classmethod
    def make_from_attributes(
        cls, *, attributes: Attributes, encode_as: _SDEncodeAs
    ) -> DeltaAttributes:
        return cls(pairs={key: encode_as(value) for key, value in attributes.pairs.items()})

    def get_stats(self) -> _SDDeltaCounter:
        return _compute_delta_stats(self.pairs)

    @classmethod
    def deserialize(cls, raw_attributes: SDRawDeltaAttributes) -> DeltaAttributes:
        return cls(pairs=raw_attributes.get("Pairs", {}))

    def serialize(self) -> SDRawDeltaAttributes:
        return {"Pairs": self.pairs} if self.pairs else {}

    def to_raw(self) -> Mapping:
        # Useful for debugging; no restrictions
        return {"Pairs": self.pairs}


@dataclass(frozen=True, kw_only=True)
class DeltaTable:
    key_columns: Sequence[SDKey] = field(default_factory=list)
    rows: Sequence[Mapping[SDKey, tuple[SDValue, SDValue]]] = field(default_factory=list)

    def __len__(self) -> int:
        return sum(map(len, self.rows))

    @classmethod
    def make_from_table(cls, *, table: Table, encode_as: _SDEncodeAs) -> DeltaTable:
        return cls(
            key_columns=table.key_columns,
            rows=[{key: encode_as(value) for key, value in row.items()} for row in table.rows],
        )

    def get_stats(self) -> _SDDeltaCounter:
        counter: _SDDeltaCounter = Counter()
        for row in self.rows:
            counter.update(_compute_delta_stats(row))
        return counter

    @classmethod
    def deserialize(cls, raw_table: SDRawDeltaTable) -> DeltaTable:
        return cls(key_columns=raw_table.get("KeyColumns", []), rows=raw_table.get("Rows", []))

    def serialize(self) -> SDRawDeltaTable:
        return {"KeyColumns": self.key_columns, "Rows": self.rows} if self.rows else {}

    def to_raw(self) -> Mapping:
        # Useful for debugging; no restrictions
        return {"KeyColumns": self.key_columns, "Rows": self.rows}


@dataclass(frozen=True, kw_only=True)
class DeltaStructuredDataNode:
    path: SDPath = ()
    attributes: DeltaAttributes = DeltaAttributes()
    table: DeltaTable = DeltaTable()
    nodes_by_name: Mapping[SDNodeName, DeltaStructuredDataNode] = field(default_factory=dict)

    def __len__(self) -> int:
        return sum(
            [
                len(self.attributes),
                len(self.table),
            ]
            + [len(node) for node in self.nodes_by_name.values()]
        )

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
            nodes_by_name={
                name: cls.make_from_node(
                    node=child,
                    encode_as=encode_as,
                )
                for name, child in node.nodes_by_name.items()
            },
        )

    def get_node(self, path: SDPath) -> DeltaStructuredDataNode | None:
        if not path:
            return self
        node = self.nodes_by_name.get(path[0])
        return None if node is None else node.get_node(path[1:])

    def get_stats(self) -> _SDDeltaCounter:
        counter: _SDDeltaCounter = Counter()
        counter.update(self.attributes.get_stats())
        counter.update(self.table.get_stats())
        for node in self.nodes_by_name.values():
            counter.update(node.get_stats())
        return counter

    @classmethod
    def deserialize(cls, *, path: SDPath, raw_tree: SDRawDeltaTree) -> DeltaStructuredDataNode:
        return cls(
            path=path,
            attributes=DeltaAttributes.deserialize(raw_attributes=raw_tree["Attributes"]),
            table=DeltaTable.deserialize(raw_table=raw_tree["Table"]),
            nodes_by_name={
                raw_node_name: cls.deserialize(
                    path=path + (raw_node_name,),
                    raw_tree=raw_node,
                )
                for raw_node_name, raw_node in raw_tree["Nodes"].items()
            },
        )

    def serialize(self) -> SDRawDeltaTree:
        return {
            "Attributes": self.attributes.serialize(),
            "Table": self.table.serialize(),
            "Nodes": {edge: node.serialize() for edge, node in self.nodes_by_name.items() if node},
        }

    def to_raw(self) -> Mapping:
        # Useful for debugging; no restrictions
        return {
            "Path": self.path,
            "Attributes": self.attributes.to_raw(),
            "Table": self.table.to_raw(),
            "Nodes": {edge: node.to_raw() for edge, node in self.nodes_by_name.items()},
        }


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
    only_old: set[SDKey]
    both: set[SDKey]
    only_new: set[SDKey]


class ComparedRowIdents(NamedTuple):
    only_old: set[SDRowIdent]
    both: set[SDRowIdent]
    only_new: set[SDRowIdent]


@overload
def _compare_dict_keys(*, left: set[SDKey], right: set[SDKey]) -> ComparedDictKeys:
    ...


@overload
def _compare_dict_keys(*, left: set[SDRowIdent], right: set[SDRowIdent]) -> ComparedRowIdents:
    ...


def _compare_dict_keys(*, left, right):
    """
    Returns the set relationships of the keys between two dictionaries:
    - relative complement of right in left
    - intersection of both
    - relative complement of left in right
    """
    return ComparedDictKeys(
        only_old=left - right,
        both=left.intersection(right),
        only_new=right - left,
    )


def _make_retentions_filter_func(
    *,
    filter_func: SDFilterFunc,
    intervals_by_key: Mapping[SDKey, RetentionInterval] | None,
    now: int,
) -> SDFilterFunc:
    return lambda k: bool(
        filter_func(k)
        and intervals_by_key
        and (interval := intervals_by_key.get(k))
        and now <= interval.keep_until
    )


def _get_filtered_dict(dict_: Mapping, filter_func: SDFilterFunc) -> dict:
    return {k: v for k, v in dict_.items() if filter_func(k)}
