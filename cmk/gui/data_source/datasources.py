#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence

from livestatus import LivestatusColumn, OnlySites, Query, QuerySpecification

from cmk.gui.i18n import _
from cmk.gui.painter.v0.base import Cell
from cmk.gui.type_defs import ColumnName, Rows, SingleInfos, VisualContext
from cmk.gui.visuals.filter import Filter

from .base import ABCDataSource, RowTable
from .livestatus import DataSourceLivestatus, query_livestatus, RowTableLivestatus
from .registry import DataSourceRegistry


def register_data_sources(registry: DataSourceRegistry) -> None:
    registry.register(DataSourceHosts)
    registry.register(DataSourceHostsByGroup)
    registry.register(DataSourceServices)
    registry.register(DataSourceServicesByGroup)
    registry.register(DataSourceServicesByHostGroup)
    registry.register(DataSourceHostGroups)
    registry.register(DataSourceMergedHostGroups)
    registry.register(DataSourceServiceGroups)
    registry.register(DataSourceMergedServiceGroups)
    registry.register(DataSourceComments)
    registry.register(DataSourceDowntimes)
    registry.register(DataSourceLog)
    registry.register(DataSourceLogHostAndServiceEvents)
    registry.register(DataSourceLogHostEvents)
    registry.register(DataSourceLogAlertStatistics)
    registry.register(DataSourceServiceDiscovery)


class DataSourceHosts(DataSourceLivestatus):
    @property
    def ident(self) -> str:
        return "hosts"

    @property
    def title(self) -> str:
        return _("All hosts")

    @property
    def infos(self) -> SingleInfos:
        return ["host"]

    @property
    def keys(self):
        return ["host_name", "host_downtimes"]

    @property
    def id_keys(self):
        return ["site", "host_name"]

    @property
    def join(self):
        return ("services", "host_name")

    @property
    def link_filters(self):
        # When the single info "hostgroup" is used, use the "opthostgroup" filter
        # to handle the data provided by the single_spec value of the "hostgroup"
        # info, which is in fact the name of the wanted host group
        return {
            "hostgroup": "opthostgroup",
        }


class DataSourceHostsByGroup(DataSourceLivestatus):
    @property
    def ident(self) -> str:
        return "hostsbygroup"

    @property
    def title(self) -> str:
        return _("Hosts grouped by host groups")

    @property
    def infos(self) -> SingleInfos:
        return ["host", "hostgroup"]

    @property
    def keys(self):
        return ["host_name", "host_downtimes"]

    @property
    def id_keys(self):
        return ["site", "hostgroup_name", "host_name"]

    @property
    def join(self):
        return ("services", "host_name")


class DataSourceServices(DataSourceLivestatus):
    @property
    def ident(self) -> str:
        return "services"

    @property
    def title(self) -> str:
        return _("All services")

    @property
    def infos(self) -> SingleInfos:
        return ["service", "host"]

    @property
    def keys(self):
        return ["host_name", "service_description", "service_downtimes"]

    @property
    def id_keys(self):
        return ["site", "host_name", "service_description"]

    @property
    def join_key(self):
        return "service_description"

    @property
    def link_filters(self):
        # When the single info "hostgroup" is used, use the "opthostgroup" filter
        # to handle the data provided by the single_spec value of the "hostgroup"
        # info, which is in fact the name of the wanted host group
        return {
            "hostgroup": "opthostgroup",
            "servicegroup": "optservicegroup",
        }


class DataSourceServicesByGroup(DataSourceLivestatus):
    @property
    def ident(self) -> str:
        return "servicesbygroup"

    @property
    def title(self) -> str:
        return _("Services grouped by service groups")

    @property
    def infos(self) -> SingleInfos:
        return ["service", "host", "servicegroup"]

    @property
    def keys(self):
        return ["host_name", "service_description", "service_downtimes"]

    @property
    def id_keys(self):
        return ["site", "servicegroup_name", "host_name", "service_description"]


class DataSourceServicesByHostGroup(DataSourceLivestatus):
    @property
    def ident(self) -> str:
        return "servicesbyhostgroup"

    @property
    def title(self) -> str:
        return _("Services grouped by host groups")

    @property
    def infos(self) -> SingleInfos:
        return ["service", "host", "hostgroup"]

    @property
    def keys(self):
        return ["host_name", "service_description", "service_downtimes"]

    @property
    def id_keys(self):
        return ["site", "hostgroup_name", "host_name", "service_description"]


class DataSourceHostGroups(DataSourceLivestatus):
    @property
    def ident(self) -> str:
        return "hostgroups"

    @property
    def title(self) -> str:
        return _("Host groups")

    @property
    def infos(self) -> SingleInfos:
        return ["hostgroup"]

    @property
    def keys(self):
        return ["hostgroup_name"]

    @property
    def id_keys(self):
        return ["site", "hostgroup_name"]


class DataSourceMergedHostGroups(DataSourceLivestatus):
    """Merged groups across sites"""

    @property
    def ident(self) -> str:
        return "merged_hostgroups"

    @property
    def title(self) -> str:
        return _("Host groups, merged")

    @property
    def table(self):
        return RowTableLivestatus("hostgroups")

    @property
    def infos(self) -> SingleInfos:
        return ["hostgroup"]

    @property
    def keys(self):
        return ["hostgroup_name"]

    @property
    def id_keys(self):
        return ["hostgroup_name"]

    @property
    def merge_by(self):
        return "hostgroup_name"


class DataSourceServiceGroups(DataSourceLivestatus):
    @property
    def ident(self) -> str:
        return "servicegroups"

    @property
    def title(self) -> str:
        return _("Service groups")

    @property
    def infos(self) -> SingleInfos:
        return ["servicegroup"]

    @property
    def keys(self):
        return ["servicegroup_name"]

    @property
    def id_keys(self):
        return ["site", "servicegroup_name"]


class DataSourceMergedServiceGroups(ABCDataSource):
    """Merged groups across sites"""

    @property
    def ident(self) -> str:
        return "merged_servicegroups"

    @property
    def title(self) -> str:
        return _("Service groups, merged")

    @property
    def table(self):
        return RowTableLivestatus("servicegroups")

    @property
    def infos(self) -> SingleInfos:
        return ["servicegroup"]

    @property
    def keys(self):
        return ["servicegroup_name"]

    @property
    def id_keys(self):
        return ["servicegroup_name"]

    @property
    def merge_by(self):
        return "servicegroup_name"


class DataSourceComments(DataSourceLivestatus):
    @property
    def ident(self) -> str:
        return "comments"

    @property
    def title(self) -> str:
        return _("Host and service comments")

    @property
    def infos(self) -> SingleInfos:
        return ["comment", "host", "service"]

    @property
    def keys(self):
        return ["comment_id", "comment_type", "host_name", "service_description"]

    @property
    def id_keys(self):
        return ["site", "comment_id"]


class DataSourceDowntimes(DataSourceLivestatus):
    @property
    def ident(self) -> str:
        return "downtimes"

    @property
    def title(self) -> str:
        return _("Scheduled downtimes")

    @property
    def infos(self) -> SingleInfos:
        return ["downtime", "host", "service"]

    @property
    def keys(self):
        return ["downtime_id", "service_description"]

    @property
    def id_keys(self):
        return ["site", "downtime_id"]


class LogDataSource(DataSourceLivestatus):
    @property
    def ident(self) -> str:
        return "log"

    @property
    def table(self):
        return RowTableLivestatus("log")

    @property
    def infos(self) -> SingleInfos:
        return ["log", "host", "service", "contact", "command"]

    @property
    def keys(self):
        return []

    @property
    def id_keys(self):
        return ["log_lineno"]

    @property
    def time_filters(self):
        return ["logtime"]


class DataSourceLog(LogDataSource):
    @property
    def title(self) -> str:
        return _("The Logfile")


class DataSourceLogHostAndServiceEvents(LogDataSource):
    @property
    def ident(self) -> str:
        return "log_events"

    @property
    def title(self) -> str:
        return _("Host and service events")

    @property
    def infos(self) -> SingleInfos:
        return ["log", "host", "service"]

    @property
    def add_headers(self):
        return "Filter: class = 1\nFilter: class = 3\nFilter: class = 8\nOr: 3\n"


class DataSourceLogHostEvents(LogDataSource):
    @property
    def ident(self) -> str:
        return "log_host_events"

    @property
    def title(self) -> str:
        return _("Host events")

    @property
    def infos(self) -> SingleInfos:
        return ["log", "host"]

    @property
    def add_headers(self):
        return "Filter: class = 1\nFilter: class = 3\nFilter: class = 8\nOr: 3\nFilter: service_description = \n"


class DataSourceLogAlertStatistics(LogDataSource):
    @property
    def ident(self) -> str:
        return "alert_stats"

    @property
    def title(self) -> str:
        return _("Alert statistics")

    @property
    def infos(self) -> SingleInfos:
        return ["log", "host", "service", "contact", "command"]

    @property
    def add_columns(self):
        return [
            "log_alerts_ok",
            "log_alerts_warn",
            "log_alerts_crit",
            "log_alerts_unknown",
            "log_alerts_problem",
        ]

    @property
    def add_headers(self):
        return "Filter: class = 1\nStats: state = 0\nStats: state = 1\nStats: state = 2\nStats: state = 3\nStats: state != 0\n"

    @property
    def id_keys(self):
        return ["host_name", "service_description"]

    @property
    def ignore_limit(self):
        return True

    def post_process(self, rows: Rows) -> Rows:
        return list(filter(lambda row: row["host_name"], rows))


class DataSourceServiceDiscovery(ABCDataSource):
    @property
    def ident(self) -> str:
        return "service_discovery"

    @property
    def title(self) -> str:
        return _("Service discovery")

    @property
    def table(self):
        return ServiceDiscoveryRowTable()

    @property
    def infos(self) -> SingleInfos:
        return ["host", "discovery"]

    @property
    def keys(self):
        return []

    @property
    def id_keys(self):
        return ["host_name"]

    @property
    def add_columns(self):
        return [
            "discovery_state",
            "discovery_check",
            "discovery_service",
        ]


class ServiceDiscoveryRowTable(RowTable):
    # The livestatus query constructed by the filters of the view may
    # contain filters that are related to the discovery info and should only be
    # handled here. We need to extract them from the query, hand over the regular
    # filters to the host livestatus query and apply the others during the discovery
    # service query.

    def create_livestatus_query(self, columns: Sequence[LivestatusColumn], headers: str) -> Query:
        return Query(
            QuerySpecification(
                table="services",
                columns=columns,
                headers=headers + "Filter: check_command = check-mk-inventory\n",
            )
        )

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
        if "long_plugin_output" not in columns:
            columns.append("long_plugin_output")

        columns = [c for c in columns if c not in datasource.add_columns]
        data = query_livestatus(
            self.create_livestatus_query(columns, headers), only_sites, limit, "read"
        )

        columns = ["site"] + columns
        service_rows = [dict(zip(columns, row)) for row in data]

        rows = []
        for row in service_rows:
            for service_line in row["long_plugin_output"].split("\n"):
                if not service_line:
                    continue

                parts = [s.strip() for s in service_line.split(":", 2)]
                if len(parts) != 3:
                    continue

                state, check, service_description = parts
                if state not in [
                    "Service ignored",
                    "Service vanished",
                    "Service unmonitored",
                ]:
                    continue

                this_row = row.copy()
                this_row.update(
                    {
                        "discovery_state": state.split(" ")[1].lower(),
                        "discovery_check": check,
                        "discovery_service": service_description,
                    }
                )
                rows.append(this_row)

        return rows
