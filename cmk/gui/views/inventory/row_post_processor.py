#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from cmk.utils.structured_data import StructuredDataNode

from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.inventory import (
    get_short_inventory_filepath,
    load_filtered_and_merged_tree,
    LoadStructuredDataError,
)
from cmk.gui.plugins.visuals.utils import Filter
from cmk.gui.type_defs import Rows
from cmk.gui.utils.user_errors import user_errors
from cmk.gui.view import View

from ..painter.v0.base import Cell
from ..sorter import SorterEntry


def inventory_row_post_processor(
    view: View, all_active_filters: Sequence[Filter], rows: Rows
) -> None:
    # If any painter, sorter or filter needs the information about the host's
    # inventory, then we load it and attach it as column "host_inventory"
    if _is_inventory_data_needed(view, all_active_filters):
        _add_inventory_data(rows)


def _is_inventory_data_needed(view: View, all_active_filters: Sequence[Filter]) -> bool:
    group_cells: list[Cell] = view.group_cells
    cells: list[Cell] = view.row_cells
    sorters: list[SorterEntry] = view.sorters

    for cell in cells:
        if cell.has_tooltip():
            if cell.tooltip_painter_name().startswith("inv_"):
                return True

    for entry in sorters:
        if entry.sorter.load_inv:
            return True

    for cell in group_cells + cells:
        if cell.painter().load_inv:
            return True

    for filt in all_active_filters:
        if filt.need_inventory(view.context.get(filt.ident, {})):
            return True

    return False


def _add_inventory_data(rows: Rows) -> None:
    corrupted_inventory_files = []
    for row in rows:
        if "host_name" not in row:
            continue

        try:
            row["host_inventory"] = load_filtered_and_merged_tree(row)
        except LoadStructuredDataError:
            # The inventory row may be joined with other rows (perf-o-meter, ...).
            # Therefore we initialize the corrupt inventory tree with an empty tree
            # in order to display all other rows.
            row["host_inventory"] = StructuredDataNode()
            corrupted_inventory_files.append(str(get_short_inventory_filepath(row["host_name"])))

            if corrupted_inventory_files:
                user_errors.add(
                    MKUserError(
                        "load_structured_data_tree",
                        _(
                            "Cannot load HW/SW inventory trees %s. Please remove the corrupted files."
                        )
                        % ", ".join(sorted(corrupted_inventory_files)),
                    )
                )
