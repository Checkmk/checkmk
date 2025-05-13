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
from typing import Generic, Literal, NamedTuple, Self, TypedDict, TypeVar

from cmk.utils import store
from cmk.utils.hostaddress import HostName

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
# TODO Centralize different stores and loaders of tree files:
#   - inventory/HOSTNAME, inventory/HOSTNAME.gz, inventory/.last
#   - inventory_archive/HOSTNAME/TIMESTAMP,
#   - inventory_delta_cache/HOSTNAME/TIMESTAMP_{TIMESTAMP,None}
#   - status_data/HOSTNAME, status_data/HOSTNAME.gz

SDNodeName = str
SDPath = tuple[SDNodeName, ...]

SDKey = str
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
    def from_previous(cls, other: RetentionInterval) -> RetentionInterval:
        return cls(other.cached_at, other.cache_interval, other.retention_interval, "previous")

    @classmethod
    def from_config(
        cls, cached_at: int, cache_interval: int, retention_interval: int
    ) -> RetentionInterval:
        return cls(cached_at, cache_interval, retention_interval, "current")

    @property
    def keep_until(self) -> int:
        return self.cached_at + self.cache_interval + self.retention_interval

    @classmethod
    def deserialize(
        cls,
        raw_retention_interval: (
            tuple[int, int, int] | tuple[int, int, int, Literal["previous", "current"]]
        ),
    ) -> RetentionInterval:
        return (
            cls(*raw_retention_interval)
            if len(raw_retention_interval) == 4
            else cls(*raw_retention_interval[:3], "current")
        )

    def serialize(self) -> tuple[int, int, int, Literal["previous", "current"]]:
        return self.cached_at, self.cache_interval, self.retention_interval, self.source


@dataclass(frozen=True)
class UpdateResult:
    reasons_by_path: dict[SDPath, list[str]] = field(default_factory=dict)

    @property
    def save_tree(self) -> bool:
        return bool(self.reasons_by_path)

    def add_attr_reason(self, path: SDPath, title: str, iterable: Iterable[str]) -> None:
        self.reasons_by_path.setdefault(path, []).append(
            f"[Attributes] {title}: {', '.join(sorted(iterable))}"
        )

    def add_row_reason(
        self, path: SDPath, ident: SDRowIdent, title: str, iterable: Iterable[str]
    ) -> None:
        self.reasons_by_path.setdefault(path, []).append(
            f"[Table] '{', '.join(map(str, ident))}': {title}: {', '.join(sorted(iterable))}"
        )

    def __str__(self) -> str:
        if not self.reasons_by_path:
            return "No tree update.\n"

        lines = ["Updated inventory tree:"]
        for path, reasons in self.reasons_by_path.items():
            lines.append(f"  Path '{' > '.join(path)}':")
            lines.extend(f"    {r}" for r in sorted(reasons))
        return "\n".join(lines) + "\n"


def parse_visible_raw_path(raw_path: str) -> SDPath:
    return tuple(part for part in raw_path.split(".") if part)


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
    only_old: set[_T]
    both: set[_T]
    only_new: set[_T]

    @classmethod
    def compare(cls, *, left: set[_T], right: set[_T]) -> Self:
        """
        Returns the set relationships of the keys between two dictionaries:
        - relative complement of right in left
        - intersection of both
        - relative complement of left in right
        """
        return cls(
            only_old=left - right,
            both=left.intersection(right),
            only_new=right - left,
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


class SDFilterChoice(NamedTuple):
    path: SDPath
    pairs: Literal["nothing", "all"] | Sequence[SDKey]
    columns: Literal["nothing", "all"] | Sequence[SDKey]
    nodes: Literal["nothing", "all"] | Sequence[SDNodeName]


class _SDRetentionFilterChoice(NamedTuple):
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
        self,
        choice: Literal["nothing", "all"] | Sequence[SDKey],
        cache_info: tuple[int, int],
    ) -> None:
        self._pairs.append(_SDRetentionFilterChoice(choice, cache_info))

    def add_columns_choice(
        self,
        choice: Literal["nothing", "all"] | Sequence[SDKey],
        cache_info: tuple[int, int],
    ) -> None:
        self._columns.append(_SDRetentionFilterChoice(choice, cache_info))


_CT = TypeVar("_CT", SDKey, SDNodeName)


def _make_filter_func(
    choice: Literal["nothing", "all"] | Sequence[_CT],
) -> Callable[[_CT], bool]:
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
    filter_tree = _FilterTree()
    for f in filters:
        filter_tree.append(f.path, f)
    return filter_tree


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
        if not isinstance(other, (_MutableAttributes, ImmutableAttributes)):
            return NotImplemented
        return self.pairs == other.pairs

    def add(self, pairs: Mapping[SDKey, SDValue]) -> None:
        self.pairs.update(pairs)

    def update(
        self,
        now: int,
        other: ImmutableAttributes,
        path: SDPath,
        interval: int,
        choice: _SDRetentionFilterChoice,
        update_result: UpdateResult,
    ) -> None:
        filter_func = _make_filter_func(choice.choice)
        retention_interval = RetentionInterval.from_config(*choice.cache_info, interval)
        compared_keys = _DictKeys.compare(
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
        for key in compared_keys.only_old:
            pairs.setdefault(key, other.pairs[key])
            retentions[key] = RetentionInterval.from_previous(other.retentions[key])

        for key in compared_keys.both.union(compared_keys.only_new):
            retentions[key] = retention_interval

        if pairs:
            self.add(pairs)
            update_result.add_attr_reason(path, "Added pairs", pairs)

        if retentions:
            self.retentions = retentions
            update_result.add_attr_reason(
                path,
                "Keep until",
                [f"{k} ({v.keep_until})" for k, v in retentions.items()],
            )

    def serialize(self) -> SDRawAttributes:
        raw_attributes: SDRawAttributes = {}
        if self.pairs:
            raw_attributes["Pairs"] = self.pairs
        if self.retentions:
            raw_attributes["Retentions"] = {k: v.serialize() for k, v in self.retentions.items()}
        return raw_attributes

    @property
    def bare(self) -> SDBareAttributes:
        # Useful for debugging; no restrictions
        return {
            "Pairs": self.pairs,
            "Retentions": {k: v.serialize() for k, v in self.retentions.items()},
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
        if not isinstance(other, (_MutableTable, ImmutableTable)):
            return NotImplemented

        compared_row_idents = _DictKeys.compare(
            left=set(self.rows_by_ident),
            right=set(other.rows_by_ident),
        )

        if compared_row_idents.only_old:
            return False

        if compared_row_idents.only_new:
            return False

        return all(
            self.rows_by_ident[i] == other.rows_by_ident[i] for i in compared_row_idents.both
        )

    def _add_key_columns(self, key_columns: Iterable[SDKey]) -> None:
        self.key_columns = sorted(set(self.key_columns).union(key_columns))

    def add(self, key_columns: Iterable[SDKey], rows: Sequence[Mapping[SDKey, SDValue]]) -> None:
        self._add_key_columns(key_columns)
        for row in rows:
            self._add_row(_make_row_ident(self.key_columns, row), row)

    def _add_row(self, ident: SDRowIdent, row: Mapping[SDKey, SDValue]) -> None:
        if row:
            self.rows_by_ident.setdefault(ident, {}).update(row)

    def update(  # pylint: disable=too-many-branches
        self,
        now: int,
        other: ImmutableTable,
        path: SDPath,
        interval: int,
        choice: _SDRetentionFilterChoice,
        update_result: UpdateResult,
    ) -> None:
        filter_func = _make_filter_func(choice.choice)
        retention_interval = RetentionInterval.from_config(*choice.cache_info, interval)
        self._add_key_columns(other.key_columns)
        old_filtered_rows = {
            ident: filtered_row
            for ident, row in other.rows_by_ident.items()
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
            for ident, row in self.rows_by_ident.items()
            if (filtered_row := _get_filtered_dict(row, filter_func))
        }
        compared_row_idents = _DictKeys.compare(
            left=set(old_filtered_rows),
            right=set(self_filtered_rows),
        )

        retentions: dict[SDRowIdent, dict[SDKey, RetentionInterval]] = {}
        for ident in compared_row_idents.only_old:
            old_row: dict[SDKey, SDValue] = {}
            for key, value in old_filtered_rows[ident].items():
                old_row.setdefault(key, value)
                retentions.setdefault(ident, {})[key] = RetentionInterval.from_previous(
                    other.retentions[ident][key]
                )

            if old_row:
                # Update row with key column entries
                old_row |= {k: other.rows_by_ident[ident][k] for k in other.key_columns}
                self._add_row(ident, old_row)
                update_result.add_row_reason(path, ident, "Added row", old_row)

        for ident in compared_row_idents.both:
            compared_keys = _DictKeys.compare(
                left=set(old_filtered_rows[ident]),
                right=set(self_filtered_rows[ident]),
            )
            row: dict[SDKey, SDValue] = {}
            for key in compared_keys.only_old:
                row.setdefault(key, other.rows_by_ident[ident][key])
                retentions.setdefault(ident, {})[key] = RetentionInterval.from_previous(
                    other.retentions[ident][key]
                )

            for key in compared_keys.both.union(compared_keys.only_new):
                retentions.setdefault(ident, {})[key] = retention_interval

            if row:
                # Update row with key column entries
                row.update(
                    {
                        **{k: other.rows_by_ident[ident][k] for k in other.key_columns},
                        **{k: self.rows_by_ident[ident][k] for k in self.key_columns},
                    }
                )
                self._add_row(ident, row)
                update_result.add_row_reason(path, ident, "Added row", row)

        for ident in compared_row_idents.only_new:
            for key in self_filtered_rows[ident]:
                retentions.setdefault(ident, {})[key] = retention_interval

        if retentions:
            self.retentions = retentions
            for ident, intervals_by_key in retentions.items():
                update_result.add_row_reason(
                    path,
                    ident,
                    "Keep until",
                    [f"{k} ({v.keep_until})" for k, v in intervals_by_key.items()],
                )

    def serialize(self) -> SDRawTable:
        raw_table: SDRawTable = {}
        if self.rows_by_ident:
            raw_table.update(
                {
                    "KeyColumns": self.key_columns,
                    "Rows": list(self.rows_by_ident.values()),
                }
            )
        if self.retentions:
            raw_table["Retentions"] = {
                i: {k: v.serialize() for k, v in ri.items()} for i, ri in self.retentions.items()
            }
        return raw_table

    @property
    def bare(self) -> SDBareTable:
        # Useful for debugging; no restrictions
        return {
            "KeyColumns": self.key_columns,
            "RowsByIdent": self.rows_by_ident,
            "Retentions": {
                i: {k: v.serialize() for k, v in ri.items()} for i, ri in self.retentions.items()
            },
        }


@dataclass(frozen=True, kw_only=True)
class MutableTree:
    path: SDPath = ()
    attributes: _MutableAttributes = field(
        default_factory=lambda: _MutableAttributes()  # pylint: disable=unnecessary-lambda
    )
    table: _MutableTable = field(
        default_factory=lambda: _MutableTable()  # pylint: disable=unnecessary-lambda
    )
    nodes_by_name: dict[SDNodeName, MutableTree] = field(default_factory=dict)

    def __len__(self) -> int:
        return sum(
            [len(self.attributes), len(self.table)]
            + [len(node) for node in self.nodes_by_name.values()]
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, (MutableTree, ImmutableTree)):
            return NotImplemented

        if self.attributes != other.attributes or self.table != other.table:
            return False

        compared_node_names = _DictKeys.compare(
            left=set(self.nodes_by_name),
            right=set(other.nodes_by_name),
        )

        if any(self.nodes_by_name[n] for n in compared_node_names.only_old):
            return False

        if any(other.nodes_by_name[n] for n in compared_node_names.only_new):
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
        update_result: UpdateResult,
    ) -> None:
        node = self.setdefault_node(choices.path)
        previous_node = previous_tree.get_tree(choices.path)
        for choice in choices.pairs:
            node.attributes.update(
                now,
                previous_node.attributes,
                choices.path,
                choices.interval,
                choice,
                update_result,
            )
        for choice in choices.columns:
            node.table.update(
                now,
                previous_node.table,
                choices.path,
                choices.interval,
                choice,
                update_result,
            )

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

    def serialize(self) -> SDRawTree:
        return {
            "Attributes": self.attributes.serialize(),
            "Table": self.table.serialize(),
            "Nodes": {name: node.serialize() for name, node in self.nodes_by_name.items() if node},
        }

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


def _deserialize_legacy_attributes(
    raw_pairs: Mapping[SDKey, SDValue],
) -> ImmutableAttributes:
    return ImmutableAttributes(pairs=raw_pairs)


def _deserialize_legacy_table(
    raw_rows: Sequence[Mapping[SDKey, SDValue]],
) -> ImmutableTable:
    key_columns = sorted({k for r in raw_rows for k in r})
    rows_by_ident: dict[SDRowIdent, dict[SDKey, SDValue]] = {}
    for row in raw_rows:
        rows_by_ident.setdefault(_make_row_ident(key_columns, row), {}).update(row)

    return ImmutableTable(key_columns=key_columns, rows_by_ident=rows_by_ident)


def _deserialize_legacy_node(  # pylint: disable=too-many-branches
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

    return ImmutableTree(
        path=path,
        attributes=_deserialize_legacy_attributes(raw_pairs),
        table=_deserialize_legacy_table(raw_rows) if raw_rows else ImmutableTable(),
        nodes_by_name={
            **{
                name: _deserialize_legacy_node(
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


def _filter_attributes(
    attributes: ImmutableAttributes, filter_tree: _FilterTree
) -> ImmutableAttributes:
    return ImmutableAttributes(
        pairs=filter_tree.filter_pairs(attributes.pairs),
        retentions=attributes.retentions,
    )


def _filter_table(table: ImmutableTable, filter_tree: _FilterTree) -> ImmutableTable:
    return ImmutableTable(
        key_columns=table.key_columns,
        rows_by_ident={
            ident: filtered_row
            for ident, row in table.rows_by_ident.items()
            if (filtered_row := filter_tree.filter_row(row))
        },
        retentions=table.retentions,
    )


def _filter_tree(tree: ImmutableTree, filter_tree: _FilterTree) -> ImmutableTree:
    return ImmutableTree(
        path=tree.path,
        attributes=_filter_attributes(tree.attributes, filter_tree),
        table=_filter_table(tree.table, filter_tree),
        nodes_by_name={
            name: filtered_node
            for name in filter_tree.filter_node_names(set(tree.nodes_by_name))
            if (
                filtered_node := _filter_tree(
                    tree.nodes_by_name.get(name, ImmutableTree(path=tree.path + (name,))),
                    filter_tree.filters_by_name.get(name, _FilterTree()),
                )
            )
        },
    )


def _merge_attributes(left: ImmutableAttributes, right: ImmutableAttributes) -> ImmutableAttributes:
    return ImmutableAttributes(
        pairs={**left.pairs, **right.pairs},
        retentions={**left.retentions, **right.retentions},
    )


def _merge_tables_by_same_or_empty_key_columns(
    key_columns: Sequence[SDKey], left: ImmutableTable, right: ImmutableTable
) -> ImmutableTable:
    compared_row_idents = _DictKeys.compare(
        left=set(right.rows_by_ident),
        right=set(left.rows_by_ident),
    )

    rows_by_ident: dict[SDRowIdent, Mapping[SDKey, SDValue]] = {}
    for ident in compared_row_idents.only_old:
        rows_by_ident.setdefault(ident, right.rows_by_ident[ident])

    for ident in compared_row_idents.both:
        rows_by_ident.setdefault(
            ident,
            {
                **left.rows_by_ident[ident],
                **right.rows_by_ident[ident],
            },
        )

    for ident in compared_row_idents.only_new:
        rows_by_ident.setdefault(ident, left.rows_by_ident[ident])

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


def _merge_nodes(left: ImmutableTree, right: ImmutableTree) -> ImmutableTree:
    compared_node_names = _DictKeys.compare(
        left=set(right.nodes_by_name),
        right=set(left.nodes_by_name),
    )

    nodes_by_name: dict[SDNodeName, ImmutableTree] = {}
    for name in compared_node_names.only_old:
        nodes_by_name[name] = right.nodes_by_name[name]

    for name in compared_node_names.both:
        nodes_by_name[name] = _merge_nodes(
            left=left.nodes_by_name[name], right=right.nodes_by_name[name]
        )

    for name in compared_node_names.only_new:
        nodes_by_name[name] = left.nodes_by_name[name]

    return ImmutableTree(
        path=left.path,
        attributes=_merge_attributes(left.attributes, right.attributes),
        table=_merge_tables(left.table, right.table),
        nodes_by_name=nodes_by_name,
    )


def _encode_as_new(value: SDValue) -> tuple[None, SDValue]:
    return (None, value)


def _encode_as_removed(value: SDValue) -> tuple[SDValue, None]:
    return (value, None)


@dataclass(frozen=True, kw_only=True)
class _DeltaDict:
    result: Mapping[SDKey, tuple[SDValue, SDValue]]
    has_changes: bool

    @classmethod
    def compare(
        cls,
        *,
        left: Mapping[SDKey, SDValue],
        right: Mapping[SDKey, SDValue],
        keep_identical: bool,
    ) -> Self:
        """
        Format of compared entries:
          new:          {k: (None, new_value), ...}
          changed:      {k: (old_value, new_value), ...}
          removed:      {k: (old_value, None), ...}
          identical:    {k: (value, value), ...}
        """
        compared_keys = _DictKeys.compare(left=set(left), right=set(right))
        compared_dict: dict[SDKey, tuple[SDValue, SDValue]] = {}

        has_changes = False
        for key in compared_keys.both:
            if (new_value := right[key]) != (old_value := left[key]):
                compared_dict.setdefault(key, (old_value, new_value))
                has_changes = True
            elif keep_identical:
                compared_dict.setdefault(key, (old_value, old_value))

        compared_dict |= {k: _encode_as_new(right[k]) for k in compared_keys.only_new}
        compared_dict |= {k: _encode_as_removed(left[k]) for k in compared_keys.only_old}

        return cls(
            result=compared_dict,
            has_changes=bool(has_changes or compared_keys.only_new or compared_keys.only_old),
        )


def _compare_attributes(
    left: ImmutableAttributes, right: ImmutableAttributes
) -> ImmutableDeltaAttributes:
    return ImmutableDeltaAttributes(
        pairs=_DeltaDict.compare(
            left=right.pairs,
            right=left.pairs,
            keep_identical=False,
        ).result,
    )


def _compare_tables(left: ImmutableTable, right: ImmutableTable) -> ImmutableDeltaTable:
    compared_row_idents = _DictKeys.compare(
        left=set(right.rows_by_ident),
        right=set(left.rows_by_ident),
    )

    rows: list[Mapping[SDKey, tuple[SDValue, SDValue]]] = []

    for ident in compared_row_idents.only_old:
        rows.append({k: _encode_as_removed(v) for k, v in right.rows_by_ident[ident].items()})

    for ident in compared_row_idents.both:
        # Note: Rows which have at least one change also provide all table fields.
        # Example:
        # If the version of a package (below "Software > Packages") has changed from 1.0 to 2.0
        # then it would be very annoying if the rest of the row is not shown.
        if (
            compared_dict_result := _DeltaDict.compare(
                left=right.rows_by_ident[ident],
                right=left.rows_by_ident[ident],
                keep_identical=True,
            )
        ).has_changes:
            rows.append(compared_dict_result.result)

    for ident in compared_row_idents.only_new:
        rows.append({k: _encode_as_new(v) for k, v in left.rows_by_ident[ident].items()})

    return ImmutableDeltaTable(
        key_columns=sorted(set(left.key_columns).union(right.key_columns)),
        rows=rows,
    )


def _compare_trees(left: ImmutableTree, right: ImmutableTree) -> ImmutableDeltaTree:
    nodes: dict[SDNodeName, ImmutableDeltaTree] = {}

    compared_node_names = _DictKeys.compare(
        left=set(right.nodes_by_name),
        right=set(left.nodes_by_name),
    )

    for name in compared_node_names.only_new:
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

    for name in compared_node_names.only_old:
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
        if not isinstance(other, (_MutableAttributes, ImmutableAttributes)):
            return NotImplemented
        return self.pairs == other.pairs

    @classmethod
    def deserialize(cls, raw_attributes: SDRawAttributes) -> ImmutableAttributes:
        return ImmutableAttributes(
            pairs=raw_attributes.get("Pairs", {}),
            retentions={
                key: RetentionInterval.deserialize(raw_retention_interval)
                for key, raw_retention_interval in raw_attributes.get("Retentions", {}).items()
            },
        )

    def serialize(self) -> SDRawAttributes:
        raw_attributes: SDRawAttributes = {}
        if self.pairs:
            raw_attributes["Pairs"] = self.pairs
        if self.retentions:
            raw_attributes["Retentions"] = {k: v.serialize() for k, v in self.retentions.items()}
        return raw_attributes

    @property
    def bare(self) -> SDBareAttributes:
        # Useful for debugging; no restrictions
        return {
            "Pairs": self.pairs,
            "Retentions": {k: v.serialize() for k, v in self.retentions.items()},
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
        if not isinstance(other, (_MutableTable, ImmutableTable)):
            return NotImplemented

        compared_row_idents = _DictKeys.compare(
            left=set(self.rows_by_ident),
            right=set(other.rows_by_ident),
        )

        if compared_row_idents.only_old:
            return False

        if compared_row_idents.only_new:
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

    @classmethod
    def deserialize(cls, raw_table: SDRawTable) -> ImmutableTable:
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
                    key: RetentionInterval.deserialize(raw_retention_interval)
                    for key, raw_retention_interval in raw_intervals_by_key.items()
                }
                for ident, raw_intervals_by_key in raw_table.get("Retentions", {}).items()
            },
        )

    def serialize(self) -> SDRawTable:
        raw_table: SDRawTable = {}
        if self.rows_by_ident:
            raw_table.update(
                {
                    "KeyColumns": self.key_columns,
                    "Rows": list(self.rows_by_ident.values()),
                }
            )
        if self.retentions:
            raw_table["Retentions"] = {
                i: {k: v.serialize() for k, v in ri.items()} for i, ri in self.retentions.items()
            }
        return raw_table

    @property
    def bare(self) -> SDBareTable:
        # Useful for debugging; no restrictions
        return {
            "KeyColumns": self.key_columns,
            "RowsByIdent": self.rows_by_ident,
            "Retentions": {
                i: {k: v.serialize() for k, v in ri.items()} for i, ri in self.retentions.items()
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
        if not isinstance(other, (MutableTree, ImmutableTree)):
            return NotImplemented

        if self.attributes != other.attributes or self.table != other.table:
            return False

        compared_node_names = _DictKeys.compare(
            left=set(self.nodes_by_name),
            right=set(other.nodes_by_name),
        )

        if any(self.nodes_by_name[n] for n in compared_node_names.only_old):
            return False

        if any(other.nodes_by_name[n] for n in compared_node_names.only_new):
            return False

        return all(
            self.nodes_by_name[n] == other.nodes_by_name[n] for n in compared_node_names.both
        )

    def filter(self, filters: Iterable[SDFilterChoice]) -> ImmutableTree:
        return _filter_tree(self, _make_filter_tree(filters))

    def merge(self, right: ImmutableTree) -> ImmutableTree:
        return _merge_nodes(self, right)

    def difference(self, right: ImmutableTree) -> ImmutableDeltaTree:
        return _compare_trees(self, right)

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

    @classmethod
    def deserialize(cls, raw_tree: Mapping) -> ImmutableTree:
        try:
            raw_attributes = raw_tree["Attributes"]
            raw_table = raw_tree["Table"]
            raw_nodes = raw_tree["Nodes"]
        except KeyError:
            return _deserialize_legacy_node(path=(), raw_tree=raw_tree)

        return ImmutableTree._deserialize(
            path=(),
            raw_attributes=raw_attributes,
            raw_table=raw_table,
            raw_nodes=raw_nodes,
        )

    @classmethod
    def _deserialize(
        cls,
        *,
        path: SDPath,
        raw_attributes: SDRawAttributes,
        raw_table: SDRawTable,
        raw_nodes: Mapping[SDNodeName, SDRawTree],
    ) -> ImmutableTree:
        return cls(
            path=path,
            attributes=ImmutableAttributes.deserialize(raw_attributes),
            table=ImmutableTable.deserialize(raw_table),
            nodes_by_name={
                name: cls._deserialize(
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
            "Nodes": {name: node.serialize() for name, node in self.nodes_by_name.items() if node},
        }

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
    attributes: ImmutableDeltaAttributes, filter_tree: _FilterTree
) -> ImmutableDeltaAttributes:
    return ImmutableDeltaAttributes(pairs=filter_tree.filter_pairs(attributes.pairs))


def _filter_delta_table(
    table: ImmutableDeltaTable, filter_tree: _FilterTree
) -> ImmutableDeltaTable:
    return ImmutableDeltaTable(
        key_columns=table.key_columns,
        rows=[filtered_row for row in table.rows if (filtered_row := filter_tree.filter_row(row))],
    )


def _filter_delta_tree(tree: ImmutableDeltaTree, filter_tree: _FilterTree) -> ImmutableDeltaTree:
    return ImmutableDeltaTree(
        path=tree.path,
        attributes=_filter_delta_attributes(tree.attributes, filter_tree),
        table=_filter_delta_table(tree.table, filter_tree),
        nodes_by_name={
            name: filtered_node
            for name in filter_tree.filter_node_names(set(tree.nodes_by_name))
            if (
                filtered_node := _filter_delta_tree(
                    tree.nodes_by_name.get(name, ImmutableDeltaTree(path=tree.path + (name,))),
                    filter_tree.filters_by_name.get(name, _FilterTree()),
                )
            )
        },
    )


_SDEncodeAs = Callable[[SDValue], tuple[SDValue, SDValue]]
SDDeltaCounter = Counter[Literal["new", "changed", "removed"]]


def _compute_delta_stats(
    dict_: Mapping[SDKey, tuple[SDValue, SDValue]],
) -> SDDeltaCounter:
    counter: SDDeltaCounter = Counter()
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
class ImmutableDeltaAttributes:
    pairs: Mapping[SDKey, tuple[SDValue, SDValue]] = field(default_factory=dict)

    def __len__(self) -> int:
        return len(self.pairs)

    @classmethod
    def from_attributes(
        cls, *, attributes: ImmutableAttributes, encode_as: _SDEncodeAs
    ) -> ImmutableDeltaAttributes:
        return cls(pairs={key: encode_as(value) for key, value in attributes.pairs.items()})

    def get_stats(self) -> SDDeltaCounter:
        return _compute_delta_stats(self.pairs)

    @classmethod
    def deserialize(cls, raw_attributes: SDRawDeltaAttributes) -> ImmutableDeltaAttributes:
        return cls(pairs=raw_attributes.get("Pairs", {}))

    def serialize(self) -> SDRawDeltaAttributes:
        return {"Pairs": self.pairs} if self.pairs else {}

    @property
    def bare(self) -> SDBareDeltaAttributes:
        # Useful for debugging; no restrictions
        return {"Pairs": self.pairs}


@dataclass(frozen=True, kw_only=True)
class ImmutableDeltaTable:
    key_columns: Sequence[SDKey] = field(default_factory=list)
    rows: Sequence[Mapping[SDKey, tuple[SDValue, SDValue]]] = field(default_factory=list)

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

    @classmethod
    def deserialize(cls, raw_table: SDRawDeltaTable) -> ImmutableDeltaTable:
        return cls(key_columns=raw_table.get("KeyColumns", []), rows=raw_table.get("Rows", []))

    def serialize(self) -> SDRawDeltaTable:
        return {"KeyColumns": self.key_columns, "Rows": self.rows} if self.rows else {}

    @property
    def bare(self) -> SDBareDeltaTable:
        # Useful for debugging; no restrictions
        return {"KeyColumns": self.key_columns, "Rows": self.rows}


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

    def filter(self, filters: Iterable[SDFilterChoice]) -> ImmutableDeltaTree:
        return _filter_delta_tree(self, _make_filter_tree(filters))

    def get_stats(self) -> SDDeltaCounter:
        counter: SDDeltaCounter = Counter()
        counter.update(self.attributes.get_stats())
        counter.update(self.table.get_stats())
        for node in self.nodes_by_name.values():
            counter.update(node.get_stats())
        return counter

    @classmethod
    def deserialize(cls, raw_tree: SDRawDeltaTree) -> ImmutableDeltaTree:
        return cls._deserialize(path=(), raw_tree=raw_tree)

    @classmethod
    def _deserialize(cls, *, path: SDPath, raw_tree: SDRawDeltaTree) -> ImmutableDeltaTree:
        return cls(
            path=path,
            attributes=ImmutableDeltaAttributes.deserialize(raw_attributes=raw_tree["Attributes"]),
            table=ImmutableDeltaTable.deserialize(raw_table=raw_tree["Table"]),
            nodes_by_name={
                raw_node_name: cls._deserialize(
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


def load_tree(filepath: Path) -> ImmutableTree:
    if raw_tree := store.load_object_from_file(filepath, default=None):
        return ImmutableTree.deserialize(raw_tree)
    return ImmutableTree()


class SDMeta(TypedDict):
    version: Literal["1"]
    do_archive: bool


def make_meta(*, do_archive: bool) -> SDMeta:
    return SDMeta(version="1", do_archive=do_archive)


class SDMetaAndRawTreeV0(TypedDict):
    meta_version: Literal["0"]
    meta_do_archive: bool
    Attributes: SDRawAttributes
    Table: SDRawTable
    Nodes: Mapping[SDNodeName, SDRawTree]


class SDMetaAndRawTree(TypedDict):
    meta: SDMeta
    raw_tree: SDRawTree


def parse_from_unzipped(raw: Mapping) -> SDMetaAndRawTree:
    # Note: Since Checkmk 2.1 we explicitly extract "Attributes", "Table" or "Nodes" while
    # deserialization. This means that "meta_*" are not taken into account and we stay
    # compatible.
    if set(raw) == set(["meta", "raw_tree"]):
        # Handle future versions
        return SDMetaAndRawTree(meta=raw["meta"], raw_tree=raw["raw_tree"])
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


def _make_meta_and_raw_tree(meta: SDMeta, raw_tree: SDRawTree) -> SDMetaAndRawTreeV0:
    return SDMetaAndRawTreeV0(
        meta_version="0",
        meta_do_archive=meta["do_archive"],
        Attributes=raw_tree["Attributes"],
        Table=raw_tree["Table"],
        Nodes=raw_tree["Nodes"],
    )


class TreeStore:
    def __init__(self, tree_dir: Path | str) -> None:
        self._tree_dir = Path(tree_dir)
        self._last_filepath = Path(tree_dir) / ".last"

    def load(self, *, host_name: HostName) -> ImmutableTree:
        return load_tree(self._tree_file(host_name))

    def save(
        self, *, host_name: HostName, tree: MutableTree, meta: SDMeta, pretty: bool = False
    ) -> None:
        self._tree_dir.mkdir(parents=True, exist_ok=True)

        tree_file = self._tree_file(host_name)

        raw_tree = tree.serialize()
        store.save_object_to_file(tree_file, raw_tree, pretty=pretty)

        if self._tree_dir.name == "inventory":
            buf = io.BytesIO()
            with gzip.GzipFile(fileobj=buf, mode="wb") as f:
                f.write((repr(_make_meta_and_raw_tree(meta, raw_tree)) + "\n").encode("utf-8"))
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
