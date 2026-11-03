#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
from collections.abc import Sequence
from typing import override

import cmk.utils.paths
from cmk.ccc.hostaddress import HostName
from cmk.gui import sites
from cmk.gui.config import active_config
from cmk.gui.data_source import ABCDataSource, RowTable
from cmk.gui.display_options import display_options
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _
from cmk.gui.inventory import load_tree_of_host, report_corrupted_trees
from cmk.gui.inventory._tree import get_history
from cmk.gui.painter import Cell
from cmk.gui.type_defs import ColumnName, Row, Rows, SingleInfos, VisualContext
from cmk.gui.utils.user_errors import user_errors
from cmk.gui.visuals import get_livestatus_filter_headers
from cmk.gui.visuals.filter import Filter
from cmk.inventory.history import HistoryStore
from cmk.inventory.raw_paths import InventoryPath
from cmk.livestatus_client import LivestatusResponse, OnlySites


class ABCDataSourceInventory(ABCDataSource):
    @property
    @override
    def ignore_limit(self) -> bool:
        return True

    @property
    @abc.abstractmethod
    def inventory_path(self) -> InventoryPath:
        raise NotImplementedError


class ABCRowTable(RowTable):
    def __init__(self, info_names: Sequence[str], add_host_columns: Sequence[ColumnName]) -> None:
        super().__init__()
        self._info_names = info_names
        self._add_host_columns = add_host_columns

    @override
    def query(
        self,
        datasource: ABCDataSource,
        cells: Sequence[Cell],
        columns: Sequence[ColumnName],
        context: VisualContext,
        _unused_headers: str,
        only_sites: OnlySites,
        limit: object,
        all_active_filters: Sequence[Filter],
    ) -> tuple[Rows, int] | Rows:
        self._add_declaration_errors()

        # Create livestatus filter for filtering out hosts
        host_columns = [
            "host_name",
            *{c for c in columns if c.startswith("host_") and c != "host_name"},
            *self._add_host_columns,
        ]

        query = "GET hosts\n"
        query += "Columns: " + (" ".join(host_columns)) + "\n"

        query += "".join(get_livestatus_filter_headers(context, all_active_filters))

        if (
            active_config.debug_livestatus_queries
            and html.output_format == "html"
            and display_options.enabled(display_options.W)
        ):
            html.open_div(class_="livestatus message", onmouseover="this.style.display='none';")
            html.open_tt()
            html.write_text_permissive(query.replace("\n", "<br>\n"))
            html.close_tt()
            html.close_div()

        data = self._get_raw_data(only_sites, query)

        # Now create big table of all inventory entries of these hosts
        headers = ["site", *host_columns]
        rows = []
        corrupted_host_names = []
        for row in data:
            hostrow: Row = dict(zip(headers, row))
            if (subrows := self._get_rows(hostrow)) is None:
                corrupted_host_names.append(hostrow["host_name"])
                continue
            for subrow in subrows:
                subrow.update(hostrow)
                rows.append(subrow)
        if corrupted_host_names:
            report_corrupted_trees(corrupted_host_names)
        return rows, len(data)

    @staticmethod
    def _get_raw_data(only_sites: OnlySites, query: str) -> LivestatusResponse:
        with sites.only_sites(only_sites), sites.prepend_site():
            return sites.live().query(query)

    @abc.abstractmethod
    def _get_rows(self, hostrow: Row) -> Sequence[Row] | None:
        raise NotImplementedError

    def _add_declaration_errors(self) -> None:
        pass


class RowTableInventory(ABCRowTable):
    def __init__(self, info_name: str, inventory_path: InventoryPath) -> None:
        super().__init__([info_name], ["host_structured_status", "host_childs"])
        self._inventory_path = inventory_path

    @override
    def _get_rows(self, hostrow: Row) -> Sequence[Row] | None:
        if not (self._info_names and (info_name := self._info_names[0])):
            return []

        if (
            tree := load_tree_of_host(
                raw_host_name=hostrow["host_name"],
                raw_status_data_tree=hostrow.get("host_structured_status", b""),
                debug=active_config.debug,
            )
        ) is None:
            return None

        rows: list[Row] = []
        for table_row in tree.get_tree(self._inventory_path.path).table.rows_with_retentions:
            row: Row = {}
            for key, (value, retention_interval) in table_row.items():
                row[f"{info_name}_{key}"] = value
                row[f"{info_name}_{key}_retention_interval"] = retention_interval
            rows.append(row)
        return rows


class RowTableInventoryHistory(ABCRowTable):
    def __init__(self) -> None:
        super().__init__(["invhist"], [])
        self._inventory_path = None

    @override
    def _get_rows(self, hostrow: Row) -> Sequence[Row] | None:
        hostname = HostName(hostrow["host_name"])
        history, corrupted_history_files = get_history(
            HistoryStore(cmk.utils.paths.omd_root),
            hostname,
        )
        if corrupted_history_files:
            user_errors.add(
                MKUserError(
                    "load_inventory_delta_tree",
                    _(
                        "Cannot load HW/SW inventory history entries %(files)s. Please remove the corrupted files."
                    )
                    % {"files": ", ".join(sorted(corrupted_history_files))},
                )
            )
        return [
            {
                "invhist_time": history_entry.current_timestamp,
                "invhist_delta": history_entry.delta_tree,
                "invhist_removed": history_entry.removed,
                "invhist_new": history_entry.new,
                "invhist_changed": history_entry.changed,
            }
            for history_entry in history
        ]


class DataSourceInventoryHistory(ABCDataSource):
    @property
    @override
    def ident(self) -> str:
        return "invhist"

    @property
    @override
    def title(self) -> str:
        return _("HW/SW inventory history")

    @property
    @override
    def table(self) -> RowTable:
        return RowTableInventoryHistory()

    @property
    @override
    def infos(self) -> SingleInfos:
        return ["host", "invhist"]

    @property
    @override
    def keys(self) -> list[ColumnName]:
        return []

    @property
    @override
    def id_keys(self) -> list[ColumnName]:
        return ["host_name", "invhist_time"]
