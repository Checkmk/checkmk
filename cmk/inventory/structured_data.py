#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
This module handles tree structures for HW/SW Inventory system and
structured monitoring data of Check_MK.
"""

from __future__ import annotations

import ast
import gzip
import io
import json
import os
import pprint
import shutil
from collections import Counter
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Generic, Literal, NewType, Self, TypedDict, TypeVar

from cmk.ccc import store
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostName
from cmk.ccc.resulttype import Error, OK, Result

from .paths import Paths as InventoryPaths
from .paths import TreePath, TreePathGz

# TODO Cleanup path in utils, base, gui, find ONE place (type defs or similar)
# TODO filter table rows?
# TODO Check filter logic:
#   - choices = ["all", "nothing", ["k1", ...]]
#   - How to handle?
# TODO Improve _make_filter_func:
# For contact groups (via make_filter)
#   - ('choices', ['some', 'keys'])
#   - 'nothing' -> _use_nothing
#   - None -> _use_all
# For retention intervals (directly)
#   - ('choices', ['some', 'keys'])
#   - MISSING (see mk/base/agent_based/inventory.py::_get_intervals_from_config) -> _use_nothing
#   - 'all' -> _use_all

SDNodeName = NewType("SDNodeName", str)
SDPath = tuple[SDNodeName, ...]

SDKey = NewType("SDKey", str)
SDValue = int | float | str | bool | None
SDRowIdent = tuple[SDValue, ...]


class SDRawAttributes(TypedDict, total=False):
    Pairs: Mapping[SDKey, SDValue]
    Retentions: Mapping[SDKey, tuple[int, int, int, Literal["previous", "current"]]]


class SDBareAttributes(TypedDict):
    Pairs: Mapping[SDKey, SDValue]
    Retentions: Mapping[SDKey, tuple[int, int, int, Literal["previous", "current"]]]


class SDRawTable(TypedDict, total=False):
    KeyColumns: Sequence[SDKey]
    Rows: Sequence[Mapping[SDKey, SDValue]]
    Retentions: Mapping[
        SDRowIdent, Mapping[SDKey, tuple[int, int, int, Literal["previous", "current"]]]
    ]


class SDBareTable(TypedDict):
    KeyColumns: Sequence[SDKey]
    RowsByIdent: Mapping[SDRowIdent, Mapping[SDKey, SDValue]]
    Retentions: Mapping[
        SDRowIdent, Mapping[SDKey, tuple[int, int, int, Literal["previous", "current"]]]
    ]


class SDRawTree(TypedDict):
    Attributes: SDRawAttributes
    Table: SDRawTable
    Nodes: Mapping[SDNodeName, SDRawTree]


class SDBareTree(TypedDict):
    Path: SDPath
    Attributes: SDBareAttributes
    Table: SDBareTable
    Nodes: Mapping[SDNodeName, SDBareTree]


class SDRawDeltaAttributes(TypedDict, total=False):
    Pairs: Mapping[SDKey, tuple[SDValue, SDValue]]


class SDBareDeltaAttributes(TypedDict):
    Pairs: Mapping[SDKey, tuple[SDValue, SDValue]]


class SDRawDeltaTable(TypedDict, total=False):
    KeyColumns: Sequence[SDKey]
    Rows: Sequence[Mapping[SDKey, tuple[SDValue, SDValue]]]


class SDBareDeltaTable(TypedDict, total=False):
    KeyColumns: Sequence[SDKey]
    Rows: Sequence[Mapping[SDKey, tuple[SDValue, SDValue]]]


class SDRawDeltaTree(TypedDict):
    Attributes: SDRawDeltaAttributes
    Table: SDRawDeltaTable
    Nodes: Mapping[SDNodeName, SDRawDeltaTree]


class SDBareDeltaTree(TypedDict):
    Path: SDPath
    Attributes: SDBareDeltaAttributes
    Table: SDBareDeltaTable
    Nodes: Mapping[SDNodeName, SDBareDeltaTree]


class _RawIntervalFromConfigMandatory(TypedDict):
    interval: int
    visible_raw_path: str


class RawIntervalFromConfig(_RawIntervalFromConfigMandatory, total=False):
    attributes: Literal["all"] | tuple[str, list[str]]
    columns: Literal["all"] | tuple[str, list[str]]


@dataclass(frozen=True)
class RetentionInterval:
    cached_at: int
    cache_interval: int
    retention_interval: int
    source: Literal["previous", "current"]

    @classmethod
    def from_previous(cls, previous: RetentionInterval) -> RetentionInterval:
        return cls(
            previous.cached_at, previous.cache_interval, previous.retention_interval, "previous"
        )

    @classmethod
    def from_config(
        cls, cached_at: int, cache_interval: int, retention_interval: int
    ) -> RetentionInterval:
        return cls(cached_at, cache_interval, retention_interval, "current")

    @property
    def keep_until(self) -> int:
        return self.cached_at + self.cache_interval + self.retention_interval


@dataclass(frozen=True, kw_only=True)
class UpdateResultAttributes:
    path: SDPath
    title: str
    message: str

    def __str__(self) -> str:
        return f"[Attributes] {self.title}: self.message"


@dataclass(frozen=True, kw_only=True)
class UpdateResultTable:
    path: SDPath
    ident: SDRowIdent
    title: str
    message: str

    def __str__(self) -> str:
        return f"[Table] '{', '.join(map(str, self.ident))}': {self.title}: self.message"


def parse_visible_raw_path(raw_path: str) -> SDPath:
    return tuple(SDNodeName(part) for part in raw_path.split(".") if part)


#   .--helpers-------------------------------------------------------------.
#   |                  _          _                                        |
#   |                 | |__   ___| |_ __   ___ _ __ ___                    |
#   |                 | '_ \ / _ \ | '_ \ / _ \ '__/ __|                   |
#   |                 | | | |  __/ | |_) |  __/ |  \__ \                   |
#   |                 |_| |_|\___|_| .__/ \___|_|  |___/                   |
#   |                              |_|                                     |
#   '----------------------------------------------------------------------'


def _make_row_ident(key_columns: Sequence[SDKey], row: Mapping[SDKey, SDValue]) -> SDRowIdent:
    return tuple(row[k] for k in key_columns if k in row)


_T = TypeVar("_T")


@dataclass(frozen=True, kw_only=True)
class _DictKeys(Generic[_T]):
    only_left: set[_T]
    both: set[_T]
    only_right: set[_T]

    @classmethod
    def compare(cls, *, left: set[_T], right: set[_T]) -> Self:
        """
        Returns the set relationships of the keys between two dictionaries:
        - relative complement of right in left
        - intersection of both
        - relative complement of left in right
        """
        return cls(
            only_left=left - right,
            both=left.intersection(right),
            only_right=right - left,
        )


# .
#   .--filters-------------------------------------------------------------.
#   |                       __ _ _ _                                       |
#   |                      / _(_) | |_ ___ _ __ ___                        |
#   |                     | |_| | | __/ _ \ '__/ __|                       |
#   |                     |  _| | | ||  __/ |  \__ \                       |
#   |                     |_| |_|_|\__\___|_|  |___/                       |
#   |                                                                      |
#   '----------------------------------------------------------------------'


@dataclass(frozen=True)
class SDFilterChoice:
    path: SDPath
    pairs: Literal["nothing", "all"] | Sequence[SDKey]
    columns: Literal["nothing", "all"] | Sequence[SDKey]
    nodes: Literal["nothing", "all"] | Sequence[SDNodeName]


@dataclass(frozen=True)
class _SDRetentionFilterChoice:
    choice: Literal["nothing", "all"] | Sequence[SDKey]
    cache_info: tuple[int, int]


@dataclass(frozen=True, kw_only=True)
class SDRetentionFilterChoices:
    path: SDPath
    interval: int
    _pairs: list[_SDRetentionFilterChoice] = field(default_factory=list)
    _columns: list[_SDRetentionFilterChoice] = field(default_factory=list)

    @property
    def pairs(self) -> Sequence[_SDRetentionFilterChoice]:
        return self._pairs

    @property
    def columns(self) -> Sequence[_SDRetentionFilterChoice]:
        return self._columns

    def add_pairs_choice(
        self, choice: Literal["nothing", "all"] | Sequence[SDKey], cache_info: tuple[int, int]
    ) -> None:
        self._pairs.append(_SDRetentionFilterChoice(choice, cache_info))

    def add_columns_choice(
        self, choice: Literal["nothing", "all"] | Sequence[SDKey], cache_info: tuple[int, int]
    ) -> None:
        self._columns.append(_SDRetentionFilterChoice(choice, cache_info))


_CT = TypeVar("_CT", SDKey, SDNodeName)


def _make_filter_func(choice: Literal["nothing", "all"] | Sequence[_CT]) -> Callable[[_CT], bool]:
    match choice:
        case "nothing":
            return lambda k: False
        case "all":
            return lambda k: True
        case _:
            return lambda k: k in choice


def _consolidate_filter_funcs(
    choices: Sequence[Literal["nothing", "all"] | Sequence[_CT]],
) -> Callable[[_CT], bool]:
    return lambda kn: any(_make_filter_func(c)(kn) for c in choices)


_VT_co = TypeVar("_VT_co", covariant=True)


def _get_filtered_dict(
    mapping: Mapping[SDKey, _VT_co], filter_func: Callable[[SDKey], bool]
) -> Mapping[SDKey, _VT_co]:
    return {k: v for k, v in mapping.items() if filter_func(k)}


@dataclass(frozen=True, kw_only=True)
class _FilterTree:
    _filter_choices_by_name: dict[SDNodeName, _FilterTree] = field(default_factory=dict)
    _filter_choices_pairs: list[Literal["nothing", "all"] | Sequence[SDKey]] = field(
        default_factory=list
    )
    _filter_choices_columns: list[Literal["nothing", "all"] | Sequence[SDKey]] = field(
        default_factory=list
    )
    _filter_choices_nodes: list[Literal["nothing", "all"] | Sequence[SDNodeName]] = field(
        default_factory=list
    )

    @property
    def filters_by_name(self) -> Mapping[SDNodeName, _FilterTree]:
        return self._filter_choices_by_name

    def filter_pairs(self, pairs: Mapping[SDKey, _VT_co]) -> Mapping[SDKey, _VT_co]:
        return (
            _get_filtered_dict(pairs, _consolidate_filter_funcs(self._filter_choices_pairs))
            if self._filter_choices_pairs
            else pairs
        )

    def filter_row(self, row: Mapping[SDKey, _VT_co]) -> Mapping[SDKey, _VT_co]:
        return (
            _get_filtered_dict(row, _consolidate_filter_funcs(self._filter_choices_columns))
            if self._filter_choices_columns
            else row
        )

    def filter_node_names(self, node_names: set[SDNodeName]) -> set[SDNodeName]:
        filter_nodes = _consolidate_filter_funcs(self._filter_choices_nodes)
        return {n for n in node_names if filter_nodes(n)}.union(self.filters_by_name)

    def append(self, path: SDPath, filter_choice: SDFilterChoice) -> None:
        if path:
            self._filter_choices_by_name.setdefault(path[0], _FilterTree()).append(
                path[1:], filter_choice
            )
            return
        self._filter_choices_pairs.append(filter_choice.pairs)
        self._filter_choices_columns.append(filter_choice.columns)
        self._filter_choices_nodes.append(filter_choice.nodes)


def _make_filter_tree(filters: Iterable[SDFilterChoice]) -> _FilterTree:
    filter_tree_ = _FilterTree()
    for f in filters:
        filter_tree_.append(f.path, f)
    return filter_tree_


def _make_retentions_filter_func(
    *,
    filter_func: Callable[[SDKey], bool],
    intervals_by_key: Mapping[SDKey, RetentionInterval] | None,
    now: int,
) -> Callable[[SDKey], bool]:
    return lambda k: bool(
        filter_func(k)
        and intervals_by_key
        and (interval := intervals_by_key.get(k))
        and now <= interval.keep_until
    )


# .
#   .--serialization-------------------------------------------------------.
#   |                      _       _ _          _   _                      |
#   |        ___  ___ _ __(_) __ _| (_)______ _| |_(_) ___  _ __           |
#   |       / __|/ _ \ '__| |/ _` | | |_  / _` | __| |/ _ \| '_ \          |
#   |       \__ \  __/ |  | | (_| | | |/ / (_| | |_| | (_) | | | |         |
#   |       |___/\___|_|  |_|\__,_|_|_/___\__,_|\__|_|\___/|_| |_|         |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def _serialize_retention_interval(
    retention_interval: RetentionInterval,
) -> tuple[int, int, int, Literal["previous", "current"]]:
    return (
        retention_interval.cached_at,
        retention_interval.cache_interval,
        retention_interval.retention_interval,
        retention_interval.source,
    )


def _serialize_attributes(attributes: _MutableAttributes | ImmutableAttributes) -> SDRawAttributes:
    raw_attributes: SDRawAttributes = {}
    if attributes.pairs:
        raw_attributes["Pairs"] = attributes.pairs
    if attributes.retentions:
        raw_attributes["Retentions"] = {
            k: _serialize_retention_interval(v) for k, v in attributes.retentions.items()
        }
    return raw_attributes


def _serialize_table(table: _MutableTable | ImmutableTable) -> SDRawTable:
    raw_table: SDRawTable = {}
    if table.rows_by_ident:
        raw_table.update(
            {
                "KeyColumns": table.key_columns,
                "Rows": list(table.rows_by_ident.values()),
            }
        )
    if table.retentions:
        raw_table["Retentions"] = {
            i: {k: _serialize_retention_interval(v) for k, v in ri.items()}
            for i, ri in table.retentions.items()
        }
    return raw_table


def serialize_tree(tree: MutableTree | ImmutableTree) -> SDRawTree:
    return {
        "Attributes": _serialize_attributes(tree.attributes),
        "Table": _serialize_table(tree.table),
        "Nodes": {name: serialize_tree(node) for name, node in tree.nodes_by_name.items() if node},
    }


def _deserialize_legacy_attributes(raw_pairs: Mapping[SDKey, SDValue]) -> ImmutableAttributes:
    return ImmutableAttributes(pairs=raw_pairs)


def _deserialize_legacy_table(raw_rows: Sequence[Mapping[SDKey, SDValue]]) -> ImmutableTable:
    key_columns = sorted({k for r in raw_rows for k in r})
    rows_by_ident: dict[SDRowIdent, dict[SDKey, SDValue]] = {}
    for row in raw_rows:
        rows_by_ident.setdefault(_make_row_ident(key_columns, row), {}).update(row)

    return ImmutableTable(key_columns=key_columns, rows_by_ident=rows_by_ident)


def _deserialize_legacy_tree(
    path: SDPath,
    raw_tree: Mapping[str, object],
    raw_rows: Sequence[Mapping] | None = None,
) -> ImmutableTree:
    raw_pairs: dict[SDKey, SDValue] = {}
    raw_tables: dict[SDNodeName, list[dict]] = {}
    raw_nodes: dict[SDNodeName, dict] = {}

    for key, value in raw_tree.items():
        if isinstance(value, dict):
            if not value:
                continue
            raw_nodes.setdefault(SDNodeName(key), value)

        elif isinstance(value, list):
            if not value:
                continue

            if all(isinstance(v, int | float | str | bool) or v is None for v in value):
                if w := ", ".join(str(v) for v in value if v):
                    raw_pairs.setdefault(SDKey(key), w)
                continue

            if all(not isinstance(v, list | dict) for row in value for v in row.values()):
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
                raw_tables.setdefault(SDNodeName(key), value)
                continue

            for idx, entry in enumerate(value):
                raw_nodes.setdefault(SDNodeName(key), {}).setdefault(str(idx), entry)

        elif isinstance(value, int | float | str | bool) or value is None:
            raw_pairs.setdefault(SDKey(key), value)

        else:
            raise TypeError(value)

    return ImmutableTree(
        path=path,
        attributes=_deserialize_legacy_attributes(raw_pairs),
        table=_deserialize_legacy_table(raw_rows) if raw_rows else ImmutableTable(),
        nodes_by_name={
            **{
                name: _deserialize_legacy_tree(
                    path + (name,),
                    raw_node,
                    raw_tables.get(name),
                )
                for name, raw_node in raw_nodes.items()
            },
            **{
                name: ImmutableTree(
                    path=path + (name,),
                    table=_deserialize_legacy_table(raw_rows),
                )
                for name in set(raw_tables) - set(raw_nodes)
                if (raw_rows := raw_tables[name])
            },
        },
    )


def _deserialize_retention_interval(
    raw_retention_interval: tuple[int, int, int]
    | tuple[int, int, int, Literal["previous", "current"]],
) -> RetentionInterval:
    return (
        RetentionInterval(*raw_retention_interval)
        if len(raw_retention_interval) == 4
        else RetentionInterval(*raw_retention_interval[:3], "current")
    )


def _deserialize_attributes(raw_attributes: SDRawAttributes) -> ImmutableAttributes:
    return ImmutableAttributes(
        pairs=raw_attributes.get("Pairs", {}),
        retentions={
            key: _deserialize_retention_interval(raw_retention_interval)
            for key, raw_retention_interval in raw_attributes.get("Retentions", {}).items()
        },
    )


def _deserialize_table(raw_table: SDRawTable) -> ImmutableTable:
    rows = raw_table.get("Rows", [])
    key_columns = raw_table.get("KeyColumns", [])

    rows_by_ident: dict[SDRowIdent, dict[SDKey, SDValue]] = {}
    for row in rows:
        rows_by_ident.setdefault(_make_row_ident(key_columns, row), {}).update(row)

    return ImmutableTable(
        key_columns=key_columns,
        rows_by_ident=rows_by_ident,
        retentions={
            ident: {
                key: _deserialize_retention_interval(raw_retention_interval)
                for key, raw_retention_interval in raw_intervals_by_key.items()
            }
            for ident, raw_intervals_by_key in raw_table.get("Retentions", {}).items()
        },
    )


def _deserialize_tree(
    *,
    path: SDPath,
    raw_attributes: SDRawAttributes,
    raw_table: SDRawTable,
    raw_nodes: Mapping[SDNodeName, SDRawTree],
) -> ImmutableTree:
    return ImmutableTree(
        path=path,
        attributes=_deserialize_attributes(raw_attributes),
        table=_deserialize_table(raw_table),
        nodes_by_name={
            name: _deserialize_tree(
                path=path + (name,),
                raw_attributes=raw_node["Attributes"],
                raw_table=raw_node["Table"],
                raw_nodes=raw_node["Nodes"],
            )
            for name, raw_node in raw_nodes.items()
        },
    )


def deserialize_tree(raw_tree: object) -> ImmutableTree:
    if not isinstance(raw_tree, dict):
        raise TypeError(raw_tree)
    try:
        raw_attributes = raw_tree["Attributes"]
        raw_table = raw_tree["Table"]
        raw_nodes = raw_tree["Nodes"]
    except KeyError:
        return _deserialize_legacy_tree(path=(), raw_tree=raw_tree)
    return _deserialize_tree(
        path=(),
        raw_attributes=raw_attributes,
        raw_table=raw_table,
        raw_nodes=raw_nodes,
    )


def _serialize_delta_value(delta_value: SDDeltaValue) -> tuple[SDValue, SDValue]:
    return (delta_value.old, delta_value.new)


def _serialize_delta_attributes(delta_attributes: ImmutableDeltaAttributes) -> SDRawDeltaAttributes:
    return (
        {"Pairs": {k: _serialize_delta_value(v) for k, v in delta_attributes.pairs.items()}}
        if delta_attributes.pairs
        else {}
    )


def _serialize_delta_table(delta_table: ImmutableDeltaTable) -> SDRawDeltaTable:
    return (
        {
            "KeyColumns": delta_table.key_columns,
            "Rows": [
                {k: _serialize_delta_value(v) for k, v in r.items()} for r in delta_table.rows
            ],
        }
        if delta_table.rows
        else {}
    )


def serialize_delta_tree(delta_tree: ImmutableDeltaTree) -> SDRawDeltaTree:
    return {
        "Attributes": _serialize_delta_attributes(delta_tree.attributes),
        "Table": _serialize_delta_table(delta_tree.table),
        "Nodes": {
            edge: serialize_delta_tree(node)
            for edge, node in delta_tree.nodes_by_name.items()
            if node
        },
    }


def _deserialize_delta_value(raw_delta_value: tuple[SDValue, SDValue]) -> SDDeltaValue:
    return SDDeltaValue(old=raw_delta_value[0], new=raw_delta_value[1])


def _deserialize_delta_attributes(raw_attributes: SDRawDeltaAttributes) -> ImmutableDeltaAttributes:
    return ImmutableDeltaAttributes(
        pairs={k: _deserialize_delta_value(v) for k, v in raw_attributes.get("Pairs", {}).items()}
    )


def _deserialize_delta_table(raw_table: SDRawDeltaTable) -> ImmutableDeltaTable:
    return ImmutableDeltaTable(
        key_columns=raw_table.get("KeyColumns", []),
        rows=[
            {k: _deserialize_delta_value(v) for k, v in r.items()}
            for r in raw_table.get("Rows", [])
        ],
    )


def _deserialize_delta_tree(*, path: SDPath, raw_tree: SDRawDeltaTree) -> ImmutableDeltaTree:
    return ImmutableDeltaTree(
        path=path,
        attributes=_deserialize_delta_attributes(raw_attributes=raw_tree["Attributes"]),
        table=_deserialize_delta_table(raw_table=raw_tree["Table"]),
        nodes_by_name={
            raw_node_name: _deserialize_delta_tree(
                path=path + (raw_node_name,),
                raw_tree=raw_node,
            )
            for raw_node_name, raw_node in raw_tree["Nodes"].items()
        },
    )


def deserialize_delta_tree(raw_tree: SDRawDeltaTree) -> ImmutableDeltaTree:
    return _deserialize_delta_tree(path=(), raw_tree=raw_tree)


# .
#   .--mutable tree--------------------------------------------------------.
#   |                      _        _     _        _                       |
#   |      _ __ ___  _   _| |_ __ _| |__ | | ___  | |_ _ __ ___  ___       |
#   |     | '_ ` _ \| | | | __/ _` | '_ \| |/ _ \ | __| '__/ _ \/ _ \      |
#   |     | | | | | | |_| | || (_| | |_) | |  __/ | |_| | |  __/  __/      |
#   |     |_| |_| |_|\__,_|\__\__,_|_.__/|_|\___|  \__|_|  \___|\___|      |
#   |                                                                      |
#   '----------------------------------------------------------------------'


@dataclass(kw_only=True)
class _MutableAttributes:
    pairs: dict[SDKey, SDValue] = field(default_factory=dict)
    retentions: Mapping[SDKey, RetentionInterval] = field(default_factory=dict)

    def __len__(self) -> int:
        # The attribute 'pairs' is decisive. Other attributes like 'retentions' have no impact
        # if there are no pairs.
        return len(self.pairs)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, _MutableAttributes | ImmutableAttributes):
            return NotImplemented
        return self.pairs == other.pairs

    def add(self, pairs: Mapping[SDKey, SDValue]) -> None:
        self.pairs.update(pairs)

    def update(
        self,
        now: int,
        previous: ImmutableAttributes,
        path: SDPath,
        interval: int,
        choice: _SDRetentionFilterChoice,
    ) -> Sequence[UpdateResultAttributes]:
        filter_func = _make_filter_func(choice.choice)
        retention_interval = RetentionInterval.from_config(*choice.cache_info, interval)
        compared_keys = _DictKeys.compare(
            left=set(
                _get_filtered_dict(
                    previous.pairs,
                    _make_retentions_filter_func(
                        filter_func=filter_func,
                        intervals_by_key=previous.retentions,
                        now=now,
                    ),
                )
            ),
            right=set(_get_filtered_dict(self.pairs, filter_func)),
        )

        pairs: dict[SDKey, SDValue] = {}
        retentions: dict[SDKey, RetentionInterval] = {}
        for key in compared_keys.only_left:
            pairs.setdefault(key, previous.pairs[key])
            retentions[key] = RetentionInterval.from_previous(previous.retentions[key])

        for key in compared_keys.both.union(compared_keys.only_right):
            retentions[key] = retention_interval

        update_results = []
        if pairs:
            self.add(pairs)
            update_results.append(
                UpdateResultAttributes(
                    path=path,
                    title="Added pairs",
                    message=", ".join(sorted(pairs)),
                )
            )

        if retentions:
            self.retentions = retentions
            update_results.append(
                UpdateResultAttributes(
                    path=path,
                    title="Keep until",
                    message=", ".join([f"{k} ({v.keep_until})" for k, v in retentions.items()]),
                )
            )

        return update_results

    @property
    def bare(self) -> SDBareAttributes:
        # Useful for debugging; no restrictions
        return {
            "Pairs": self.pairs,
            "Retentions": {k: _serialize_retention_interval(v) for k, v in self.retentions.items()},
        }


@dataclass(kw_only=True)
class _MutableTable:
    key_columns: Sequence[SDKey] = field(default_factory=list)
    rows_by_ident: dict[SDRowIdent, dict[SDKey, SDValue]] = field(default_factory=dict)
    retentions: Mapping[SDRowIdent, Mapping[SDKey, RetentionInterval]] = field(default_factory=dict)

    def __len__(self) -> int:
        # The attribute 'rows' is decisive. Other attributes like 'key_columns' or 'retentions'
        # have no impact if there are no rows.
        return sum(map(len, self.rows_by_ident.values()))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, _MutableTable | ImmutableTable):
            return NotImplemented

        compared_row_idents = _DictKeys.compare(
            left=set(self.rows_by_ident),
            right=set(other.rows_by_ident),
        )

        if compared_row_idents.only_left:
            return False

        if compared_row_idents.only_right:
            return False

        return all(
            self.rows_by_ident[i] == other.rows_by_ident[i] for i in compared_row_idents.both
        )

    def _add_key_columns(self, key_columns: Iterable[SDKey]) -> None:
        self.key_columns = sorted(set(self.key_columns).union(key_columns))

    def _add_row(self, ident: SDRowIdent, row: Mapping[SDKey, SDValue]) -> None:
        if row:
            self.rows_by_ident.setdefault(ident, {}).update(row)

    def add(self, key_columns: Iterable[SDKey], rows: Sequence[Mapping[SDKey, SDValue]]) -> None:
        self._add_key_columns(key_columns)
        for row in rows:
            self._add_row(_make_row_ident(self.key_columns, row), row)

    def update(
        self,
        now: int,
        previous: ImmutableTable,
        path: SDPath,
        interval: int,
        choice: _SDRetentionFilterChoice,
    ) -> Sequence[UpdateResultTable]:
        filter_func = _make_filter_func(choice.choice)
        retention_interval = RetentionInterval.from_config(*choice.cache_info, interval)
        self._add_key_columns(previous.key_columns)
        previous_filtered_rows = {
            ident: filtered_row
            for ident, row in previous.rows_by_ident.items()
            if (
                filtered_row := _get_filtered_dict(
                    row,
                    _make_retentions_filter_func(
                        filter_func=filter_func,
                        intervals_by_key=previous.retentions.get(ident),
                        now=now,
                    ),
                )
            )
        }
        current_filtered_rows = {
            ident: filtered_row
            for ident, row in self.rows_by_ident.items()
            if (filtered_row := _get_filtered_dict(row, filter_func))
        }
        compared_row_idents = _DictKeys.compare(
            left=set(previous_filtered_rows),
            right=set(current_filtered_rows),
        )

        retentions: dict[SDRowIdent, dict[SDKey, RetentionInterval]] = {}
        update_results = []
        for ident in compared_row_idents.only_left:
            previous_row: dict[SDKey, SDValue] = {}
            for key, value in previous_filtered_rows[ident].items():
                previous_row.setdefault(key, value)
                retentions.setdefault(ident, {})[key] = RetentionInterval.from_previous(
                    previous.retentions[ident][key]
                )

            if previous_row:
                # Update row with key column entries
                previous_row |= {k: previous.rows_by_ident[ident][k] for k in previous.key_columns}
                self._add_row(ident, previous_row)
                update_results.append(
                    UpdateResultTable(
                        path=path,
                        ident=ident,
                        title="Added row",
                        message=", ".join(sorted(previous_row)),
                    )
                )

        for ident in compared_row_idents.both:
            compared_keys = _DictKeys.compare(
                left=set(previous_filtered_rows[ident]),
                right=set(current_filtered_rows[ident]),
            )
            row: dict[SDKey, SDValue] = {}
            for key in compared_keys.only_left:
                row.setdefault(key, previous.rows_by_ident[ident][key])
                retentions.setdefault(ident, {})[key] = RetentionInterval.from_previous(
                    previous.retentions[ident][key]
                )

            for key in compared_keys.both.union(compared_keys.only_right):
                retentions.setdefault(ident, {})[key] = retention_interval

            if row:
                # Update row with key column entries
                row.update(
                    {
                        **{k: previous.rows_by_ident[ident][k] for k in previous.key_columns},
                        **{k: self.rows_by_ident[ident][k] for k in self.key_columns},
                    }
                )
                self._add_row(ident, row)
                update_results.append(
                    UpdateResultTable(
                        path=path,
                        ident=ident,
                        title="Added row",
                        message=", ".join(sorted(row)),
                    )
                )

        for ident in compared_row_idents.only_right:
            for key in current_filtered_rows[ident]:
                retentions.setdefault(ident, {})[key] = retention_interval

        if retentions:
            self.retentions = retentions
            for ident, intervals_by_key in retentions.items():
                update_results.append(
                    UpdateResultTable(
                        path=path,
                        ident=ident,
                        title="Keep until",
                        message=", ".join(
                            [f"{k} ({v.keep_until})" for k, v in intervals_by_key.items()]
                        ),
                    )
                )

        return update_results

    @property
    def bare(self) -> SDBareTable:
        # Useful for debugging; no restrictions
        return {
            "KeyColumns": self.key_columns,
            "RowsByIdent": self.rows_by_ident,
            "Retentions": {
                i: {k: _serialize_retention_interval(v) for k, v in ri.items()}
                for i, ri in self.retentions.items()
            },
        }


@dataclass(frozen=True, kw_only=True)
class MutableTree:
    path: SDPath = ()
    attributes: _MutableAttributes = field(default_factory=lambda: _MutableAttributes())
    table: _MutableTable = field(default_factory=lambda: _MutableTable())
    nodes_by_name: dict[SDNodeName, MutableTree] = field(default_factory=dict)

    def __len__(self) -> int:
        return sum(
            [len(self.attributes), len(self.table)]
            + [len(node) for node in self.nodes_by_name.values()]
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, MutableTree | ImmutableTree):
            return NotImplemented

        if self.attributes != other.attributes or self.table != other.table:
            return False

        compared_node_names = _DictKeys.compare(
            left=set(self.nodes_by_name),
            right=set(other.nodes_by_name),
        )

        if any(self.nodes_by_name[n] for n in compared_node_names.only_left):
            return False

        if any(other.nodes_by_name[n] for n in compared_node_names.only_right):
            return False

        return all(
            self.nodes_by_name[n] == other.nodes_by_name[n] for n in compared_node_names.both
        )

    def add(
        self,
        *,
        path: SDPath,
        pairs: Sequence[Mapping[SDKey, SDValue]] | None = None,
        key_columns: Sequence[SDKey] | None = None,
        rows: Sequence[Mapping[SDKey, SDValue]] | None = None,
    ) -> None:
        node = self.setdefault_node(path)
        if pairs:
            for p in pairs:
                node.attributes.add(p)
        if key_columns and rows:
            node.table.add(key_columns, rows)

    def update(
        self,
        *,
        now: int,
        previous_tree: ImmutableTree,
        choices: SDRetentionFilterChoices,
    ) -> Sequence[UpdateResultAttributes | UpdateResultTable]:
        node = self.setdefault_node(choices.path)
        previous_node = previous_tree.get_tree(choices.path)
        return [
            r
            for c in choices.pairs
            for r in node.attributes.update(
                now, previous_node.attributes, choices.path, choices.interval, c
            )
        ] + [
            r
            for c in choices.columns
            for r in node.table.update(now, previous_node.table, choices.path, choices.interval, c)
        ]

    def setdefault_node(self, path: SDPath) -> MutableTree:
        if not path:
            return self

        name = path[0]
        node = self.nodes_by_name.setdefault(name, MutableTree(path=self.path + (name,)))
        return node.setdefault_node(path[1:])

    def get_attribute(self, path: SDPath, key: SDKey) -> SDValue:
        return self.get_tree(path).attributes.pairs.get(key)

    def get_tree(self, path: SDPath) -> MutableTree:
        if not path:
            return self
        return (
            MutableTree()
            if (node := self.nodes_by_name.get(path[0])) is None
            else node.get_tree(path[1:])
        )

    def has_table(self, path: SDPath) -> bool:
        return len(self.get_tree(path).table) > 0

    @property
    def bare(self) -> SDBareTree:
        # Useful for debugging; no restrictions
        return {
            "Path": self.path,
            "Attributes": self.attributes.bare,
            "Table": self.table.bare,
            "Nodes": {name: node.bare for name, node in self.nodes_by_name.items()},
        }

    def __str__(self) -> str:
        return f"{self.__class__.__name__}({pprint.pformat(self.bare)})"


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


def _filter_attributes(
    attributes: ImmutableAttributes, filter_tree_: _FilterTree
) -> ImmutableAttributes:
    return ImmutableAttributes(
        pairs=filter_tree_.filter_pairs(attributes.pairs),
        retentions=attributes.retentions,
    )


def _filter_table(table: ImmutableTable, filter_tree_: _FilterTree) -> ImmutableTable:
    return ImmutableTable(
        key_columns=table.key_columns,
        rows_by_ident={
            ident: filtered_row
            for ident, row in table.rows_by_ident.items()
            if (filtered_row := filter_tree_.filter_row(row))
        },
        retentions=table.retentions,
    )


def _filter_tree(tree: ImmutableTree, filter_tree_: _FilterTree) -> ImmutableTree:
    return ImmutableTree(
        path=tree.path,
        attributes=_filter_attributes(tree.attributes, filter_tree_),
        table=_filter_table(tree.table, filter_tree_),
        nodes_by_name={
            name: filtered_node
            for name in filter_tree_.filter_node_names(set(tree.nodes_by_name))
            if (
                filtered_node := _filter_tree(
                    tree.nodes_by_name.get(name, ImmutableTree(path=tree.path + (name,))),
                    filter_tree_.filters_by_name.get(name, _FilterTree()),
                )
            )
        },
    )


def filter_tree(tree: ImmutableTree, filters: Iterable[SDFilterChoice]) -> ImmutableTree:
    return _filter_tree(tree, _make_filter_tree(filters))


def _merge_attributes(left: ImmutableAttributes, right: ImmutableAttributes) -> ImmutableAttributes:
    return ImmutableAttributes(
        pairs={**left.pairs, **right.pairs},
        retentions={**left.retentions, **right.retentions},
    )


def _merge_tables_by_same_or_empty_key_columns(
    key_columns: Sequence[SDKey], left: ImmutableTable, right: ImmutableTable
) -> ImmutableTable:
    compared_row_idents = _DictKeys.compare(
        left=set(left.rows_by_ident),
        right=set(right.rows_by_ident),
    )

    rows_by_ident: dict[SDRowIdent, Mapping[SDKey, SDValue]] = {}
    for ident in compared_row_idents.only_left:
        rows_by_ident.setdefault(ident, left.rows_by_ident[ident])

    for ident in compared_row_idents.both:
        rows_by_ident.setdefault(
            ident,
            {
                **left.rows_by_ident[ident],
                **right.rows_by_ident[ident],
            },
        )

    for ident in compared_row_idents.only_right:
        rows_by_ident.setdefault(ident, right.rows_by_ident[ident])

    return ImmutableTable(
        key_columns=key_columns,
        rows_by_ident=rows_by_ident,
        retentions={**left.retentions, **right.retentions},
    )


def _merge_tables(left: ImmutableTable, right: ImmutableTable) -> ImmutableTable:
    if left.key_columns and not right.key_columns:
        return _merge_tables_by_same_or_empty_key_columns(left.key_columns, left, right)

    if not left.key_columns and right.key_columns:
        return _merge_tables_by_same_or_empty_key_columns(right.key_columns, left, right)

    if left.key_columns == right.key_columns:
        return _merge_tables_by_same_or_empty_key_columns(left.key_columns, left, right)

    # Re-calculate row identifiers for legacy tables or inventory and status tables
    key_columns = sorted(set(left.key_columns).intersection(right.key_columns))
    rows_by_ident: dict[SDRowIdent, dict[SDKey, SDValue]] = {}
    for row in list(left.rows_by_ident.values()) + list(right.rows_by_ident.values()):
        rows_by_ident.setdefault(_make_row_ident(key_columns, row), {}).update(row)

    return ImmutableTable(
        key_columns=key_columns,
        rows_by_ident=rows_by_ident,
        retentions={**left.retentions, **right.retentions},
    )


def merge_trees(left: ImmutableTree, right: ImmutableTree) -> ImmutableTree:
    compared_node_names = _DictKeys.compare(
        left=set(left.nodes_by_name),
        right=set(right.nodes_by_name),
    )

    nodes_by_name: dict[SDNodeName, ImmutableTree] = {}
    for name in compared_node_names.only_left:
        nodes_by_name[name] = left.nodes_by_name[name]

    for name in compared_node_names.both:
        nodes_by_name[name] = merge_trees(
            left=left.nodes_by_name[name], right=right.nodes_by_name[name]
        )

    for name in compared_node_names.only_right:
        nodes_by_name[name] = right.nodes_by_name[name]

    return ImmutableTree(
        path=left.path,
        attributes=_merge_attributes(left.attributes, right.attributes),
        table=_merge_tables(left.table, right.table),
        nodes_by_name=nodes_by_name,
    )


@dataclass(frozen=True, kw_only=True)
class SDDeltaValue:
    old: SDValue
    new: SDValue


def _encode_as_new(value: SDValue) -> SDDeltaValue:
    return SDDeltaValue(old=None, new=value)


def _encode_as_removed(value: SDValue) -> SDDeltaValue:
    return SDDeltaValue(old=value, new=None)


@dataclass(frozen=True, kw_only=True)
class _DeltaDict:
    result: Mapping[SDKey, SDDeltaValue]
    has_changes: bool

    @classmethod
    def compare(
        cls, *, left: Mapping[SDKey, SDValue], right: Mapping[SDKey, SDValue], keep_identical: bool
    ) -> Self:
        """
        Format of compared entries:
          new:          {k: (None, new_value), ...}
          changed:      {k: (old_value, new_value), ...}
          removed:      {k: (old_value, None), ...}
          identical:    {k: (value, value), ...}
        """
        compared_keys = _DictKeys.compare(left=set(left), right=set(right))
        compared_dict: dict[SDKey, SDDeltaValue] = {}

        has_changes = False
        for key in compared_keys.both:
            if (left_value := left[key]) != (right_value := right[key]):
                compared_dict.setdefault(key, SDDeltaValue(old=right_value, new=left_value))
                has_changes = True
            elif keep_identical:
                compared_dict.setdefault(key, SDDeltaValue(old=left_value, new=left_value))

        compared_dict |= {k: _encode_as_removed(right[k]) for k in compared_keys.only_right}
        compared_dict |= {k: _encode_as_new(left[k]) for k in compared_keys.only_left}

        return cls(
            result=compared_dict,
            has_changes=bool(has_changes or compared_keys.only_right or compared_keys.only_left),
        )


def _compare_attributes(
    left: ImmutableAttributes, right: ImmutableAttributes
) -> ImmutableDeltaAttributes:
    return ImmutableDeltaAttributes(
        pairs=_DeltaDict.compare(
            left=left.pairs,
            right=right.pairs,
            keep_identical=False,
        ).result,
    )


def _compare_tables(left: ImmutableTable, right: ImmutableTable) -> ImmutableDeltaTable:
    compared_row_idents = _DictKeys.compare(
        left=set(left.rows_by_ident),
        right=set(right.rows_by_ident),
    )

    rows: list[Mapping[SDKey, SDDeltaValue]] = []

    for ident in compared_row_idents.only_left:
        rows.append({k: _encode_as_new(v) for k, v in left.rows_by_ident[ident].items()})

    for ident in compared_row_idents.both:
        # Note: Rows which have at least one change also provide all table fields.
        # Example:
        # If the version of a package (below "Software > Packages") has changed from 1.0 to 2.0
        # then it would be very annoying if the rest of the row is not shown.
        if (
            compared_dict_result := _DeltaDict.compare(
                left=left.rows_by_ident[ident],
                right=right.rows_by_ident[ident],
                keep_identical=True,
            )
        ).has_changes:
            rows.append(compared_dict_result.result)

    for ident in compared_row_idents.only_right:
        rows.append({k: _encode_as_removed(v) for k, v in right.rows_by_ident[ident].items()})

    return ImmutableDeltaTable(
        key_columns=sorted(set(left.key_columns).union(right.key_columns)),
        rows=rows,
    )


def _compare_trees(left: ImmutableTree, right: ImmutableTree) -> ImmutableDeltaTree:
    nodes: dict[SDNodeName, ImmutableDeltaTree] = {}

    compared_node_names = _DictKeys.compare(
        left=set(left.nodes_by_name),
        right=set(right.nodes_by_name),
    )

    for name in compared_node_names.only_left:
        if child_left := left.nodes_by_name[name]:
            nodes[name] = ImmutableDeltaTree.from_tree(
                tree=child_left,
                encode_as=_encode_as_new,
            )

    for name in compared_node_names.both:
        if (child_left := left.nodes_by_name[name]) == (child_right := right.nodes_by_name[name]):
            continue

        if (node := _compare_trees(child_left, child_right)).get_stats():
            nodes[name] = node

    for name in compared_node_names.only_right:
        if child_right := right.nodes_by_name[name]:
            nodes[name] = ImmutableDeltaTree.from_tree(
                tree=child_right,
                encode_as=_encode_as_removed,
            )

    return ImmutableDeltaTree(
        path=left.path,
        attributes=_compare_attributes(left.attributes, right.attributes),
        table=_compare_tables(left.table, right.table),
        nodes_by_name=nodes,
    )


@dataclass(frozen=True, kw_only=True)
class ImmutableAttributes:
    pairs: Mapping[SDKey, SDValue] = field(default_factory=dict)
    retentions: Mapping[SDKey, RetentionInterval] = field(default_factory=dict)

    def __len__(self) -> int:
        # The attribute 'pairs' is decisive. Other attributes like 'retentions' have no impact
        # if there are no pairs.
        return len(self.pairs)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, _MutableAttributes | ImmutableAttributes):
            return NotImplemented
        return self.pairs == other.pairs

    @property
    def bare(self) -> SDBareAttributes:
        # Useful for debugging; no restrictions
        return {
            "Pairs": self.pairs,
            "Retentions": {k: _serialize_retention_interval(v) for k, v in self.retentions.items()},
        }


@dataclass(frozen=True, kw_only=True)
class ImmutableTable:
    key_columns: Sequence[SDKey] = field(default_factory=list)
    rows_by_ident: Mapping[SDRowIdent, Mapping[SDKey, SDValue]] = field(default_factory=dict)
    retentions: Mapping[SDRowIdent, Mapping[SDKey, RetentionInterval]] = field(default_factory=dict)

    def __len__(self) -> int:
        # The attribute 'rows' is decisive. Other attributes like 'key_columns' or 'retentions'
        # have no impact if there are no rows.
        return sum(map(len, self.rows_by_ident.values()))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, _MutableTable | ImmutableTable):
            return NotImplemented

        compared_row_idents = _DictKeys.compare(
            left=set(self.rows_by_ident),
            right=set(other.rows_by_ident),
        )

        if compared_row_idents.only_left:
            return False

        if compared_row_idents.only_right:
            return False

        return all(
            self.rows_by_ident[i] == other.rows_by_ident[i] for i in compared_row_idents.both
        )

    @property
    def rows(self) -> Sequence[Mapping[SDKey, SDValue]]:
        return list(self.rows_by_ident.values())

    @property
    def rows_with_retentions(
        self,
    ) -> Sequence[Mapping[SDKey, tuple[SDValue, RetentionInterval | None]]]:
        return [
            {key: (value, self.retentions.get(ident, {}).get(key)) for key, value in row.items()}
            for ident, row in self.rows_by_ident.items()
        ]

    @property
    def bare(self) -> SDBareTable:
        # Useful for debugging; no restrictions
        return {
            "KeyColumns": self.key_columns,
            "RowsByIdent": self.rows_by_ident,
            "Retentions": {
                i: {k: _serialize_retention_interval(v) for k, v in ri.items()}
                for i, ri in self.retentions.items()
            },
        }


@dataclass(frozen=True, kw_only=True)
class ImmutableTree:
    path: SDPath = ()
    attributes: ImmutableAttributes = ImmutableAttributes()
    table: ImmutableTable = ImmutableTable()
    nodes_by_name: Mapping[SDNodeName, ImmutableTree] = field(default_factory=dict)

    def __len__(self) -> int:
        return sum(
            [len(self.attributes), len(self.table)]
            + [len(node) for node in self.nodes_by_name.values()]
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, MutableTree | ImmutableTree):
            return NotImplemented

        if self.attributes != other.attributes or self.table != other.table:
            return False

        compared_node_names = _DictKeys.compare(
            left=set(self.nodes_by_name),
            right=set(other.nodes_by_name),
        )

        if any(self.nodes_by_name[n] for n in compared_node_names.only_left):
            return False

        if any(other.nodes_by_name[n] for n in compared_node_names.only_right):
            return False

        return all(
            self.nodes_by_name[n] == other.nodes_by_name[n] for n in compared_node_names.both
        )

    def get_attribute(self, path: SDPath, key: SDKey) -> SDValue:
        return self.get_tree(path).attributes.pairs.get(key)

    def get_rows(self, path: SDPath) -> Sequence[Mapping[SDKey, SDValue]]:
        return self.get_tree(path).table.rows

    def get_tree(self, path: SDPath) -> ImmutableTree:
        if not path:
            return self
        return (
            ImmutableTree()
            if (node := self.nodes_by_name.get(path[0])) is None
            else node.get_tree(path[1:])
        )

    @property
    def bare(self) -> SDBareTree:
        # Useful for debugging; no restrictions
        return {
            "Path": self.path,
            "Attributes": self.attributes.bare,
            "Table": self.table.bare,
            "Nodes": {name: node.bare for name, node in self.nodes_by_name.items()},
        }

    def __str__(self) -> str:
        return f"{self.__class__.__name__}({pprint.pformat(self.bare)})"


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
    attributes: ImmutableDeltaAttributes, filter_tree_: _FilterTree
) -> ImmutableDeltaAttributes:
    return ImmutableDeltaAttributes(pairs=filter_tree_.filter_pairs(attributes.pairs))


def _filter_delta_table(
    table: ImmutableDeltaTable, filter_tree_: _FilterTree
) -> ImmutableDeltaTable:
    return ImmutableDeltaTable(
        key_columns=table.key_columns,
        rows=[filtered_row for row in table.rows if (filtered_row := filter_tree_.filter_row(row))],
    )


def _filter_delta_tree(tree: ImmutableDeltaTree, filter_tree_: _FilterTree) -> ImmutableDeltaTree:
    return ImmutableDeltaTree(
        path=tree.path,
        attributes=_filter_delta_attributes(tree.attributes, filter_tree_),
        table=_filter_delta_table(tree.table, filter_tree_),
        nodes_by_name={
            name: filtered_node
            for name in filter_tree_.filter_node_names(set(tree.nodes_by_name))
            if (
                filtered_node := _filter_delta_tree(
                    tree.nodes_by_name.get(name, ImmutableDeltaTree(path=tree.path + (name,))),
                    filter_tree_.filters_by_name.get(name, _FilterTree()),
                )
            )
        },
    )


def filter_delta_tree(
    tree: ImmutableDeltaTree, filters: Iterable[SDFilterChoice]
) -> ImmutableDeltaTree:
    return _filter_delta_tree(tree, _make_filter_tree(filters))


_SDEncodeAs = Callable[[SDValue], SDDeltaValue]
SDDeltaCounter = Counter[Literal["new", "changed", "removed"]]


def _compute_delta_stats(dict_: Mapping[SDKey, SDDeltaValue]) -> SDDeltaCounter:
    counter: SDDeltaCounter = Counter()
    for delta_value in dict_.values():
        match [delta_value.old is None, delta_value.new is None]:
            case [True, False]:
                counter["new"] += 1
            case [False, True]:
                counter["removed"] += 1
            case [False, False] if delta_value.old != delta_value.new:
                counter["changed"] += 1
    return counter


@dataclass(frozen=True, kw_only=True)
class ImmutableDeltaAttributes:
    pairs: Mapping[SDKey, SDDeltaValue] = field(default_factory=dict)

    def __len__(self) -> int:
        return len(self.pairs)

    @classmethod
    def from_attributes(
        cls, *, attributes: ImmutableAttributes, encode_as: _SDEncodeAs
    ) -> ImmutableDeltaAttributes:
        return cls(pairs={key: encode_as(value) for key, value in attributes.pairs.items()})

    def get_stats(self) -> SDDeltaCounter:
        return _compute_delta_stats(self.pairs)

    @property
    def bare(self) -> SDBareDeltaAttributes:
        # Useful for debugging; no restrictions
        return {"Pairs": {k: _serialize_delta_value(v) for k, v in self.pairs.items()}}


@dataclass(frozen=True, kw_only=True)
class ImmutableDeltaTable:
    key_columns: Sequence[SDKey] = field(default_factory=list)
    rows: Sequence[Mapping[SDKey, SDDeltaValue]] = field(default_factory=list)

    def __len__(self) -> int:
        return sum(map(len, self.rows))

    @classmethod
    def from_table(cls, *, table: ImmutableTable, encode_as: _SDEncodeAs) -> ImmutableDeltaTable:
        return cls(
            key_columns=table.key_columns,
            rows=[{key: encode_as(value) for key, value in row.items()} for row in table.rows],
        )

    def get_stats(self) -> SDDeltaCounter:
        counter: SDDeltaCounter = Counter()
        for row in self.rows:
            counter.update(_compute_delta_stats(row))
        return counter

    @property
    def bare(self) -> SDBareDeltaTable:
        # Useful for debugging; no restrictions
        return {
            "KeyColumns": self.key_columns,
            "Rows": [{k: _serialize_delta_value(v) for k, v in r.items()} for r in self.rows],
        }


@dataclass(frozen=True, kw_only=True)
class ImmutableDeltaTree:
    path: SDPath = ()
    attributes: ImmutableDeltaAttributes = ImmutableDeltaAttributes()
    table: ImmutableDeltaTable = ImmutableDeltaTable()
    nodes_by_name: Mapping[SDNodeName, ImmutableDeltaTree] = field(default_factory=dict)

    def __len__(self) -> int:
        return sum(
            [
                len(self.attributes),
                len(self.table),
            ]
            + [len(node) for node in self.nodes_by_name.values()]
        )

    @classmethod
    def from_tree(cls, *, tree: ImmutableTree, encode_as: _SDEncodeAs) -> ImmutableDeltaTree:
        return cls(
            path=tree.path,
            attributes=ImmutableDeltaAttributes.from_attributes(
                attributes=tree.attributes,
                encode_as=encode_as,
            ),
            table=ImmutableDeltaTable.from_table(
                table=tree.table,
                encode_as=encode_as,
            ),
            nodes_by_name={
                name: cls.from_tree(
                    tree=child,
                    encode_as=encode_as,
                )
                for name, child in tree.nodes_by_name.items()
            },
        )

    def get_tree(self, path: SDPath) -> ImmutableDeltaTree:
        if not path:
            return self
        node = self.nodes_by_name.get(path[0])
        return ImmutableDeltaTree() if node is None else node.get_tree(path[1:])

    def get_stats(self) -> SDDeltaCounter:
        counter: SDDeltaCounter = Counter()
        counter.update(self.attributes.get_stats())
        counter.update(self.table.get_stats())
        for node in self.nodes_by_name.values():
            counter.update(node.get_stats())
        return counter

    @property
    def bare(self) -> SDBareDeltaTree:
        # Useful for debugging; no restrictions
        return {
            "Path": self.path,
            "Attributes": self.attributes.bare,
            "Table": self.table.bare,
            "Nodes": {edge: node.bare for edge, node in self.nodes_by_name.items()},
        }

    def __str__(self) -> str:
        return f"{self.__class__.__name__}({pprint.pformat(self.bare)})"


# .
#   .--IO------------------------------------------------------------------.
#   |                              ___ ___                                 |
#   |                             |_ _/ _ \                                |
#   |                              | | | | |                               |
#   |                              | | |_| |                               |
#   |                             |___\___/                                |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def _transform_tree_path(tree_path: TreePath, mtime: float) -> None:
    with store.locked(tree_path.path), store.locked(tree_path.legacy):
        if raw_tree := store.load_object_from_file(tree_path.legacy, default=None):
            _save_raw_tree(tree_path, raw_tree)
            os.utime(tree_path.path, (mtime, mtime))
    tree_path.legacy.unlink(missing_ok=True)


def _transform_tree_path_gz(tree_path_gz: TreePathGz, mtime: float) -> None:
    with store.locked(tree_path_gz.path), store.locked(tree_path_gz.legacy):
        if gzipped := store.load_bytes_from_file(tree_path_gz.legacy, default=b""):
            _save_raw_tree_gz(tree_path_gz, parse_from_gzipped(gzipped))
            os.utime(tree_path_gz.path, (mtime, mtime))
    tree_path_gz.legacy.unlink(missing_ok=True)


def transform(tree_path: TreePath | TreePathGz, mtime: float) -> None:
    match tree_path:
        case TreePath():
            _transform_tree_path(tree_path, mtime)
        case TreePathGz():
            _transform_tree_path_gz(tree_path, mtime)


def rename(
    omd_root: Path, *, old_host_name: HostName, new_host_name: HostName
) -> Sequence[Literal["inv", "invarch"]]:
    inv_paths = InventoryPaths(omd_root)
    old_inv_tree_path = inv_paths.inventory_tree(HostName(old_host_name))
    old_inv_tree_path_gz = inv_paths.inventory_tree_gz(HostName(old_host_name))
    old_stat_tree_path = inv_paths.status_data_tree(HostName(old_host_name))
    new_inv_tree_path = inv_paths.inventory_tree(HostName(new_host_name))
    new_inv_tree_path_gz = inv_paths.inventory_tree_gz(HostName(new_host_name))
    new_stat_tree_path = inv_paths.status_data_tree(HostName(new_host_name))
    actions: set[Literal["inv", "invarch"]] = set()
    for old_file_path, new_file_path in [
        (old_inv_tree_path.path, new_inv_tree_path.path),
        (old_inv_tree_path.legacy, new_inv_tree_path.legacy),
        (old_inv_tree_path_gz.path, new_inv_tree_path_gz.path),
        (old_inv_tree_path_gz.legacy, new_inv_tree_path_gz.legacy),
        (old_stat_tree_path.path, new_stat_tree_path.path),
        (old_stat_tree_path.legacy, new_stat_tree_path.legacy),
    ]:
        try:
            old_file_path.rename(new_file_path)
            actions.add("inv")
        except FileNotFoundError:
            pass

    for old_directory, new_directory in [
        (
            inv_paths.archive_host(HostName(old_host_name)),
            inv_paths.archive_host(HostName(new_host_name)),
        ),
        (
            inv_paths.delta_cache_host(HostName(old_host_name)),
            inv_paths.delta_cache_host(HostName(new_host_name)),
        ),
    ]:
        try:
            shutil.move(old_directory, new_directory)
            actions.add("invarch")
        except FileNotFoundError:
            pass

    return list(actions)


def _load_tree_from_tree_path(tree_path: TreePath) -> ImmutableTree:
    if raw_tree := store.load_text_from_file(tree_path.path):
        return deserialize_tree(json.loads(raw_tree))
    if raw_tree := store.load_object_from_file(tree_path.legacy, default=None):
        return deserialize_tree(raw_tree)
    return ImmutableTree()


class SDMeta(TypedDict):
    version: Literal["1"]
    do_archive: bool


def _save_raw_tree(tree_path: TreePath, raw_tree: SDRawTree) -> None:
    tree_path.path.parent.mkdir(parents=True, exist_ok=True)
    store.save_text_to_file(tree_path.path, json.dumps(raw_tree) + "\n")


def _save_raw_tree_gz(tree_path_gz: TreePathGz, meta_and_raw_tree: SDMetaAndRawTree) -> None:
    tree_path_gz.path.parent.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb") as f:
        f.write((json.dumps(meta_and_raw_tree) + "\n").encode("utf-8"))
    store.save_bytes_to_file(tree_path_gz.path, buf.getvalue())


@dataclass(frozen=True)
class _TreePathMTime:
    mtime: float
    is_json: bool


def _compute_mtime(tree_path: TreePath) -> _TreePathMTime | None:
    try:
        return _TreePathMTime(tree_path.path.stat().st_mtime, True)
    except FileNotFoundError:
        # TODO CMK-23408
        try:
            return _TreePathMTime(tree_path.legacy.stat().st_mtime, False)
        except FileNotFoundError:
            return None


def _archive_inventory_tree(inv_paths: InventoryPaths, host_name: HostName) -> None:
    tree_path = inv_paths.inventory_tree(host_name)
    if (tree_path_mtime := _compute_mtime(tree_path)) is None:
        return

    tree_path_gz = inv_paths.inventory_tree_gz(host_name)
    archive_tree = inv_paths.archive_tree(host_name, int(tree_path_mtime.mtime))

    if tree_path_mtime.is_json:
        inv_paths.archive_host(host_name).mkdir(parents=True, exist_ok=True)
        tree_path.path.rename(archive_tree.path)
        tree_path_gz.path.unlink(missing_ok=True)
        tree_path.legacy.unlink(missing_ok=True)
        tree_path_gz.legacy.unlink(missing_ok=True)
        return

    if raw_tree := store.load_object_from_file(tree_path.legacy, default=None):
        inv_paths.archive_host(host_name).mkdir(parents=True, exist_ok=True)
        store.save_text_to_file(archive_tree.path, json.dumps(raw_tree))
        tree_path.legacy.unlink(missing_ok=True)
        tree_path_gz.legacy.unlink(missing_ok=True)


def make_meta(*, do_archive: bool) -> SDMeta:
    return SDMeta(version="1", do_archive=do_archive)


class SDMetaAndRawTree(TypedDict):
    meta: SDMeta
    raw_tree: SDRawTree


def _parse_raw_meta(raw_meta: object) -> SDMeta:
    if not isinstance(raw_meta, dict):
        raise TypeError(raw_meta)
    if not isinstance(version := raw_meta.get("version"), str):
        raise TypeError(version)
    if not isinstance(do_archive := raw_meta.get("do_archive"), bool):
        raise TypeError(do_archive)
    match version:
        case "1":
            return SDMeta(version=version, do_archive=do_archive)
        case _:
            raise ValueError(version)


def _parse_raw_tree(raw_tree: object) -> SDRawTree:
    if not isinstance(raw_tree, dict):
        raise TypeError(raw_tree)
    return SDRawTree(
        Attributes=raw_tree.get("Attributes", {}),
        Table=raw_tree.get("Table", {}),
        Nodes=raw_tree.get("Nodes", {}),
    )


def _parse_from_unzipped(raw: object) -> SDMetaAndRawTree:
    if not isinstance(raw, dict):
        raise TypeError(raw)
    if set(raw) == {"meta", "raw_tree"}:
        # Handle future versions
        return SDMetaAndRawTree(
            meta=_parse_raw_meta(raw.get("meta")),
            raw_tree=_parse_raw_tree(raw.get("raw_tree")),
        )
    return SDMetaAndRawTree(
        meta=SDMeta(
            version="1",
            do_archive=raw.get("meta_do_archive", True),
        ),
        raw_tree=SDRawTree(
            Attributes=raw.get("Attributes", {}),
            Table=raw.get("Table", {}),
            Nodes=raw.get("Nodes", {}),
        ),
    )


def _parse_dump(dump: bytes) -> object:
    try:
        return json.loads(dump.decode("utf-8"))
    except json.JSONDecodeError:
        # TODO CMK-23408
        return ast.literal_eval(dump.decode("utf-8"))


def parse_from_gzipped(gzipped: bytes) -> SDMetaAndRawTree:
    # Note: Since Checkmk 2.1 we explicitly extract "Attributes", "Table" or "Nodes" while
    # deserialization. This means that "meta_*" are not taken into account and we stay
    # compatible.
    return _parse_from_unzipped(_parse_dump(gzip.GzipFile(fileobj=io.BytesIO(gzipped)).read()))


def parse_from_raw_status_data_tree(dump: bytes) -> ImmutableTree:
    return deserialize_tree(_parse_dump(dump))


class RawInventoryStore:
    def __init__(self, omd_root: Path) -> None:
        self.inv_paths = InventoryPaths(omd_root)

    def save_meta_and_raw_inventory_tree(
        self, *, host_name: HostName, meta_and_raw_tree: SDMetaAndRawTree, timestamp: int
    ) -> None:
        tree_path = self.inv_paths.inventory_tree(host_name)
        _save_raw_tree(tree_path, meta_and_raw_tree["raw_tree"])
        tree_path.legacy.unlink(missing_ok=True)
        os.utime(tree_path.path, (timestamp, timestamp))

        tree_path_gz = self.inv_paths.inventory_tree_gz(host_name)
        _save_raw_tree_gz(tree_path_gz, meta_and_raw_tree)
        tree_path_gz.legacy.unlink(missing_ok=True)
        os.utime(tree_path_gz.path, (timestamp, timestamp))

    def archive_inventory_tree(self, *, host_name: HostName) -> None:
        _archive_inventory_tree(self.inv_paths, host_name)


class InventoryStore:
    def __init__(self, omd_root: Path) -> None:
        self.inv_paths = InventoryPaths(omd_root)

    def load_inventory_tree(self, *, host_name: HostName) -> ImmutableTree:
        return _load_tree_from_tree_path(self.inv_paths.inventory_tree(host_name))

    def save_inventory_tree(
        self, *, host_name: HostName, tree: MutableTree | ImmutableTree, meta: SDMeta
    ) -> None:
        raw_tree = serialize_tree(tree)

        tree_path = self.inv_paths.inventory_tree(host_name)
        _save_raw_tree(tree_path, raw_tree)
        tree_path.legacy.unlink(missing_ok=True)

        tree_path_gz = self.inv_paths.inventory_tree_gz(host_name)
        _save_raw_tree_gz(tree_path_gz, SDMetaAndRawTree(meta=meta, raw_tree=raw_tree))
        tree_path_gz.legacy.unlink(missing_ok=True)

        # Inform Livestatus about the latest inventory update
        self.inv_paths.inventory_marker_file.touch()

    def remove_inventory_tree(self, *, host_name: HostName) -> None:
        tree_path = self.inv_paths.inventory_tree(host_name)
        tree_path.path.unlink(missing_ok=True)
        tree_path.legacy.unlink(missing_ok=True)

        tree_path_gz = self.inv_paths.inventory_tree_gz(host_name)
        tree_path_gz.path.unlink(missing_ok=True)
        tree_path_gz.legacy.unlink(missing_ok=True)

    def load_status_data_tree(self, *, host_name: HostName) -> ImmutableTree:
        return _load_tree_from_tree_path(self.inv_paths.status_data_tree(host_name))

    def save_status_data_tree(
        self, *, host_name: HostName, tree: MutableTree | ImmutableTree
    ) -> None:
        tree_path = self.inv_paths.status_data_tree(host_name)
        _save_raw_tree(tree_path, serialize_tree(tree))
        tree_path.legacy.unlink(missing_ok=True)

        # Inform Livestatus about the latest inventory update
        self.inv_paths.status_data_marker_file.touch()

    def remove_status_data_tree(self, *, host_name: HostName) -> None:
        tree_path = self.inv_paths.status_data_tree(host_name)
        tree_path.path.unlink(missing_ok=True)
        tree_path.legacy.unlink(missing_ok=True)

    def load_previous_inventory_tree(self, *, host_name: HostName) -> ImmutableTree:
        if tree := _load_tree_from_tree_path(self.inv_paths.inventory_tree(host_name)):
            return tree

        try:
            latest_archive_file_path = max(
                self.inv_paths.archive_host(host_name).iterdir(),
                key=lambda fp: int(fp.with_suffix("").name),
            )
        except (FileNotFoundError, ValueError):
            return ImmutableTree()

        return _load_tree_from_tree_path(
            TreePath.from_archive_or_delta_cache_file_path(latest_archive_file_path)
        )

    def archive_inventory_tree(self, *, host_name: HostName) -> None:
        _archive_inventory_tree(self.inv_paths, host_name)


@dataclass(frozen=True)
class HistoryDeltaPath:
    file_path: Path
    previous_timestamp: int
    current_timestamp: int


@dataclass(frozen=True)
class HistoryPath:
    tree_path: TreePath
    timestamp: int


@dataclass(frozen=True, kw_only=True)
class HistoryArchivePath:
    previous: HistoryPath
    current: HistoryPath

    @property
    def current_timestamp(self) -> int:
        return self.current.timestamp


@dataclass(frozen=True, kw_only=True)
class HistoryEntry:
    previous_timestamp: int
    current_timestamp: int
    new: int
    changed: int
    removed: int
    delta_tree: ImmutableDeltaTree

    @classmethod
    def from_raw(
        cls,
        *,
        previous_timestamp: int,
        current_timestamp: int,
        raw: tuple[int, int, int, SDRawDeltaTree],
    ) -> HistoryEntry:
        new, changed, removed, raw_delta_tree = raw
        return cls(
            previous_timestamp=previous_timestamp,
            current_timestamp=current_timestamp,
            new=new,
            changed=changed,
            removed=removed,
            delta_tree=deserialize_delta_tree(raw_delta_tree),
        )

    @classmethod
    def from_delta_tree(
        cls,
        *,
        previous_timestamp: int,
        current_timestamp: int,
        delta_tree: ImmutableDeltaTree,
    ) -> HistoryEntry:
        delta_stats = delta_tree.get_stats()
        return cls(
            previous_timestamp=previous_timestamp,
            current_timestamp=current_timestamp,
            new=delta_stats["new"],
            changed=delta_stats["changed"],
            removed=delta_stats["removed"],
            delta_tree=delta_tree,
        )


class HistoryStore:
    def __init__(self, omd_root: Path) -> None:
        self.inv_paths = InventoryPaths(omd_root)
        self._lookup: dict[tuple[Path, Path], ImmutableTree] = {}

    def _collect_paths_from_delta_cache(
        self, host_name: HostName
    ) -> Iterator[Result[HistoryDeltaPath, Path]]:
        try:
            file_paths = list(self.inv_paths.delta_cache_host(host_name).iterdir())
        except FileNotFoundError:
            return

        for file_path in file_paths:
            try:
                previous_name, current_name = file_path.with_suffix("").name.split("_")
                previous_timestamp = -1 if previous_name == "None" else int(previous_name)
                current_timestamp = int(current_name)
            except ValueError:
                yield Error(file_path)
                continue

            yield OK(
                HistoryDeltaPath(
                    file_path=file_path,
                    previous_timestamp=previous_timestamp,
                    current_timestamp=current_timestamp,
                )
            )

    def _collect_paths_from_archive(
        self, host_name: HostName
    ) -> Iterator[Result[HistoryPath, Path]]:
        try:
            file_paths = list(self.inv_paths.archive_host(host_name).iterdir())
        except FileNotFoundError:
            return

        yield OK(HistoryPath(TreePath(path=Path(), legacy=Path()), -1))
        for file_path in file_paths:
            try:
                yield OK(
                    HistoryPath(
                        tree_path=TreePath.from_archive_or_delta_cache_file_path(file_path),
                        timestamp=int(file_path.with_suffix("").name),
                    )
                )
            except ValueError:
                yield Error(file_path)

        tree_path = self.inv_paths.inventory_tree(host_name)
        try:
            yield OK(
                HistoryPath(
                    tree_path=tree_path,
                    timestamp=int(tree_path.path.stat().st_mtime),
                )
            )
        except FileNotFoundError:
            # TODO CMK-23408
            try:
                yield OK(
                    HistoryPath(
                        tree_path=tree_path,
                        timestamp=int(tree_path.legacy.stat().st_mtime),
                    )
                )
            except FileNotFoundError:
                pass

    def collect_history_paths(
        self, *, host_name: HostName
    ) -> Iterator[Result[HistoryDeltaPath | HistoryArchivePath, Path]]:
        known_paths: dict[tuple[HostName, int, int], HistoryDeltaPath | HistoryArchivePath] = {}
        for result_from_delta_cache in self._collect_paths_from_delta_cache(host_name):
            if result_from_delta_cache.is_ok():
                known_paths[
                    (
                        host_name,
                        result_from_delta_cache.ok.previous_timestamp,
                        result_from_delta_cache.ok.current_timestamp,
                    )
                ] = result_from_delta_cache.ok
            else:
                yield result_from_delta_cache

        results_from_archive = list(self._collect_paths_from_archive(host_name))
        sorted_paths_from_archive = sorted(
            [r.ok for r in results_from_archive if r.is_ok()], key=lambda p: p.timestamp
        )
        for previous, current in zip(sorted_paths_from_archive, sorted_paths_from_archive[1:]):
            if (key := (host_name, previous.timestamp, current.timestamp)) not in known_paths:
                known_paths[key] = HistoryArchivePath(previous=previous, current=current)

        for key in sorted(known_paths, key=lambda k: k[-1]):
            yield OK(known_paths[key])

        for result_from_archive in results_from_archive:
            if result_from_archive.is_error():
                yield Error(result_from_archive.error)

    def _lookup_tree(self, tree_path: TreePath) -> ImmutableTree:
        if tree_path.path == Path() or tree_path.legacy == Path():
            return ImmutableTree()

        key = (tree_path.path, tree_path.legacy)
        if key in self._lookup:
            return self._lookup[key]

        return self._lookup.setdefault(key, _load_tree_from_tree_path(tree_path))

    def load_history_entry(
        self, *, host_name: HostName, path: HistoryDeltaPath | HistoryArchivePath
    ) -> Result[HistoryEntry, Sequence[Path]]:
        match path:
            case HistoryDeltaPath():
                try:
                    raw = (
                        json.loads(store.load_text_from_file(path.file_path))
                        if path.file_path.suffix == ".json"
                        else store.load_object_from_file(path.file_path, default=None)
                    )
                except MKGeneralException:
                    return Error([path.file_path])

                if raw is None:
                    return Error([path.file_path])

                return OK(
                    HistoryEntry.from_raw(
                        previous_timestamp=path.previous_timestamp,
                        current_timestamp=path.current_timestamp,
                        raw=raw,
                    )
                )

            case HistoryArchivePath():
                entry = HistoryEntry.from_delta_tree(
                    previous_timestamp=path.previous.timestamp,
                    current_timestamp=path.current.timestamp,
                    delta_tree=_compare_trees(
                        self._lookup_tree(path.current.tree_path),
                        self._lookup_tree(path.previous.tree_path),
                    ),
                )

                if entry.new or entry.changed or entry.removed:
                    if path.current.tree_path != self.inv_paths.inventory_tree(host_name):
                        self.save_history_entry(host_name=host_name, history_entry=entry)
                    return OK(entry)

                return Error(
                    [
                        path.current.tree_path.path,
                        path.current.tree_path.legacy,
                        path.current.tree_path.path,
                        path.current.tree_path.legacy,
                    ]
                )

    def save_history_entry(self, *, host_name: HostName, history_entry: HistoryEntry) -> None:
        delta_cache_tree = self.inv_paths.delta_cache_tree(
            host_name,
            history_entry.previous_timestamp,
            history_entry.current_timestamp,
        )
        self.inv_paths.delta_cache_host(host_name).mkdir(parents=True, exist_ok=True)
        store.save_text_to_file(
            delta_cache_tree.path,
            json.dumps(
                (
                    history_entry.new,
                    history_entry.changed,
                    history_entry.removed,
                    serialize_delta_tree(history_entry.delta_tree),
                )
            ),
        )
        delta_cache_tree.legacy.unlink(missing_ok=True)


@dataclass(frozen=True)
class History:
    entries: Sequence[HistoryEntry]
    corrupted: Sequence[Path]


def load_history(
    history_store: HistoryStore,
    host_name: HostName,
    *,
    history_paths_filter: Callable[
        [Sequence[HistoryDeltaPath | HistoryArchivePath]],
        Sequence[HistoryDeltaPath | HistoryArchivePath],
    ],
    delta_tree_filters: Sequence[SDFilterChoice] | None,
) -> History:
    paths = []
    corrupted: set[Path] = set()
    for path_result in history_store.collect_history_paths(host_name=host_name):
        if path_result.is_ok():
            paths.append(path_result.ok)
        else:
            corrupted.add(path_result.error)

    entries = []
    for path in history_paths_filter(paths):
        if (
            entry_result := history_store.load_history_entry(host_name=host_name, path=path)
        ).is_ok():
            entries.append(entry_result.ok)
        else:
            corrupted.update(entry_result.error)

    if delta_tree_filters is None:
        return History(entries=entries, corrupted=list(corrupted))

    return History(
        entries=[
            HistoryEntry.from_delta_tree(
                previous_timestamp=e.previous_timestamp,
                current_timestamp=e.current_timestamp,
                delta_tree=d,
            )
            for e in entries
            if (d := filter_delta_tree(e.delta_tree, delta_tree_filters))
        ],
        corrupted=list(corrupted),
    )
