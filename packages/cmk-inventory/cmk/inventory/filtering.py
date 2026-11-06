#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Iterable, Mapping, Sequence, Set
from dataclasses import dataclass, field
from typing import Literal

from ._dict_keys import get_filtered_dict
from .config import InventoryPathsConfig, NothingOrChoices, PermittedPath
from .delta import ImmutableDeltaAttributes, ImmutableDeltaTable, ImmutableDeltaTree
from .raw_paths import InventoryPath, parse_internal_raw_path, parse_visible_raw_path
from .trees import ImmutableAttributes, ImmutableTable, ImmutableTree, SDKey, SDNodeName, SDPath


def make_filter_func[CT: str](
    choice: Literal["nothing", "all"] | Sequence[CT],
) -> Callable[[CT], bool]:
    match choice:
        case "nothing":
            return lambda _k: False
        case "all":
            return lambda _k: True
        case _:
            return lambda k: k in choice


def consolidate_filter_funcs[CT: str](
    choices: Sequence[Literal["nothing", "all"] | Sequence[CT]],
) -> Callable[[CT], bool]:
    filter_funcs = [make_filter_func(c) for c in choices]
    return lambda kn: any(f(kn) for f in filter_funcs)


@dataclass(frozen=True)
class SDFilterChoice:
    path: SDPath
    pairs: Literal["nothing", "all"] | Sequence[SDKey]
    columns: Literal["nothing", "all"] | Sequence[SDKey]
    nodes: Literal["nothing", "all"] | Sequence[SDNodeName]


@dataclass(frozen=True, kw_only=True)
class _SDFilterTrie:
    keep_pair: Callable[[SDKey], bool] | None
    keep_column: Callable[[SDKey], bool] | None
    keep_node: Callable[[SDNodeName], bool]
    children: Mapping[SDNodeName, _SDFilterTrie]

    def filter_pairs[VT_co](self, pairs: Mapping[SDKey, VT_co]) -> Mapping[SDKey, VT_co]:
        return pairs if self.keep_pair is None else get_filtered_dict(pairs, self.keep_pair)

    def filter_row[VT_co](self, row: Mapping[SDKey, VT_co]) -> Mapping[SDKey, VT_co]:
        return row if self.keep_column is None else get_filtered_dict(row, self.keep_column)

    def filter_node_names(self, node_names: Set[SDNodeName]) -> Set[SDNodeName]:
        return {n for n in node_names if self.keep_node(n)}.union(self.children)

    def child(self, name: SDNodeName) -> _SDFilterTrie:
        return self.children.get(name, _EMPTY_FILTER_TRIE)


@dataclass
class _SDFilterTrieBuilder:
    pairs: list[Literal["nothing", "all"] | Sequence[SDKey]] = field(default_factory=list)
    columns: list[Literal["nothing", "all"] | Sequence[SDKey]] = field(default_factory=list)
    nodes: list[Literal["nothing", "all"] | Sequence[SDNodeName]] = field(default_factory=list)
    children: dict[SDNodeName, _SDFilterTrieBuilder] = field(default_factory=dict)

    def append(self, path: SDPath, filter_choice: SDFilterChoice) -> None:
        if path:
            self.children.setdefault(path[0], _SDFilterTrieBuilder()).append(
                path[1:], filter_choice
            )
            return
        self.pairs.append(filter_choice.pairs)
        self.columns.append(filter_choice.columns)
        self.nodes.append(filter_choice.nodes)

    def build(self) -> _SDFilterTrie:
        return _SDFilterTrie(
            keep_pair=consolidate_filter_funcs(self.pairs) if self.pairs else None,
            keep_column=consolidate_filter_funcs(self.columns) if self.columns else None,
            keep_node=consolidate_filter_funcs(self.nodes),
            children={name: child.build() for name, child in self.children.items()},
        )


_EMPTY_FILTER_TRIE = _SDFilterTrieBuilder().build()


def _make_filter_trie(filters: Iterable[SDFilterChoice]) -> _SDFilterTrie:
    builder = _SDFilterTrieBuilder()
    for f in filters:
        builder.append(f.path, f)
    return builder.build()


def _filter_attributes(attributes: ImmutableAttributes, trie: _SDFilterTrie) -> ImmutableAttributes:
    return ImmutableAttributes(
        pairs=trie.filter_pairs(attributes.pairs),
        retentions=attributes.retentions,
    )


def _filter_table(table: ImmutableTable, trie: _SDFilterTrie) -> ImmutableTable:
    return ImmutableTable(
        key_columns=table.key_columns,
        rows_by_ident={
            ident: filtered_row
            for ident, row in table.rows_by_ident.items()
            if (filtered_row := trie.filter_row(row))
        },
        retentions=table.retentions,
    )


def _filter_tree(tree: ImmutableTree, trie: _SDFilterTrie) -> ImmutableTree:
    return ImmutableTree(
        path=tree.path,
        attributes=_filter_attributes(tree.attributes, trie),
        table=_filter_table(tree.table, trie),
        nodes_by_name={
            name: filtered_node
            for name in trie.filter_node_names(set(tree.nodes_by_name))
            if (
                filtered_node := _filter_tree(
                    tree.nodes_by_name.get(name, ImmutableTree(path=tree.path + (name,))),
                    trie.child(name),
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


def _transform_attribute[T](
    f: Callable[[str], T], x: NothingOrChoices | None
) -> Literal["nothing", "all"] | Sequence[T]:
    if x is None:
        return "all"
    if x == "nothing":
        return x
    return [f(y) for y in x[1]]


def _make_filter_choices_from_permitted_paths(
    permitted_paths: Sequence[PermittedPath],
) -> Sequence[SDFilterChoice]:
    return [
        SDFilterChoice(
            path=parse_visible_raw_path(entry["visible_raw_path"]),
            pairs=_transform_attribute(SDKey, entry.get("attributes")),
            columns=_transform_attribute(SDKey, entry.get("columns")),
            nodes=_transform_attribute(SDNodeName, entry.get("nodes")),
        )
        for entry in permitted_paths
        if entry.get("visible_raw_path")
    ]


def make_filter_choices_from_contact_groups(
    configs: Sequence[InventoryPathsConfig | None],
) -> Sequence[SDFilterChoice] | None:
    if not configs:
        return None
    permitted_paths: list[PermittedPath] = []
    for config in configs:
        match config:
            case None | "allow_all":
                return None
            case "forbid_all":
                continue
            case ("paths", paths):
                permitted_paths.extend(paths)
    return _make_filter_choices_from_permitted_paths(permitted_paths)


def filter_tree(tree: ImmutableTree, filters: Iterable[SDFilterChoice]) -> ImmutableTree:
    return _filter_tree(tree, _make_filter_trie(filters))


def _filter_delta_attributes(
    attributes: ImmutableDeltaAttributes, trie: _SDFilterTrie
) -> ImmutableDeltaAttributes:
    return ImmutableDeltaAttributes(pairs=trie.filter_pairs(attributes.pairs))


def _filter_delta_table(table: ImmutableDeltaTable, trie: _SDFilterTrie) -> ImmutableDeltaTable:
    return ImmutableDeltaTable(
        key_columns=table.key_columns,
        rows=[filtered_row for row in table.rows if (filtered_row := trie.filter_row(row))],
    )


def _filter_delta_tree(tree: ImmutableDeltaTree, trie: _SDFilterTrie) -> ImmutableDeltaTree:
    return ImmutableDeltaTree(
        path=tree.path,
        attributes=_filter_delta_attributes(tree.attributes, trie),
        table=_filter_delta_table(tree.table, trie),
        nodes_by_name={
            name: filtered_node
            for name in trie.filter_node_names(set(tree.nodes_by_name))
            if (
                filtered_node := _filter_delta_tree(
                    tree.nodes_by_name.get(name, ImmutableDeltaTree(path=tree.path + (name,))),
                    trie.child(name),
                )
            )
        },
    )


def filter_delta_tree(
    tree: ImmutableDeltaTree, filters: Iterable[SDFilterChoice]
) -> ImmutableDeltaTree:
    return _filter_delta_tree(tree, _make_filter_trie(filters))
