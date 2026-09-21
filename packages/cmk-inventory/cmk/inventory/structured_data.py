#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""
This module handles tree structures for HW/SW Inventory system and
structured monitoring data of Check_MK.
"""

import pprint
from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import auto, Enum
from typing import Literal, NewType, override, Self, TypedDict

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
    def valid_until(self) -> int:
        return self.cached_at + self.cache_interval

    @property
    def keep_until(self) -> int:
        return self.valid_until + self.retention_interval


class SDBareAttributes(TypedDict):
    Pairs: Mapping[SDKey, SDValue]
    Retentions: Mapping[SDKey, RetentionInterval]


class SDBareTable(TypedDict):
    KeyColumns: Sequence[SDKey]
    RowsByIdent: Mapping[SDRowIdent, Mapping[SDKey, SDValue]]
    Retentions: Mapping[SDRowIdent, Mapping[SDKey, RetentionInterval]]


class SDBareTree(TypedDict):
    Path: SDPath
    Attributes: SDBareAttributes
    Table: SDBareTable
    Nodes: Mapping[SDNodeName, SDBareTree]


def parse_visible_raw_path(raw_path: str) -> SDPath:
    return tuple(SDNodeName(part) for part in raw_path.split(".") if part)


class TreeSource(Enum):
    node = auto()
    table = auto()
    attributes = auto()


@dataclass(frozen=True)
class InventoryPath:
    path: SDPath
    source: TreeSource
    key: SDKey = SDKey("")

    @property
    def node_name(self) -> str:
        return self.path[-1] if self.path else ""


def _sanitize_path(path: Sequence[str]) -> SDPath:
    # ":": Nested tables, see also lib/structured_data.py
    return tuple(
        SDNodeName(p) for part in path for p in (part.split(":") if ":" in part else [part]) if p
    )


def parse_internal_raw_path(raw: str) -> InventoryPath:
    if not raw:
        return InventoryPath(
            path=(),
            source=TreeSource.node,
        )
    if raw.endswith("."):
        return InventoryPath(
            path=_sanitize_path(raw[:-1].strip(".").split(".")),
            source=TreeSource.node,
        )
    if raw.endswith(":"):
        return InventoryPath(
            path=_sanitize_path(raw[:-1].strip(".").split(".")),
            source=TreeSource.table,
        )
    path = raw.strip(".").split(".")
    sanitized_path = _sanitize_path(path[:-1])
    if ":" in path[-2]:
        source = TreeSource.table
        # Forget the last '*' or an index like '17'
        # because it's related to columns (not nodes)
        sanitized_path = sanitized_path[:-1]
    else:
        source = TreeSource.attributes
    return InventoryPath(
        path=sanitized_path,
        source=source,
        key=SDKey(path[-1]),
    )


#   .--helper--------------------------------------------------------------.


def make_row_ident(key_columns: Sequence[SDKey], row: Mapping[SDKey, SDValue]) -> SDRowIdent:
    return tuple(row[k] for k in key_columns if k in row)


@dataclass(frozen=True, kw_only=True)
class _DictKeys[T]:
    only_left: set[T]
    both: set[T]
    only_right: set[T]

    @classmethod
    def compare(cls, *, left: set[T], right: set[T]) -> Self:
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
#   .--mutable tree--------------------------------------------------------.


def _format_update_result_attrs(*, title: str, message: str) -> str:
    return f"[Attributes] {title}: {message}"


@dataclass(kw_only=True)
class _MutableAttributes:
    pairs: dict[SDKey, SDValue] = field(default_factory=dict)
    retentions: Mapping[SDKey, RetentionInterval] = field(default_factory=dict)
    update_results: list[str] = field(default_factory=list)

    def __len__(self) -> int:
        # The attribute 'pairs' is decisive. Other attributes like 'retentions' have no impact
        # if there are no pairs.
        return len(self.pairs)

    @override
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
        interval: int,
        choice: _SDRetentionFilterChoice,
    ) -> None:
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

        if pairs:
            self.add(pairs)
            self.update_results.append(
                _format_update_result_attrs(
                    title="Added pairs",
                    message=", ".join(sorted(pairs)),
                )
            )

        if retentions:
            self.retentions = retentions
            self.update_results.append(
                _format_update_result_attrs(
                    title="Keep until",
                    message=", ".join(
                        [f"{k} ({retentions[k].keep_until})" for k in sorted(retentions)]
                    ),
                )
            )

    @property
    def bare(self) -> SDBareAttributes:
        # Useful for debugging; no restrictions
        return {
            "Pairs": self.pairs,
            "Retentions": self.retentions,
        }


def _format_update_result_table(ident: SDRowIdent, *, title: str, message: str) -> str:
    return f"[Table] '{', '.join(map(str, ident))}': {title}: {message}"


@dataclass(kw_only=True)
class _MutableTable:
    key_columns: Sequence[SDKey] = field(default_factory=list)
    rows_by_ident: dict[SDRowIdent, dict[SDKey, SDValue]] = field(default_factory=dict)
    retentions: Mapping[SDRowIdent, Mapping[SDKey, RetentionInterval]] = field(default_factory=dict)
    update_results: list[str] = field(default_factory=list)

    def __len__(self) -> int:
        # The attribute 'rows' is decisive. Other attributes like 'key_columns' or 'retentions'
        # have no impact if there are no rows.
        return sum(map(len, self.rows_by_ident.values()))

    @override
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
        if rows:
            self._add_key_columns(key_columns)
        for row in rows:
            self._add_row(make_row_ident(self.key_columns, row), row)

    def update(
        self,
        now: int,
        previous: ImmutableTable,
        interval: int,
        choice: _SDRetentionFilterChoice,
    ) -> None:
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
                self.update_results.append(
                    _format_update_result_table(
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
                self.update_results.append(
                    _format_update_result_table(
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
                self.update_results.append(
                    _format_update_result_table(
                        ident=ident,
                        title="Keep until",
                        message=", ".join(
                            [
                                f"{k} ({intervals_by_key[k].keep_until})"
                                for k in sorted(intervals_by_key)
                            ]
                        ),
                    )
                )

    @property
    def bare(self) -> SDBareTable:
        # Useful for debugging; no restrictions
        return {
            "KeyColumns": self.key_columns,
            "RowsByIdent": self.rows_by_ident,
            "Retentions": self.retentions,
        }


@dataclass(frozen=True, kw_only=True)
class MutableTree:
    path: SDPath = ()
    attributes: _MutableAttributes = field(default_factory=_MutableAttributes)
    table: _MutableTable = field(default_factory=_MutableTable)
    nodes_by_name: dict[SDNodeName, MutableTree] = field(default_factory=dict)

    def __len__(self) -> int:
        return sum(
            [len(self.attributes), len(self.table)]
            + [len(node) for node in self.nodes_by_name.values()]
        )

    @override
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
    ) -> None:
        node = self.setdefault_node(choices.path)
        previous_node = previous_tree.get_tree(choices.path)
        for c in choices.pairs:
            node.attributes.update(now, previous_node.attributes, choices.interval, c)
        for c in choices.columns:
            node.table.update(now, previous_node.table, choices.interval, c)

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

    def get_update_results(self) -> Mapping[SDPath, Sequence[str]]:
        by_path = {}
        if self.attributes.update_results or self.table.update_results:
            by_path[self.path] = list(self.attributes.update_results) + list(
                self.table.update_results
            )
        for node in self.nodes_by_name.values():
            if update_results := node.get_update_results():
                by_path.update({p: list(rs) for p, rs in update_results.items()})
        return by_path

    @property
    def bare(self) -> SDBareTree:
        # Useful for debugging; no restrictions
        return {
            "Path": self.path,
            "Attributes": self.attributes.bare,
            "Table": self.table.bare,
            "Nodes": {name: node.bare for name, node in self.nodes_by_name.items()},
        }

    @override
    def __str__(self) -> str:
        return f"{self.__class__.__name__}({pprint.pformat(self.bare)})"


# .
#   .--immutable tree------------------------------------------------------.


@dataclass(frozen=True, kw_only=True)
class SDDeltaValue:
    old: SDValue
    new: SDValue


class SDBareDeltaAttributes(TypedDict):
    Pairs: Mapping[SDKey, SDDeltaValue]


class SDBareDeltaTable(TypedDict, total=False):
    KeyColumns: Sequence[SDKey]
    Rows: Sequence[Mapping[SDKey, SDDeltaValue]]


class SDBareDeltaTree(TypedDict):
    Path: SDPath
    Attributes: SDBareDeltaAttributes
    Table: SDBareDeltaTable
    Nodes: Mapping[SDNodeName, SDBareDeltaTree]


@dataclass(frozen=True, kw_only=True)
class ImmutableAttributes:
    pairs: Mapping[SDKey, SDValue] = field(default_factory=dict)
    retentions: Mapping[SDKey, RetentionInterval] = field(default_factory=dict)

    def __len__(self) -> int:
        # The attribute 'pairs' is decisive. Other attributes like 'retentions' have no impact
        # if there are no pairs.
        return len(self.pairs)

    @override
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, _MutableAttributes | ImmutableAttributes):
            return NotImplemented
        return self.pairs == other.pairs

    @property
    def bare(self) -> SDBareAttributes:
        # Useful for debugging; no restrictions
        return {
            "Pairs": self.pairs,
            "Retentions": self.retentions,
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

    @override
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
            "Retentions": self.retentions,
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

    @override
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

    @override
    def __str__(self) -> str:
        return f"{self.__class__.__name__}({pprint.pformat(self.bare)})"


# .
#   .--immutable delta tree------------------------------------------------.


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
        return {"Pairs": self.pairs}


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
            "Rows": self.rows,
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

    @override
    def __str__(self) -> str:
        return f"{self.__class__.__name__}({pprint.pformat(self.bare)})"


# .
#   .--filtering-----------------------------------------------------------.


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


# Data for the HW/SW Inventory has a validity period (live data or persisted).
# With the retention intervals configuration you can keep specific attributes or table columns
# longer than their validity period.
#
# 1.) Collect cache infos from plugins if and only if there is a configured 'path-to-node' and
#     attributes/table keys entry in the ruleset 'Retention intervals for HW/SW Inventory
#     entities'.
#
# 2.) Process collected cache infos - handle the following four cases:
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


def _parse_choice(
    raw_choice: Literal["all"] | tuple[str, list[str]],
) -> Sequence[SDKey] | Literal["all"]:
    return [SDKey(k) for k in raw_choice[-1]] if isinstance(raw_choice, tuple) else raw_choice


def make_retention_filter_choices(
    *,
    now: int,
    raw_intervals_from_config: Sequence[RawIntervalFromConfig],
    pairs_cache_info: Mapping[SDPath, tuple[int, int] | None],
    columns_cache_info: Mapping[SDPath, tuple[int, int] | None],
) -> Sequence[SDRetentionFilterChoices]:
    def cache_info(
        by_path: Mapping[SDPath, tuple[int, int] | None], path: SDPath
    ) -> tuple[int, int]:
        return (now, 0) if (ci := by_path.get(path)) is None else ci

    choices_by_path: dict[SDPath, SDRetentionFilterChoices] = {}
    for entry in raw_intervals_from_config:
        path = parse_visible_raw_path(entry["visible_raw_path"])
        choices = choices_by_path.setdefault(
            path, SDRetentionFilterChoices(path=path, interval=entry["interval"])
        )
        if attributes := entry.get("attributes"):
            choices.add_pairs_choice(
                choice=_parse_choice(attributes),
                cache_info=cache_info(pairs_cache_info, path),
            )
        elif columns := entry.get("columns"):
            choices.add_columns_choice(
                choice=_parse_choice(columns),
                cache_info=cache_info(columns_cache_info, path),
            )
    return list(choices_by_path.values())


def _make_filter_func[CT: (SDKey, SDNodeName)](
    choice: Literal["nothing", "all"] | Sequence[CT],
) -> Callable[[CT], bool]:
    match choice:
        case "nothing":
            return lambda _k: False
        case "all":
            return lambda _k: True
        case _:
            return lambda k: k in choice


def _consolidate_filter_funcs[CT: (SDKey, SDNodeName)](
    choices: Sequence[Literal["nothing", "all"] | Sequence[CT]],
) -> Callable[[CT], bool]:
    return lambda kn: any(_make_filter_func(c)(kn) for c in choices)


def _get_filtered_dict[VT_co](
    mapping: Mapping[SDKey, VT_co], filter_func: Callable[[SDKey], bool]
) -> Mapping[SDKey, VT_co]:
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

    def filter_pairs[VT_co](self, pairs: Mapping[SDKey, VT_co]) -> Mapping[SDKey, VT_co]:
        return (
            _get_filtered_dict(pairs, _consolidate_filter_funcs(self._filter_choices_pairs))
            if self._filter_choices_pairs
            else pairs
        )

    def filter_row[VT_co](self, row: Mapping[SDKey, VT_co]) -> Mapping[SDKey, VT_co]:
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


def make_filter_choices_from_api_request_paths(
    api_request_paths: Sequence[str],
) -> Sequence[SDFilterChoice]:
    def _make_filter_choice(inventory_path: InventoryPath) -> SDFilterChoice:
        if inventory_path.key:
            return SDFilterChoice(
                path=inventory_path.path,
                pairs=[inventory_path.key],
                columns=[inventory_path.key],
                nodes="nothing",
            )
        return SDFilterChoice(
            path=inventory_path.path,
            pairs="all",
            columns="all",
            nodes="all",
        )

    return [
        _make_filter_choice(parse_internal_raw_path(raw_path)) for raw_path in api_request_paths
    ]


def filter_tree(tree: ImmutableTree, filters: Iterable[SDFilterChoice]) -> ImmutableTree:
    return _filter_tree(tree, _make_filter_tree(filters))


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


# .
#   .--merging-------------------------------------------------------------.


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
        rows_by_ident.setdefault(make_row_ident(key_columns, row), {}).update(row)

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


# .
#   .--comparing-----------------------------------------------------------.


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


def compare_trees(left: ImmutableTree, right: ImmutableTree) -> ImmutableDeltaTree:
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

        if (node := compare_trees(child_left, child_right)).get_stats():
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
