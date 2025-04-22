#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Hashable, Sequence

from cmk.gui.painter.v0 import Cell
from cmk.gui.type_defs import Row


def group_value(row: Row, group_cells: Sequence[Cell]) -> Hashable:
    """The Group-value of a row is used for deciding whether
    two rows are in the same group or not"""
    group = []
    for cell in group_cells:
        painter = cell.painter()

        group_by_val = painter.group_by(row, cell)
        if group_by_val is not None:
            group.append(group_by_val)

        else:
            for c in painter.columns:
                if c in row:
                    group.append(row[c])

    return _create_dict_key(group)


def _create_dict_key(value: list | dict | Hashable) -> Hashable:
    if isinstance(value, list | tuple):
        return tuple(map(_create_dict_key, value))
    if isinstance(value, dict):
        return tuple((k, _create_dict_key(v)) for (k, v) in sorted(value.items()))
    return value
