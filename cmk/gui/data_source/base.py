#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import abc
from collections.abc import Sequence

from livestatus import OnlySites

from cmk.gui.painter.v0 import Cell
from cmk.gui.type_defs import ColumnName, Rows, SingleInfos, VisualContext
from cmk.gui.visuals.filter import Filter


class RowTable(abc.ABC):
    @abc.abstractmethod
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
        raise NotImplementedError()


class ABCDataSource(abc.ABC):
    """Provider of rows for the views (basically tables of data) in the GUI"""

    @property
    @abc.abstractmethod
    def ident(self) -> str:
        """The identity of a data source. One word, may contain alpha numeric characters"""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def title(self) -> str:
        """Used as display-string for the datasource in the GUI (e.g. view editor)"""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def table(self) -> RowTable:
        """Returns a table object that can provide a list of rows for the provided
        query using the query() method."""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def infos(self) -> SingleInfos:
        """Infos that are available with this data sources

        A info is used to create groups out of single painters and filters.
        e.g. 'host' groups all painters and filters which begin with "host_".
        Out of this declaration multisite knows which filters or painters are
        available for the single datasources."""
        raise NotImplementedError()

    @property
    def merge_by(self) -> str | None:
        """
        1. Results in fetching these columns from the datasource.
        2. Rows from different sites are merged together. For example members
           of hostgroups which exist on different sites are merged together to
           show the user one big hostgroup.
        """
        return None

    @property
    def add_columns(self) -> list[ColumnName]:
        """These columns are requested automatically in addition to the
        other needed columns."""
        return []

    @property
    def unsupported_columns(self) -> list[ColumnName]:
        """These columns are ignored, e.g. 'site' for DataSourceBIAggregations"""
        return []

    @property
    def add_headers(self) -> str:
        """additional livestatus headers to add to each call"""
        return ""

    @property
    @abc.abstractmethod
    def keys(self) -> list[ColumnName]:
        """columns which must be fetched in order to execute commands on
        the items (= in order to identify the items and gather all information
        needed for constructing Nagios commands)
        those columns are always fetched from the datasource for each item"""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def id_keys(self) -> list[ColumnName]:
        """These are used to generate a key which is unique for each data row
        is used to identify an item between http requests"""
        raise NotImplementedError()

    @property
    def join(self) -> tuple[str, str] | None:
        """A view can display e.g. host-rows and include information from e.g.
        the service table to create a column which shows e.g. the state of one
        service.
        With this attibute it is configured which tables can be joined into
        this table and by which attribute. It must be given as tuple, while
        the first argument is the name of the table to be joined and the second
        argument is the column in the master table (in this case hosts) which
        is used to match the rows of the master and slave table."""
        return None

    @property
    def join_key(self) -> str | None:
        """Each joined column in the view can have a 4th attribute which is
        used as value for this column to filter the datasource query
        to get the matching row of the slave table."""
        return None

    @property
    def ignore_limit(self) -> bool:
        """Ignore the soft/hard query limits in view.py/query_data(). This
        fixes stats queries on e.g. the log table."""
        return False

    @property
    def auth_domain(self) -> str:
        """Querying a table might require to use another auth domain than
        the default one (read). When this is set, the given auth domain
        will be used while fetching the data for this datasource from
        livestatus."""
        return "read"

    @property
    def time_filters(self) -> list[str]:
        return []

    @property
    def link_filters(self) -> dict[str, str]:
        """When the single info "hostgroup" is used, use the "opthostgroup" filter
        to handle the data provided by the single_spec value of the "hostgroup"
        info, which is in fact the name of the wanted hostgroup"""
        return {}

    # TODO: This can be cleaned up later
    def post_process(self, rows: Rows) -> Rows:
        """Optional function to postprocess the resulting data after executing
        the regular data fetching"""
        return rows
