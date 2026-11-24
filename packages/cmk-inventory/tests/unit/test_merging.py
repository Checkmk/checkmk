#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.inventory.merging import merge_trees
from cmk.inventory.trees import ImmutableTable, ImmutableTree, SDKey


def test_merge_with_empty_tables() -> None:
    assert merge_trees(ImmutableTree(), ImmutableTree()) == ImmutableTree()


def test_merge_with_empty_left_table() -> None:
    assert merge_trees(
        ImmutableTree(),
        ImmutableTree(
            table=ImmutableTable(
                key_columns=[SDKey("key_column")],
                rows_by_ident={
                    ("Key Column",): {SDKey("key_column"): "Key Column", SDKey("value"): "Value"}
                },
            )
        ),
    ) == ImmutableTree(
        table=ImmutableTable(
            key_columns=[SDKey("key_column")],
            rows_by_ident={
                ("Key Column",): {SDKey("key_column"): "Key Column", SDKey("value"): "Value"}
            },
        )
    )


def test_merge_with_empty_right_table() -> None:
    assert merge_trees(
        ImmutableTree(
            table=ImmutableTable(
                key_columns=[SDKey("key_column")],
                rows_by_ident={
                    ("Key Column",): {SDKey("key_column"): "Key Column", SDKey("value"): "Value"}
                },
            )
        ),
        ImmutableTree(),
    ) == ImmutableTree(
        table=ImmutableTable(
            key_columns=[SDKey("key_column")],
            rows_by_ident={
                ("Key Column",): {SDKey("key_column"): "Key Column", SDKey("value"): "Value"}
            },
        )
    )


def test_merge_joins_the_rows_of_the_same_ident() -> None:
    assert merge_trees(
        ImmutableTree(
            table=ImmutableTable(
                key_columns=[SDKey("key_column")],
                rows_by_ident={
                    ("Key Column",): {SDKey("key_column"): "Key Column", SDKey("left"): "Left"}
                },
            )
        ),
        ImmutableTree(
            table=ImmutableTable(
                key_columns=[SDKey("key_column")],
                rows_by_ident={
                    ("Key Column",): {SDKey("key_column"): "Key Column", SDKey("right"): "Right"}
                },
            )
        ),
    ).table.rows == [
        {SDKey("key_column"): "Key Column", SDKey("left"): "Left", SDKey("right"): "Right"}
    ]
