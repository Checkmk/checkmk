#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Mapping, Sequence, Set
from dataclasses import dataclass, field
from typing import Literal

from ._choices import consolidate_filter_funcs, get_filtered_dict
from .delta import ImmutableDeltaAttributes, ImmutableDeltaTable, ImmutableDeltaTree
from .raw_paths import InventoryPath, parse_internal_raw_path
from .trees import (
    ImmutableAttributes,
    ImmutableTable,
    ImmutableTree,
    SDKey,
    SDNodeName,
    SDPath,
)


@dataclass(frozen=True)
class SDFilterChoice:
    path: SDPath
    pairs: Literal["nothing", "all"] | Sequence[SDKey]
    columns: Literal["nothing", "all"] | Sequence[SDKey]
    nodes: Literal["nothing", "all"] | Sequence[SDNodeName]


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
            get_filtered_dict(pairs, consolidate_filter_funcs(self._filter_choices_pairs))
            if self._filter_choices_pairs
            else pairs
        )

    def filter_row[VT_co](self, row: Mapping[SDKey, VT_co]) -> Mapping[SDKey, VT_co]:
        return (
            get_filtered_dict(row, consolidate_filter_funcs(self._filter_choices_columns))
            if self._filter_choices_columns
            else row
        )

    def filter_node_names(self, node_names: Set[SDNodeName]) -> Set[SDNodeName]:
        filter_nodes = consolidate_filter_funcs(self._filter_choices_nodes)
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
