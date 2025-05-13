#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
from collections.abc import Iterable, Sequence

from livestatus import LivestatusResponse, OnlySites

from cmk.ccc.hostaddress import HostName

import cmk.utils.paths
from cmk.utils.structured_data import InventoryStore, RetentionInterval, SDValue

from cmk.gui import sites
from cmk.gui.config import active_config
from cmk.gui.data_source import ABCDataSource, RowTable
from cmk.gui.display_options import display_options
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _
from cmk.gui.inventory._tree import get_history, InventoryPath, load_tree
from cmk.gui.painter.v0 import Cell
from cmk.gui.type_defs import ColumnName, Row, Rows, SingleInfos, VisualContext
from cmk.gui.utils.user_errors import user_errors
from cmk.gui.visuals import get_livestatus_filter_headers
from cmk.gui.visuals.filter import Filter


class ABCDataSourceInventory(ABCDataSource):
    @property
    def ignore_limit(self):
        return True

    @property
    @abc.abstractmethod
    def inventory_path(self) -> InventoryPath:
        raise NotImplementedError()


class ABCRowTable(RowTable):
    def __init__(self, info_names: Sequence[str], add_host_columns: Sequence[ColumnName]) -> None:
        super().__init__()
        self._info_names = info_names
        self._add_host_columns = add_host_columns

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
        for row in data:
            hostrow: Row = dict(zip(headers, row))
            for subrow in self._get_rows(hostrow):
                subrow.update(hostrow)
                rows.append(subrow)
        return rows, len(data)

    @staticmethod
    def _get_raw_data(only_sites: OnlySites, query: str) -> LivestatusResponse:
        with sites.only_sites(only_sites), sites.prepend_site():
            return sites.live().query(query)

    @abc.abstractmethod
    def _get_rows(self, hostrow: Row) -> Iterable[Row]:
        raise NotImplementedError()

    def _add_declaration_errors(self) -> None:
        pass


class RowTableInventory(ABCRowTable):
    def __init__(self, info_name: str, inventory_path: InventoryPath) -> None:
        super().__init__([info_name], ["host_structured_status", "host_childs"])
        self._inventory_path = inventory_path

    def _get_rows(self, hostrow: Row) -> Iterable[Row]:
        if not (self._info_names and (info_name := self._info_names[0])):
            return

        host_name = hostrow.get("host_name")
        try:
            table_rows = (
                load_tree(
                    host_name=host_name,
                    raw_status_data_tree=hostrow.get("host_structured_status", b""),
                )
                .get_tree(self._inventory_path.path)
                .table.rows_with_retentions
            )
        except Exception as e:
            if active_config.debug:
                html.show_warning("%s" % e)
            user_errors.add(
                MKUserError(
                    "load_inventory_tree",
                    _(
                        "Cannot load HW/SW Inventory tree of host %s."
                        " Please remove the corrupted file."
                    )
                    % host_name,
                )
            )
            return

        for table_row in table_rows:
            row: dict[str, SDValue | RetentionInterval | None] = {}
            for key, (value, retention_interval) in table_row.items():
                row["_".join([info_name, key])] = value
                row["_".join([info_name, key, "retention_interval"])] = retention_interval
            yield row


class RowTableInventoryHistory(ABCRowTable):
    def __init__(self) -> None:
        super().__init__(["invhist"], [])
        self._inventory_path = None

    def _get_rows(self, hostrow: Row) -> Iterable[Row]:
        hostname: HostName = hostrow["host_name"]
        history, corrupted_history_files = get_history(
            InventoryStore(cmk.utils.paths.omd_root),
            hostname,
        )
        if corrupted_history_files:
            user_errors.add(
                MKUserError(
                    "load_inventory_delta_tree",
                    _(
                        "Cannot load HW/SW Inventory history entries %s. Please remove the corrupted files."
                    )
                    % ", ".join(sorted(corrupted_history_files)),
                )
            )
        for history_entry in history:
            yield {
                "invhist_time": history_entry.timestamp,
                "invhist_delta": history_entry.delta_tree,
                "invhist_removed": history_entry.removed,
                "invhist_new": history_entry.new,
                "invhist_changed": history_entry.changed,
            }


class DataSourceInventoryHistory(ABCDataSource):
    @property
    def ident(self) -> str:
        return "invhist"

    @property
    def title(self) -> str:
        return _("HW/SW Inventory history")

    @property
    def table(self) -> RowTable:
        return RowTableInventoryHistory()

    @property
    def infos(self) -> SingleInfos:
        return ["host", "invhist"]

    @property
    def keys(self) -> list[ColumnName]:
        return []

    @property
    def id_keys(self) -> list[ColumnName]:
        return ["host_name", "invhist_time"]
