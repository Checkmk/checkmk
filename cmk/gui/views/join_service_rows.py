#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from livestatus import SiteId

from cmk.gui.plugins.visuals.utils import Filter, get_livestatus_filter_headers
from cmk.gui.type_defs import ColumnName, Row, Rows
from cmk.gui.view import View
from cmk.gui.views.data_source import data_source_registry
from cmk.gui.views.painter.v0.base import columns_of_cells, JoinCell
from cmk.gui.views.sorter import SorterEntry
from cmk.gui.views.store import get_permitted_views


def join_service_row_post_processor(
    view: View, all_active_filters: Sequence[Filter], rows: Rows
) -> None:
    if not view.join_cells:
        return

    if not (isinstance(join := view.datasource.join, tuple) and len(join) == 2):
        raise ValueError()

    join_table, join_master_column = join
    slave_ds = data_source_registry[join_table]()

    if slave_ds.join_key is None:
        raise ValueError()

    row_data = slave_ds.table.query(
        view.datasource,
        view.row_cells,
        columns=list(
            set(
                [join_master_column, slave_ds.join_key]
                + _get_needed_join_columns(view.join_cells, view.sorters)
            )
        ),
        context=view.context,
        headers="{}{}\n".format(
            "".join(get_livestatus_filter_headers(view.context, all_active_filters)),
            "\n".join(_make_join_filters(view.join_cells, slave_ds.join_key)),
        ),
        only_sites=view.only_sites,
        limit=None,
        all_active_filters=[],
    )

    if isinstance(row_data, tuple):
        join_rows, _unfiltered_amount_of_rows = row_data
    else:
        join_rows = row_data

    per_master_entry: dict[tuple[SiteId, str], dict[str, Row]] = {}
    for row in join_rows:
        current_entry = per_master_entry.setdefault(_make_master_key(row, join_master_column), {})
        current_entry[row[slave_ds.join_key]] = row

    # Add this information into master table in artificial column "JOIN"
    for row in rows:
        row.setdefault("JOIN", {}).update(
            per_master_entry.get(_make_master_key(row, join_master_column), {})
        )


def _get_needed_join_columns(
    join_cells: list[JoinCell], sorters: list[SorterEntry]
) -> list[ColumnName]:
    join_columns = columns_of_cells(join_cells, get_permitted_views())

    # Columns needed for sorters
    # TODO: Move sorter parsing and logic to something like Cells()
    for entry in sorters:
        join_columns.update(entry.sorter.columns)

    # Remove (implicit) site column
    try:
        join_columns.remove("site")
    except KeyError:
        pass

    return list(join_columns)


def _make_join_filters(join_cells: list[JoinCell], join_key: str) -> list[str]:
    join_filters = [join_cell.livestatus_filter(join_key) for join_cell in join_cells]
    join_filters.append("Or: %d" % len(join_filters))
    return join_filters


def _make_master_key(row: Row, join_master_column: str) -> tuple[SiteId, str]:
    return (SiteId(row["site"]), row[join_master_column])
