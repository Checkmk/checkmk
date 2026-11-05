#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal, NewType, override

from ._dict_keys import DictKeys, get_filtered_dict

SDNodeName = NewType("SDNodeName", str)
SDPath = tuple[SDNodeName, ...]

SDKey = NewType("SDKey", str)
SDValue = int | float | str | bool | None
SDRowIdent = tuple[SDValue, ...]


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


def sort_missing_values_first(
    compare: Callable[[SDValue, SDValue], int],
) -> Callable[[SDValue, SDValue], int]:
    def wrapper(val_a: SDValue, val_b: SDValue) -> int:
        if val_a is None:
            return 0 if val_b is None else -1

        if val_b is None:
            return 1

        return compare(val_a, val_b)

    return wrapper


def compare_sd_values(val_a: SDValue, val_b: SDValue) -> int:
    if isinstance(val_a, str) and isinstance(val_b, str):
        return (val_a > val_b) - (val_a < val_b)
    if isinstance(val_a, int | float) and isinstance(val_b, int | float):
        return (val_a > val_b) - (val_a < val_b)
    raise TypeError(val_a, val_b)


def make_row_ident(key_columns: Sequence[SDKey], row: Mapping[SDKey, SDValue]) -> SDRowIdent:
    return tuple(row[k] for k in key_columns if k in row)


@dataclass(frozen=True, kw_only=True)
class ImmutableAttributes:
    pairs: Mapping[SDKey, SDValue] = field(default_factory=dict)
    retentions: Mapping[SDKey, RetentionInterval] = field(default_factory=dict)

    def __len__(self) -> int:
        return len(self.pairs)

    @override
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, _MutableAttributes | ImmutableAttributes):
            return NotImplemented
        return self.pairs == other.pairs


@dataclass(frozen=True, kw_only=True)
class ImmutableTable:
    key_columns: Sequence[SDKey] = field(default_factory=list)
    rows_by_ident: Mapping[SDRowIdent, Mapping[SDKey, SDValue]] = field(default_factory=dict)
    retentions: Mapping[SDRowIdent, Mapping[SDKey, RetentionInterval]] = field(default_factory=dict)

    def __len__(self) -> int:
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


def _format_update_result_attrs(*, title: str, message: str) -> str:
    return f"[Attributes] {title}: {message}"


@dataclass(kw_only=True)
class _MutableAttributes:
    pairs: dict[SDKey, SDValue] = field(default_factory=dict)
    retentions: Mapping[SDKey, RetentionInterval] = field(default_factory=dict)
    update_results: list[str] = field(default_factory=list)

    def __len__(self) -> int:
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
        *,
        now: int,
        previous: ImmutableAttributes,
        filter_func: Callable[[SDKey], bool],
        retention_interval: RetentionInterval,
    ) -> None:
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


def _format_update_result_table(ident: SDRowIdent, *, title: str, message: str) -> str:
    return f"[Table] '{', '.join(map(str, ident))}': {title}: {message}"


@dataclass(kw_only=True)
class _MutableTable:
    key_columns: Sequence[SDKey] = field(default_factory=list)
    rows_by_ident: dict[SDRowIdent, dict[SDKey, SDValue]] = field(default_factory=dict)
    retentions: Mapping[SDRowIdent, Mapping[SDKey, RetentionInterval]] = field(default_factory=dict)
    update_results: list[str] = field(default_factory=list)

    def __len__(self) -> int:
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
        *,
        now: int,
        previous: ImmutableTable,
        filter_func: Callable[[SDKey], bool],
        retention_interval: RetentionInterval,
    ) -> None:
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
        node = self._setdefault_node(path)
        if pairs:
            for p in pairs:
                node.attributes.add(p)
        if key_columns and rows:
            node.table.add(key_columns, rows)

    def update_attributes(
        self,
        *,
        path: SDPath,
        now: int,
        previous_tree: ImmutableTree,
        filter_func: Callable[[SDKey], bool],
        retention_interval: RetentionInterval,
    ) -> None:
        self._setdefault_node(path).attributes.update(
            now=now,
            previous=previous_tree.get_tree(path).attributes,
            filter_func=filter_func,
            retention_interval=retention_interval,
        )

    def update_table(
        self,
        *,
        path: SDPath,
        now: int,
        previous_tree: ImmutableTree,
        filter_func: Callable[[SDKey], bool],
        retention_interval: RetentionInterval,
    ) -> None:
        self._setdefault_node(path).table.update(
            now=now,
            previous=previous_tree.get_tree(path).table,
            filter_func=filter_func,
            retention_interval=retention_interval,
        )

    def _setdefault_node(self, path: SDPath) -> MutableTree:
        node = self
        for name in path:
            node = node.nodes_by_name.setdefault(name, MutableTree(path=node.path + (name,)))
        return node

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
