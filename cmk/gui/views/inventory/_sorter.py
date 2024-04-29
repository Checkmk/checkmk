#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import TypedDict

from cmk.utils.structured_data import SDKey, SDPath

from ._display_hints import AttributeDisplayHint, ColumnDisplayHint
from .registry import SortFunction


class SorterFromHint(TypedDict):
    title: str
    columns: Sequence[str]
    load_inv: bool
    cmp: SortFunction


def attribute_sorter_from_hint(
    path: SDPath, key: SDKey, hint: AttributeDisplayHint
) -> SorterFromHint:
    return SorterFromHint(
        title=hint.long_inventory_title,
        columns=["host_inventory", "host_structured_status"],
        load_inv=True,
        cmp=lambda left, right: hint.sort_function(
            left["host_inventory"].get_attribute(path, key),
            right["host_inventory"].get_attribute(path, key),
        ),
    )


def column_sorter_from_hint(ident: str, hint: ColumnDisplayHint) -> SorterFromHint:
    return SorterFromHint(
        title=hint.long_inventory_title,
        columns=[ident],
        load_inv=False,
        cmp=lambda left, right: hint.sort_function(left.get(ident), right.get(ident)),
    )
