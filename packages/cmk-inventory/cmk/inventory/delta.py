#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal

from ._dict_keys import DictKeys
from .trees import (
    ImmutableAttributes,
    ImmutableTable,
    ImmutableTree,
    SDKey,
    SDNodeName,
    SDPath,
    SDValue,
)


@dataclass(frozen=True, kw_only=True)
class SDDeltaValue:
    old: SDValue
    new: SDValue


_SDEncodeAs = Callable[[SDValue], SDDeltaValue]
_SDDeltaCounter = Counter[Literal["new", "changed", "removed"]]


def _compute_delta_stats(dict_: Mapping[SDKey, SDDeltaValue]) -> _SDDeltaCounter:
    counter: _SDDeltaCounter = Counter()
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

    def get_stats(self) -> _SDDeltaCounter:
        return _compute_delta_stats(self.pairs)


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

    def get_stats(self) -> _SDDeltaCounter:
        counter: _SDDeltaCounter = Counter()
        for row in self.rows:
            counter.update(_compute_delta_stats(row))
        return counter


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

    def get_stats(self) -> _SDDeltaCounter:
        counter: _SDDeltaCounter = Counter()
        counter.update(self.attributes.get_stats())
        counter.update(self.table.get_stats())
        for node in self.nodes_by_name.values():
            counter.update(node.get_stats())
        return counter


def _encode_as_new(value: SDValue) -> SDDeltaValue:
    return SDDeltaValue(old=None, new=value)


def _encode_as_removed(value: SDValue) -> SDDeltaValue:
    return SDDeltaValue(old=value, new=None)


def _compare_pairs(
    left: Mapping[SDKey, SDValue], right: Mapping[SDKey, SDValue]
) -> Mapping[SDKey, SDDeltaValue]:
    compared_keys = DictKeys.compare(left=set(left), right=set(right))
    return {
        **{
            k: SDDeltaValue(old=right[k], new=left[k])
            for k in compared_keys.both
            if left[k] != right[k]
        },
        **{k: _encode_as_removed(right[k]) for k in compared_keys.only_right},
        **{k: _encode_as_new(left[k]) for k in compared_keys.only_left},
    }


def _identical_pairs(
    left: Mapping[SDKey, SDValue], right: Mapping[SDKey, SDValue]
) -> Mapping[SDKey, SDDeltaValue]:
    return {k: SDDeltaValue(old=v, new=v) for k, v in left.items() if k in right and right[k] == v}


def _compare_attributes(
    left: ImmutableAttributes, right: ImmutableAttributes
) -> ImmutableDeltaAttributes:
    return ImmutableDeltaAttributes(pairs=_compare_pairs(left.pairs, right.pairs))


def _compare_tables(left: ImmutableTable, right: ImmutableTable) -> ImmutableDeltaTable:
    compared_row_idents = DictKeys.compare(
        left=set(left.rows_by_ident),
        right=set(right.rows_by_ident),
    )

    rows: list[Mapping[SDKey, SDDeltaValue]] = []

    for ident in compared_row_idents.only_left:
        rows.append({k: _encode_as_new(v) for k, v in left.rows_by_ident[ident].items()})

    for ident in compared_row_idents.both:
        left_row = left.rows_by_ident[ident]
        right_row = right.rows_by_ident[ident]
        if changed_pairs := _compare_pairs(left_row, right_row):
            rows.append({**_identical_pairs(left_row, right_row), **changed_pairs})

    for ident in compared_row_idents.only_right:
        rows.append({k: _encode_as_removed(v) for k, v in right.rows_by_ident[ident].items()})

    return ImmutableDeltaTable(
        key_columns=sorted(set(left.key_columns).union(right.key_columns)),
        rows=rows,
    )


def compare_trees(left: ImmutableTree, right: ImmutableTree) -> ImmutableDeltaTree:
    nodes: dict[SDNodeName, ImmutableDeltaTree] = {}

    compared_node_names = DictKeys.compare(
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
