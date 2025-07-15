#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass

from cmk.utils.structured_data import ImmutableTree, SDKey, SDPath, SDValue

from cmk.gui.config import active_config
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _
from cmk.gui.inventory import get_short_inventory_filepath, load_tree
from cmk.gui.painter.v0 import Cell, JoinCell
from cmk.gui.type_defs import Row, Rows, ViewSpec
from cmk.gui.utils.user_errors import user_errors
from cmk.gui.view import View
from cmk.gui.visuals.filter import Filter

from ..sorter import SorterEntry


def inventory_row_post_processor(
    view: View, all_active_filters: Sequence[Filter], rows: Rows
) -> None:
    # If any painter, sorter or filter needs the information about the host's
    # inventory, then we load it and attach it as column "host_inventory"
    if _is_inventory_data_needed(view, all_active_filters):
        _add_inventory_data(rows)
        _join_inventory_rows(
            view_macros=_get_view_macros(view.spec),
            view_join_cells=view.join_cells,
            view_datasource_ident=view.datasource.ident,
            rows=rows,
        )


def _is_inventory_data_needed(view: View, all_active_filters: Sequence[Filter]) -> bool:
    if view.datasource.ident.startswith("inv") and _get_view_macros(view.spec):
        return True

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


def _get_view_macros(view_spec: ViewSpec) -> Sequence[tuple[str, str]] | None:
    return view_spec.get("inventory_join_macros", {}).get("macros")


def _add_inventory_data(rows: Rows) -> None:
    corrupted_inventory_files = set()
    for row in rows:
        if "host_name" not in row:
            continue

        try:
            row["host_inventory"] = load_tree(
                host_name=row["host_name"],
                raw_status_data_tree=row.get("host_structured_status", b""),
            )
        except Exception as e:
            if active_config.debug:
                html.show_warning("%s" % e)
            # The inventory row may be joined with other rows (perf-o-meter, ...).
            # Therefore we initialize the corrupt inventory tree with an empty tree
            # in order to display all other rows.
            row["host_inventory"] = ImmutableTree()
            corrupted_inventory_files.add(str(get_short_inventory_filepath(row["host_name"])))

    if corrupted_inventory_files:
        user_errors.add(
            MKUserError(
                "load_structured_data_tree",
                _("Cannot load HW/SW Inventory trees %s. Please remove the corrupted files.")
                % ", ".join(sorted(corrupted_inventory_files)),
            )
        )


def _join_inventory_rows(
    *,
    view_macros: Sequence[tuple[str, str]] | None,
    view_join_cells: Sequence[JoinCell],
    view_datasource_ident: str,
    rows: Rows,
) -> None:
    if not view_macros:
        return

    # First we extract the table rows for all known join inv painters.
    # With this the extraction of the relevant nodes (and their table rows)
    # is done once per path.
    if not (table_rows_by_master_key := _extract_table_rows(view_join_cells, rows)):
        return

    # Then we evaluate these rows and try to find matching row entries.
    for row in rows:
        row_values_by_macro = {
            macro: row_value
            for column_name, macro in view_macros
            if (row_value := row.get(f"{view_datasource_ident}_{column_name}")) is not None
        }

        found_values_by_ident: dict[str, list[str | int | float]] = {}
        for found_table_row in table_rows_by_master_key.get(_MasterKey.make(row), []):
            if found_table_row.matches(row_values_by_macro):
                found_values_by_ident.setdefault(found_table_row.ident, []).append(
                    found_table_row.column_value
                )

        for ident, values in found_values_by_ident.items():
            if len(values) == 1:
                row.setdefault("JOIN", {}).update({ident: {ident: values[0]}})


def _extract_table_rows(
    join_cells: Sequence[JoinCell], rows: Rows
) -> Mapping[_MasterKey, Sequence[_FoundTableRow]]:
    painter_macros_by_path_and_ident: dict[tuple[SDPath, str], list[tuple[str, str]]] = {}
    for join_cell in join_cells:
        if (
            (params := join_cell.painter_parameters()) is None
            or not (cols_to_match := params.get("columns_to_match"))
            or not (path := params.get("path_to_table"))
        ):
            continue

        for macro_column_name, macro in cols_to_match:
            painter_macros_by_path_and_ident.setdefault(
                (path, join_cell.painter_name()), []
            ).append((macro_column_name, macro))

    table_rows_by_master_key: dict[_MasterKey, list[_FoundTableRow]] = {}
    for row in rows:
        if (master_key := _MasterKey.make(row)) in table_rows_by_master_key:
            continue

        for (path, ident), painter_macros in painter_macros_by_path_and_ident.items():
            if tree := row["host_inventory"].get_tree(path):
                table_rows_by_master_key.setdefault(master_key, []).extend(
                    list(_find_table_rows(ident, painter_macros, tree.table.rows))
                )

    return table_rows_by_master_key


@dataclass(frozen=True)
class _MasterKey:
    site: str
    hostname: str

    @classmethod
    def make(cls, row: Row) -> _MasterKey:
        return _MasterKey(row["site"], row["host_name"])


@dataclass(frozen=True)
class _FoundTableRow:
    ident: str
    column_value: str | int | float
    macros: Mapping[str, str | int | float]

    def matches(self, row_values_by_macro: Mapping[str, str | int | float]) -> bool:
        return any(
            self.macros.get(macro) == row_value for macro, row_value in row_values_by_macro.items()
        )


def _find_table_rows(
    ident: str,
    painter_macros: Sequence[tuple[str, str]],
    table_rows: Sequence[Mapping[SDKey, SDValue]],
) -> Iterator[_FoundTableRow]:
    def _find_column_value_of_ident(
        ident: str, table_row: Mapping[SDKey, SDValue]
    ) -> str | int | float | None:
        for key, value in table_row.items():
            if ident.endswith(key):
                return value
        return None

    for table_row in table_rows:
        if (column_value := _find_column_value_of_ident(ident, table_row)) is None:
            continue

        yield _FoundTableRow(
            ident=ident,
            column_value=column_value,
            macros={
                macro: macro_table_value
                for macro_column_name, macro in painter_macros
                if (macro_table_value := table_row.get(SDKey(macro_column_name))) is not None
            },
        )
