#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import NamedTuple

from livestatus import lqencode, SiteId

from cmk.gui.plugins.visuals.utils import Filter, get_livestatus_filter_headers
from cmk.gui.type_defs import ColumnName, LivestatusQuery, Row, Rows
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

    inventory_join_macros = dict(view.spec.get("inventory_join_macros", {}).get("macros", []))
    join_filters = _make_join_filters(
        [
            _JoinValue(
                view.datasource.ident,
                inventory_join_macros,
                slave_ds.join_key,
                join_cell.join_value,
            )
            for join_cell in view.join_cells
        ],
        rows,
    )

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
            "\n".join(join_filters.filters),
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
        master_entry = per_master_entry.get(_make_master_key(row, join_master_column), {})

        join_info = {
            join_value.value: attrs
            for join_value in join_filters.without_macros
            if (attrs := master_entry.get(join_value.value))
        }

        join_info.update(
            {
                join_value.value: attrs
                for join_value in join_filters.with_macros
                if (attrs := master_entry.get(join_value.replace_macros(row).value))
            }
        )

        row.setdefault("JOIN", {}).update(join_info)


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


def _make_master_key(row: Row, join_master_column: str) -> tuple[SiteId, str]:
    return (SiteId(row["site"]), row[join_master_column])


@dataclass(frozen=True)
class _JoinValue:
    _datasource_ident: str
    _inventory_join_macros: dict[str, str]
    join_column_name: str
    _value: str

    @property
    def value(self) -> str:
        return self._value

    def has_macros(self) -> bool:
        return any(macro in self._value for macro in self._inventory_join_macros.values())

    def replace_macros(self, row: Row) -> _JoinValue:
        replaced_value = self._value
        for column_name, macro in self._inventory_join_macros.items():
            if (row_value := row.get(f"{self._datasource_ident}_{column_name}")) is None:
                continue
            if macro in replaced_value:
                replaced_value = replaced_value.replace(macro, row_value)
        return _JoinValue(
            self._datasource_ident,
            self._inventory_join_macros,
            self.join_column_name,
            replaced_value,
        )


class _JoinFilters(NamedTuple):
    with_macros: list[_JoinValue]
    without_macros: list[_JoinValue]
    filters: list[LivestatusQuery]


def _make_join_filters(join_values: Sequence[_JoinValue], rows: Rows) -> _JoinFilters:
    with_macros = []
    without_macros = []
    filters = []

    for join_value in join_values:
        if join_value.has_macros():
            with_macros.append(join_value)
            filters.append(_livestatus_filter_from_macros(join_value, rows))
        else:
            without_macros.append(join_value)
            filters.append(_livestatus_filter(join_value))

    filters.append("Or: %d" % len(filters))
    return _JoinFilters(
        with_macros=with_macros,
        without_macros=without_macros,
        filters=filters,
    )


def _livestatus_filter_from_macros(join_value: _JoinValue, rows: Rows) -> LivestatusQuery:
    filters_by_hostname: dict[str, list[str]] = {}
    for row in rows:
        filters_by_hostname.setdefault(row["host_name"], []).append(
            _livestatus_filter(join_value.replace_macros(row))
        )

    join_filters = []
    for host_name, filters in filters_by_hostname.items():
        join_filters.append(
            f"Filter: host_name = {host_name}"
            + "\n"
            + "\n".join(filters)
            + f"\nOr: {len(filters)}"
            + "\nAnd: 2"
        )

    joined_filters = "\n".join(join_filters)
    return f"{joined_filters}\nOr: {len(join_filters)}"


def _livestatus_filter(join_value: _JoinValue) -> LivestatusQuery:
    return f"Filter: {lqencode(join_value.join_column_name)} = {lqencode(join_value.value)}"
