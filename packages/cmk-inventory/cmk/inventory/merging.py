#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from .trees import (
    ImmutableAttributes,
    ImmutableTable,
    ImmutableTree,
    make_row_ident,
    SDKey,
    SDRowIdent,
    SDValue,
)


def _merge_attributes(left: ImmutableAttributes, right: ImmutableAttributes) -> ImmutableAttributes:
    return ImmutableAttributes(
        pairs={**left.pairs, **right.pairs},
        retentions={**left.retentions, **right.retentions},
    )


def _merge_tables_by_same_or_empty_key_columns(
    key_columns: Sequence[SDKey], left: ImmutableTable, right: ImmutableTable
) -> ImmutableTable:
    rows_by_ident = {
        ident: {**left.rows_by_ident.get(ident, {}), **right.rows_by_ident.get(ident, {})}
        for ident in {**left.rows_by_ident, **right.rows_by_ident}
    }

    return ImmutableTable(
        key_columns=key_columns,
        rows_by_ident=rows_by_ident,
        retentions={**left.retentions, **right.retentions},
    )


def _merge_tables_by_common_key_columns(
    left: ImmutableTable, right: ImmutableTable
) -> ImmutableTable:
    key_columns = sorted(set(left.key_columns).intersection(right.key_columns))
    rows_by_ident: dict[SDRowIdent, dict[SDKey, SDValue]] = {}
    for row in list(left.rows_by_ident.values()) + list(right.rows_by_ident.values()):
        rows_by_ident.setdefault(make_row_ident(key_columns, row), {}).update(row)

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

    return _merge_tables_by_common_key_columns(left, right)


def merge_trees(left: ImmutableTree, right: ImmutableTree) -> ImmutableTree:
    nodes_by_name = {
        **left.nodes_by_name,
        **right.nodes_by_name,
        **{
            name: merge_trees(left=left.nodes_by_name[name], right=right.nodes_by_name[name])
            for name in left.nodes_by_name.keys() & right.nodes_by_name.keys()
        },
    }

    return ImmutableTree(
        path=left.path,
        attributes=_merge_attributes(left.attributes, right.attributes),
        table=_merge_tables(left.table, right.table),
        nodes_by_name=nodes_by_name,
    )
