#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Sequence

from cmk.agent_based.v2 import Attributes, TableRow


def sort_inventory_result(
    result: Iterable[Attributes | TableRow],
) -> Sequence[Attributes | TableRow]:
    return sorted(
        result,
        key=lambda r: (
            (
                sorted(r.key_columns.items()),
                sorted(r.inventory_columns.items()),
                sorted(r.status_columns.items()),
            )
            if isinstance(r, TableRow)
            else (
                sorted(r.inventory_attributes.items()),
                sorted(r.status_attributes.items()),
            )
        ),
    )
