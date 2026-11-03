#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.views.sorter import Sorter
from cmk.inventory.trees import SDKey, SDPath

from ._display_hints import AttributeDisplayHint, ColumnDisplayHintOfView


def attribute_sorter_from_hint(path: SDPath, key: SDKey, hint: AttributeDisplayHint) -> Sorter:
    return Sorter(
        ident=hint.name,
        title=hint.long_inventory_title,
        columns=["host_inventory", "host_structured_status"],
        sort_function=lambda r1, r2, **_kwargs: hint.sort_function(
            r1["host_inventory"].get_attribute(path, key),
            r2["host_inventory"].get_attribute(path, key),
        ),
        load_inv=True,
    )


def column_sorter_from_hint(hint: ColumnDisplayHintOfView) -> Sorter:
    return Sorter(
        ident=hint.name,
        title=hint.long_inventory_title,
        columns=[hint.name],
        sort_function=lambda r1, r2, **_kwargs: hint.sort_function(
            r1.get(hint.name), r2.get(hint.name)
        ),
        load_inv=False,
    )
