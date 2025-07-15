#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import functools
from collections.abc import Callable, Sequence
from typing import cast

from livestatus import LivestatusColumn, LivestatusRow, OnlySites, Query, QuerySpecification

from cmk.gui import sites
from cmk.gui.config import active_config
from cmk.gui.display_options import display_options
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.painter.v0 import Cell
from cmk.gui.type_defs import ColumnName, Rows, VisualContext
from cmk.gui.visuals.filter import Filter
from cmk.utils.check_utils import worst_service_state

from .base import ABCDataSource, RowTable


class DataSourceLivestatus(ABCDataSource):
    """Base class for all simple data sources which 1:1 base on a livestatus table"""

    @property
    def table(self) -> RowTableLivestatus:
        return RowTableLivestatus(self.ident)


class RowTableLivestatus(RowTable):
    def __init__(self, table_name: str) -> None:
        super().__init__()
        self._table_name = table_name

    @property
    def table_name(self) -> str:
        return self._table_name

    @staticmethod
    def _prepare_columns(
        datasource: ABCDataSource,
        cells: Sequence[Cell],
        columns: list[ColumnName],
    ) -> tuple[list[ColumnName], dict[int, list[ColumnName]]]:
        dynamic_columns = {}
        for index, cell in enumerate(cells):
            dyn_col = cell.painter().dynamic_columns(cell)
            dynamic_columns[index] = dyn_col
            columns += dyn_col

        # Prevent merge column from being duplicated in the query
        columns = list(set(columns + ([datasource.merge_by] if datasource.merge_by else [])))

        # Most layouts need current state of object in order to
        # choose background color - even if no painter for state
        # is selected. Make sure those columns are fetched. This
        # must not be done for the table 'log' as it cannot correctly
        # distinguish between service_state and host_state
        if "log" not in datasource.infos:
            state_columns: list[ColumnName] = []
            if "service" in datasource.infos:
                state_columns += ["service_has_been_checked", "service_state"]
            if "host" in datasource.infos:
                state_columns += ["host_has_been_checked", "host_state"]
            for c in state_columns:
                if c not in columns:
                    columns.append(c)

        # Remove columns which are implicitly added by the datasource. We sort the remaining
        # columns to allow for repeatable tests.
        return [c for c in sorted(columns) if c not in datasource.add_columns], dynamic_columns

    def create_livestatus_query(self, columns: Sequence[LivestatusColumn], headers: str) -> Query:
        return Query(QuerySpecification(table=self.table_name, columns=columns, headers=headers))

    def query(
        self,
        datasource: ABCDataSource,
        cells: Sequence[Cell],
        columns: list[ColumnName],
        context: VisualContext,
        headers: str,
        only_sites: OnlySites,
        limit: int | None,
        all_active_filters: list[Filter],
    ) -> Rows | tuple[Rows, int]:
        """Retrieve data via livestatus, convert into list of dicts,

        datasource: The data source to query
        columns: the list of livestatus columns to query
        headers: query headers
        only_sites: list of sites the query is limited to
        limit: maximum number of data rows to query
        all_active_filters: Momentarily unused
        """
        columns, dynamic_columns = self._prepare_columns(datasource, cells, columns)
        data = query_livestatus(
            self.create_livestatus_query(columns, headers + datasource.add_headers),
            only_sites,
            limit,
            datasource.auth_domain,
        )

        if merge_column := datasource.merge_by:
            data = _merge_data(data, columns, merge_column)

        # convert lists-rows into dictionaries.
        # performance, but makes live much easier later.
        columns = ["site"] + columns + datasource.add_columns
        rows: Rows = datasource.post_process([dict(zip(columns, row)) for row in data])

        for index, cell in enumerate(cells):
            painter = cell.painter()
            painter.derive(rows, cell, dynamic_columns.get(index, []))

        return rows, len(data)


def debug_livestatus(query: Query) -> None:
    if all(
        (
            active_config.debug_livestatus_queries,
            request.accept_mimetypes.accept_html,
            display_options.enabled(display_options.W),
        )
    ):
        html.open_div(class_=["livestatus", "message"])
        html.tt(str(query).replace("\n", "<br>\n"))
        html.close_div()


def query_row(
    query: Query, only_sites: OnlySites, limit: int | None, auth_domain: str
) -> LivestatusRow:
    debug_livestatus(query)

    sites.live().set_auth_domain(auth_domain)

    with sites.only_sites(only_sites), sites.prepend_site(), sites.set_limit(limit):
        row = sites.live().query_row(query)

    sites.live().set_auth_domain("read")

    return row


def query_livestatus(
    query: Query, only_sites: OnlySites, limit: int | None, auth_domain: str
) -> list[LivestatusRow]:
    debug_livestatus(query)

    sites.live().set_auth_domain(auth_domain)
    with sites.only_sites(only_sites), sites.prepend_site(), sites.set_limit(limit):
        data = sites.live().query(query)

    sites.live().set_auth_domain("read")

    return data


def _merge_data(
    data: list[LivestatusRow],
    columns: list[ColumnName],
    merge_column: ColumnName,
) -> list[LivestatusRow]:
    """Merge all data rows with different sites but the same value in merge_column

    We require that all column names are prefixed with the tablename. The column with the merge key
    is required to be the *second* column (right after the site column)"""
    merged: dict[ColumnName, LivestatusRow] = {}

    mergefuncs: list[Callable[[LivestatusColumn, LivestatusColumn], LivestatusColumn]] = [
        # site column is not merged
        lambda a, b: ""
    ]

    def worst_host_state(a, b):
        if a == 1 or b == 1:
            return 1
        return max(a, b)

    for c in columns:
        _tablename, col = c.split("_", 1)
        if col.startswith("num_") or col.startswith("members"):
            mergefunc = lambda a, b: a + b
        elif col.startswith("worst_service"):
            mergefunc = functools.partial(worst_service_state, default=3)
        elif col.startswith("worst_host"):
            mergefunc = worst_host_state
        else:
            mergefunc = lambda a, b: a

        mergefuncs.append(mergefunc)

    merge_column_index = columns.index(merge_column) + 1  # first entry in row is the site
    for row in data:
        mergekey = row[merge_column_index]
        if mergekey in merged:
            merged[mergekey] = cast(
                LivestatusRow, [f(a, b) for f, a, b in zip(mergefuncs, merged[mergekey], row)]
            )
        else:
            merged[mergekey] = row

    # return all rows sorted according to merge key
    mergekeys = sorted(merged.keys())
    return [merged[k] for k in mergekeys]
