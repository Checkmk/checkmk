#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Literal, TypedDict

from ._legacy import deserialize_legacy_tree
from .delta import ImmutableDeltaAttributes, ImmutableDeltaTable, ImmutableDeltaTree, SDDeltaValue
from .trees import (
    ImmutableAttributes,
    ImmutableTable,
    ImmutableTree,
    make_row_ident,
    MutableTree,
    RetentionInterval,
    SDKey,
    SDNodeName,
    SDPath,
    SDRowIdent,
    SDValue,
)


class _SDRawAttributes(TypedDict, total=False):
    Pairs: Mapping[SDKey, SDValue]
    Retentions: Mapping[SDKey, tuple[int, int, int, Literal["previous", "current"]]]


class _SDRawTable(TypedDict, total=False):
    KeyColumns: Sequence[SDKey]
    Rows: Sequence[Mapping[SDKey, SDValue]]
    Retentions: Mapping[
        SDRowIdent, Mapping[SDKey, tuple[int, int, int, Literal["previous", "current"]]]
    ]


class SDRawTree(TypedDict):
    Attributes: _SDRawAttributes
    Table: _SDRawTable
    Nodes: Mapping[SDNodeName, SDRawTree]


class _SDRawDeltaAttributes(TypedDict, total=False):
    Pairs: Mapping[SDKey, tuple[SDValue, SDValue]]


class _SDRawDeltaTable(TypedDict, total=False):
    KeyColumns: Sequence[SDKey]
    Rows: Sequence[Mapping[SDKey, tuple[SDValue, SDValue]]]


class SDRawDeltaTree(TypedDict):
    Attributes: _SDRawDeltaAttributes
    Table: _SDRawDeltaTable
    Nodes: Mapping[SDNodeName, SDRawDeltaTree]


def _serialize_retention_interval(
    retention_interval: RetentionInterval,
) -> tuple[int, int, int, Literal["previous", "current"]]:
    return (
        retention_interval.cached_at,
        retention_interval.cache_interval,
        retention_interval.retention_interval,
        retention_interval.source,
    )


def _serialize_attributes(
    pairs: Mapping[SDKey, SDValue], retentions: Mapping[SDKey, RetentionInterval]
) -> _SDRawAttributes:
    raw_attributes: _SDRawAttributes = {}
    if pairs:
        raw_attributes["Pairs"] = pairs
    if retentions:
        raw_attributes["Retentions"] = {
            k: _serialize_retention_interval(v) for k, v in retentions.items()
        }
    return raw_attributes


def _serialize_table(
    key_columns: Sequence[SDKey],
    rows_by_ident: Mapping[SDRowIdent, Mapping[SDKey, SDValue]],
    retentions: Mapping[SDRowIdent, Mapping[SDKey, RetentionInterval]],
) -> _SDRawTable:
    raw_table: _SDRawTable = {}
    if rows_by_ident:
        raw_table.update(
            {
                "KeyColumns": key_columns,
                "Rows": list(rows_by_ident.values()),
            }
        )
    if retentions:
        raw_table["Retentions"] = {
            i: {k: _serialize_retention_interval(v) for k, v in ri.items()}
            for i, ri in retentions.items()
        }
    return raw_table


def serialize_tree(tree: MutableTree | ImmutableTree) -> SDRawTree:
    return {
        "Attributes": _serialize_attributes(tree.attributes.pairs, tree.attributes.retentions),
        "Table": _serialize_table(
            tree.table.key_columns, tree.table.rows_by_ident, tree.table.retentions
        ),
        "Nodes": {name: serialize_tree(node) for name, node in tree.nodes_by_name.items() if node},
    }


def _deserialize_retention_interval(
    raw_retention_interval: tuple[int, int, int]
    | tuple[int, int, int, Literal["previous", "current"]],
) -> RetentionInterval:
    return (
        RetentionInterval(*raw_retention_interval)
        if len(raw_retention_interval) == 4
        else RetentionInterval(*raw_retention_interval[:3], "current")
    )


def _deserialize_attributes(raw_attributes: _SDRawAttributes) -> ImmutableAttributes:
    return ImmutableAttributes(
        pairs=raw_attributes.get("Pairs", {}),
        retentions={
            key: _deserialize_retention_interval(raw_retention_interval)
            for key, raw_retention_interval in raw_attributes.get("Retentions", {}).items()
        },
    )


def _deserialize_table(raw_table: _SDRawTable) -> ImmutableTable:
    rows = raw_table.get("Rows", [])
    key_columns = raw_table.get("KeyColumns", [])

    rows_by_ident: dict[SDRowIdent, dict[SDKey, SDValue]] = {}
    for row in rows:
        rows_by_ident.setdefault(make_row_ident(key_columns, row), {}).update(row)

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
    raw_attributes: _SDRawAttributes,
    raw_table: _SDRawTable,
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
        return deserialize_legacy_tree(path=(), raw_tree=raw_tree)
    return _deserialize_tree(
        path=(),
        raw_attributes=raw_attributes,
        raw_table=raw_table,
        raw_nodes=raw_nodes,
    )


def _serialize_delta_value(delta_value: SDDeltaValue) -> tuple[SDValue, SDValue]:
    return (delta_value.old, delta_value.new)


def _serialize_delta_attributes(
    delta_attributes: ImmutableDeltaAttributes,
) -> _SDRawDeltaAttributes:
    return (
        {"Pairs": {k: _serialize_delta_value(v) for k, v in delta_attributes.pairs.items()}}
        if delta_attributes.pairs
        else {}
    )


def _serialize_delta_table(delta_table: ImmutableDeltaTable) -> _SDRawDeltaTable:
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


def _deserialize_delta_attributes(
    raw_attributes: _SDRawDeltaAttributes,
) -> ImmutableDeltaAttributes:
    return ImmutableDeltaAttributes(
        pairs={k: _deserialize_delta_value(v) for k, v in raw_attributes.get("Pairs", {}).items()}
    )


def _deserialize_delta_table(raw_table: _SDRawDeltaTable) -> ImmutableDeltaTable:
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
