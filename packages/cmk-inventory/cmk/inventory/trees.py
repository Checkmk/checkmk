#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pprint
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal, NewType, override, TypedDict

from ._choices import get_filtered_dict, make_filter_func
from ._dict_keys import DictKeys

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


def make_row_ident(key_columns: Sequence[SDKey], row: Mapping[SDKey, SDValue]) -> SDRowIdent:
    return tuple(row[k] for k in key_columns if k in row)


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
        filter_func = make_filter_func(choice.choice)
        retention_interval = RetentionInterval.from_config(*choice.cache_info, interval)
        compared_keys = DictKeys.compare(
            left=set(
                get_filtered_dict(
                    previous.pairs,
                    _make_retentions_filter_func(
                        filter_func=filter_func,
                        intervals_by_key=previous.retentions,
                        now=now,
                    ),
                )
            ),
            right=set(get_filtered_dict(self.pairs, filter_func)),
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

        compared_row_idents = DictKeys.compare(
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
        filter_func = make_filter_func(choice.choice)
        retention_interval = RetentionInterval.from_config(*choice.cache_info, interval)
        self._add_key_columns(previous.key_columns)
        previous_filtered_rows = {
            ident: filtered_row
            for ident, row in previous.rows_by_ident.items()
            if (
                filtered_row := get_filtered_dict(
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
            if (filtered_row := get_filtered_dict(row, filter_func))
        }
        compared_row_idents = DictKeys.compare(
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
            compared_keys = DictKeys.compare(
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

        compared_node_names = DictKeys.compare(
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

        compared_row_idents = DictKeys.compare(
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

        compared_node_names = DictKeys.compare(
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
