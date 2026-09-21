#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import TypeIs

from .trees import (
    ImmutableAttributes,
    ImmutableTable,
    ImmutableTree,
    make_row_ident,
    SDKey,
    SDNodeName,
    SDPath,
    SDRowIdent,
    SDValue,
)


def _deserialize_legacy_attributes(raw_pairs: Mapping[SDKey, SDValue]) -> ImmutableAttributes:
    return ImmutableAttributes(pairs=raw_pairs)


def _deserialize_legacy_table(raw_rows: Sequence[Mapping[SDKey, SDValue]]) -> ImmutableTable:
    key_columns = sorted({k for r in raw_rows for k in r})
    rows_by_ident: dict[SDRowIdent, dict[SDKey, SDValue]] = {}
    for row in raw_rows:
        rows_by_ident.setdefault(make_row_ident(key_columns, row), {}).update(row)

    return ImmutableTable(key_columns=key_columns, rows_by_ident=rows_by_ident)


def _is_sd_value(value: object) -> TypeIs[SDValue]:
    return value is None or isinstance(value, int | float | str | bool)


def _parse_legacy_row(raw_row: Mapping[str, object]) -> Mapping[SDKey, SDValue]:
    return {SDKey(key): value for key, value in raw_row.items() if _is_sd_value(value)}


def deserialize_legacy_tree(
    path: SDPath,
    raw_tree: Mapping[str, object],
    raw_rows: Sequence[Mapping[SDKey, SDValue]] | None = None,
) -> ImmutableTree:
    raw_pairs: dict[SDKey, SDValue] = {}
    raw_tables: dict[SDNodeName, list[Mapping[SDKey, SDValue]]] = {}
    raw_nodes: dict[SDNodeName, dict[str, object]] = {}

    for key, value in raw_tree.items():
        if isinstance(value, dict):
            if not value:
                continue
            raw_nodes.setdefault(SDNodeName(key), value)

        elif isinstance(value, list):
            if not value:
                continue

            if all(_is_sd_value(v) for v in value):
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
                raw_tables.setdefault(SDNodeName(key), [_parse_legacy_row(r) for r in value])
                continue

            for idx, entry in enumerate(value):
                raw_nodes.setdefault(SDNodeName(key), {}).setdefault(str(idx), entry)

        elif _is_sd_value(value):
            raw_pairs.setdefault(SDKey(key), value)

        else:
            raise TypeError(value)

    return ImmutableTree(
        path=path,
        attributes=_deserialize_legacy_attributes(raw_pairs),
        table=_deserialize_legacy_table(raw_rows) if raw_rows else ImmutableTable(),
        nodes_by_name={
            **{
                name: deserialize_legacy_tree(
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
