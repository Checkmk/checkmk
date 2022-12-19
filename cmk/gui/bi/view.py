#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Sequence

from livestatus import OnlySites

from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.plugins.visuals.utils import Filter, get_livestatus_filter_headers
from cmk.gui.type_defs import ColumnName, Rows, SingleInfos, VisualContext
from cmk.gui.views.data_source import ABCDataSource, RowTable
from cmk.gui.views.painter.v0.base import Cell

from cmk.bi.computer import BIAggregationFilter

from .bi_manager import BIManager

#     ____        _
#    |  _ \  __ _| |_ __ _ ___  ___  _   _ _ __ ___ ___  ___
#    | | | |/ _` | __/ _` / __|/ _ \| | | | '__/ __/ _ \/ __|
#    | |_| | (_| | || (_| \__ \ (_) | |_| | | | (_|  __/\__ \
#    |____/ \__,_|\__\__,_|___/\___/ \__,_|_|  \___\___||___/
#


class DataSourceBIAggregations(ABCDataSource):
    @property
    def ident(self) -> str:
        return "bi_aggregations"

    @property
    def title(self) -> str:
        return _("BI Aggregations")

    @property
    def table(self) -> RowTable:
        return RowTableBIAggregations()

    @property
    def infos(self) -> SingleInfos:
        return ["aggr", "aggr_group"]

    @property
    def unsupported_columns(self) -> list[ColumnName]:
        return ["site"]

    @property
    def keys(self) -> list[ColumnName]:
        return []

    @property
    def id_keys(self) -> list[ColumnName]:
        return ["aggr_name"]


class RowTableBIAggregations(RowTable):
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
        return table(context, columns, headers, only_sites, limit, all_active_filters)


class DataSourceBIHostAggregations(ABCDataSource):
    @property
    def ident(self) -> str:
        return "bi_host_aggregations"

    @property
    def title(self) -> str:
        return _("BI Aggregations affected by one host")

    @property
    def table(self) -> RowTable:
        return RowTableBIHostAggregations()

    @property
    def infos(self) -> SingleInfos:
        return ["aggr", "host", "aggr_group"]

    @property
    def keys(self) -> list[ColumnName]:
        return []

    @property
    def id_keys(self) -> list[ColumnName]:
        return ["aggr_name"]


class RowTableBIHostAggregations(RowTable):
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
        return host_table(context, columns, headers, only_sites, limit, all_active_filters)


class DataSourceBIHostnameAggregations(ABCDataSource):
    """Similar to host aggregations, but the name of the aggregation
    is used to join the host table rather then the affected host"""

    @property
    def ident(self) -> str:
        return "bi_hostname_aggregations"

    @property
    def title(self) -> str:
        return _("BI Hostname Aggregations")

    @property
    def table(self) -> RowTable:
        return RowTableBIHostnameAggregations()

    @property
    def infos(self) -> SingleInfos:
        return ["aggr", "host", "aggr_group"]

    @property
    def keys(self) -> list[ColumnName]:
        return []

    @property
    def id_keys(self) -> list[ColumnName]:
        return ["aggr_name"]


class RowTableBIHostnameAggregations(RowTable):
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
        return hostname_table(context, columns, headers, only_sites, limit, all_active_filters)


class DataSourceBIHostnameByGroupAggregations(ABCDataSource):
    """The same but with group information"""

    @property
    def ident(self) -> str:
        return "bi_hostnamebygroup_aggregations"

    @property
    def title(self) -> str:
        return _("BI aggregations for hosts by host groups")

    @property
    def table(self) -> RowTable:
        return RowTableBIHostnameByGroupAggregations()

    @property
    def infos(self) -> SingleInfos:
        return ["aggr", "host", "hostgroup", "aggr_group"]

    @property
    def keys(self) -> list[ColumnName]:
        return []

    @property
    def id_keys(self) -> list[ColumnName]:
        return ["aggr_name"]


class RowTableBIHostnameByGroupAggregations(RowTable):
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
        return hostname_by_group_table(
            context, columns, headers, only_sites, limit, all_active_filters
        )


def table(
    context: VisualContext,
    columns: list[ColumnName],
    query: str,
    only_sites: OnlySites,
    limit: int | None,
    all_active_filters: Iterable[Filter],
) -> list[dict]:
    bi_aggregation_filter = compute_bi_aggregation_filter(context, all_active_filters)
    bi_manager = BIManager()
    bi_manager.status_fetcher.set_assumed_states(user.bi_assumptions)
    return bi_manager.computer.compute_legacy_result_for_filter(bi_aggregation_filter)


def hostname_table(
    context: VisualContext,
    columns: list[ColumnName],
    query: str,
    only_sites: OnlySites,
    limit: int | None,
    all_active_filters: Iterable[Filter],
) -> Rows:
    """Table of all host aggregations, i.e. aggregations using data from exactly one host"""
    return singlehost_table(
        context,
        columns,
        query,
        only_sites,
        limit,
        all_active_filters,
        joinbyname=True,
        bygroup=False,
    )


def hostname_by_group_table(
    context: VisualContext,
    columns: list[ColumnName],
    query: str,
    only_sites: OnlySites,
    limit: int | None,
    all_active_filters: Iterable[Filter],
) -> Rows:
    return singlehost_table(
        context,
        columns,
        query,
        only_sites,
        limit,
        all_active_filters,
        joinbyname=True,
        bygroup=True,
    )


def host_table(
    context: VisualContext,
    columns: list[ColumnName],
    query: str,
    only_sites: OnlySites,
    limit: int | None,
    all_active_filters: Iterable[Filter],
) -> Rows:
    return singlehost_table(
        context,
        columns,
        query,
        only_sites,
        limit,
        all_active_filters,
        joinbyname=False,
        bygroup=False,
    )


def singlehost_table(
    context: VisualContext,
    columns: list[ColumnName],
    query: str,
    only_sites: OnlySites,
    limit: int | None,
    all_active_filters: Iterable[Filter],
    joinbyname: bool,
    bygroup: bool,
) -> Rows:
    filterheaders = "".join(get_livestatus_filter_headers(context, all_active_filters))
    host_columns = [c for c in columns if c.startswith("host_")]

    rows = []
    bi_manager = BIManager()
    bi_manager.status_fetcher.set_assumed_states(user.bi_assumptions)
    bi_aggregation_filter = compute_bi_aggregation_filter(context, all_active_filters)
    required_aggregations = bi_manager.computer.get_required_aggregations(bi_aggregation_filter)
    bi_manager.status_fetcher.update_states_filtered(
        filterheaders, only_sites, limit, host_columns, bygroup, required_aggregations
    )

    aggregation_results = bi_manager.computer.compute_results(required_aggregations)
    legacy_results = bi_manager.computer.convert_to_legacy_results(
        aggregation_results, bi_aggregation_filter
    )

    for site_host_name, values in bi_manager.status_fetcher.states.items():
        for legacy_result in legacy_results:
            if site_host_name in legacy_result["aggr_hosts"]:
                # Combine bi columns + extra livestatus columns + bi computation columns into one row
                row = values._asdict()
                row.update(row["remaining_row_keys"])
                del row["remaining_row_keys"]
                row.update(legacy_result)
                row["site"] = site_host_name[0]
                rows.append(row)
    return rows


def compute_bi_aggregation_filter(
    context: VisualContext, all_active_filters: Iterable[Filter]
) -> BIAggregationFilter:
    only_hosts = []
    only_group = []
    only_service = []
    only_aggr_name = []
    group_prefix = []

    for active_filter in all_active_filters:
        conf = context.get(active_filter.ident, {})

        if active_filter.ident == "aggr_hosts":
            if (host_name := conf.get("aggr_host_host", "")) != "":
                only_hosts = [host_name]
        elif active_filter.ident == "aggr_group":
            if aggr_group := conf.get(active_filter.htmlvars[0]):
                only_group = [aggr_group]
        elif active_filter.ident == "aggr_service":
            service_spec = tuple(conf.get(var, "") for var in active_filter.htmlvars)
            # service_spec: site_id, host, service
            # Since no data has been fetched yet, the site is also unknown
            if all(service_spec):
                only_service = [(service_spec[1], service_spec[2])]
        elif active_filter.ident == "aggr_name":
            if aggr_name := conf.get("aggr_name"):
                only_aggr_name = [aggr_name]
        elif active_filter.ident == "aggr_group_tree":
            if group_name := conf.get("aggr_group_tree"):
                group_prefix = [group_name]

    # BIAggregationFilter
    # ("hosts", List[HostName]),
    # ("services", List[Tuple[HostName, ServiceName]]),
    # ("aggr_ids", List[str]),
    # ("aggr_names", List[str]),
    # ("aggr_groups", List[str]),
    # ("aggr_paths", List[List[str]]),
    return BIAggregationFilter(
        only_hosts,  # hosts
        only_service,  # services
        [],  # ids
        only_aggr_name,  # names
        only_group,  # groups
        group_prefix,  # paths
    )
