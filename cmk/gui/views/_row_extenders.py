#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from cmk.gui.painter import RowExtender
from cmk.gui.type_defs import Row, Rows
from cmk.gui.view import View
from cmk.gui.visuals.filter import Filter


def _needed_row_extenders(view: View) -> Sequence[RowExtender]:
    return list(
        dict.fromkeys(
            [
                *(
                    extender
                    for cell in view.group_cells + view.row_cells
                    for extender in cell.needed_row_extenders()
                ),
                *(
                    entry.sorter.row_extender
                    for entry in view.sorters
                    if entry.sorter.row_extender is not None
                ),
            ]
        )
    )


def row_extenders_post_processor(
    view: View,
    all_active_filters: Sequence[Filter],  # noqa: ARG001
    rows: Rows,
) -> None:
    extended_rows: Sequence[Row] = rows
    for extend_rows in _needed_row_extenders(view):
        extended_rows = extend_rows(extended_rows)
    rows[:] = extended_rows
