#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

from cmk.gui.i18n import _

from cmk.gui.plugins.views import (
    data_source_registry,
    DataSource,
    DataSourceLivestatus,
    RowTable,
    RowTableLivestatus,
    query_livestatus,
)


@data_source_registry.register
class DataSourceHosts(DataSourceLivestatus):
    @property
    def ident(self):
        return "hosts"

    @property
    def title(self):
        return _("All hosts")

    @property
    def infos(self):
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
        # info, which is in fact the name of the wanted hostgroup
        return {
            "hostgroup": "opthostgroup",
        }


@data_source_registry.register
class DataSourceHostsByGroup(DataSourceLivestatus):
    @property
    def ident(self):
        return "hostsbygroup"

    @property
    def title(self):
        return _("Hosts grouped by host groups")

    @property
    def infos(self):
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


@data_source_registry.register
class DataSourceServices(DataSourceLivestatus):
    @property
    def ident(self):
        return "services"

    @property
    def title(self):
        return _("All services")

    @property
    def infos(self):
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
        # info, which is in fact the name of the wanted hostgroup
        return {
            "hostgroup": "opthostgroup",
            "servicegroup": "optservicegroup",
        }


@data_source_registry.register
class DataSourceServicesByGroup(DataSourceLivestatus):
    @property
    def ident(self):
        return "servicesbygroup"

    @property
    def title(self):
        return _("Services grouped by service groups")

    @property
    def infos(self):
        return ["service", "host", "servicegroup"]

    @property
    def keys(self):
        return ["host_name", "service_description", "service_downtimes"]

    @property
    def id_keys(self):
        return ["site", "servicegroup_name", "host_name", "service_description"]


@data_source_registry.register
class DataSourceServicesByHostGroup(DataSourceLivestatus):
    @property
    def ident(self):
        return "servicesbyhostgroup"

    @property
    def title(self):
        return _("Services grouped by host groups")

    @property
    def infos(self):
        return ["service", "host", "hostgroup"]

    @property
    def keys(self):
        return ["host_name", "service_description", "service_downtimes"]

    @property
    def id_keys(self):
        return ["site", "hostgroup_name", "host_name", "service_description"]


@data_source_registry.register
class DataSourceHostGroups(DataSourceLivestatus):
    @property
    def ident(self):
        return "hostgroups"

    @property
    def title(self):
        return _("Hostgroups")

    @property
    def infos(self):
        return ["hostgroup"]

    @property
    def keys(self):
        return ["hostgroup_name"]

    @property
    def id_keys(self):
        return ["site", "hostgroup_name"]


@data_source_registry.register
class DataSourceMergedHostGroups(DataSourceLivestatus):
    """Merged groups across sites"""
    @property
    def ident(self):
        return "merged_hostgroups"

    @property
    def title(self):
        return _("Hostgroups, merged")

    @property
    def infos(self):
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


@data_source_registry.register
class DataSourceServiceGroups(DataSourceLivestatus):
    @property
    def ident(self):
        return "servicegroups"

    @property
    def title(self):
        return _("Servicegroups")

    @property
    def infos(self):
        return ["servicegroup"]

    @property
    def keys(self):
        return ["servicegroup_name"]

    @property
    def id_keys(self):
        return ["site", "servicegroup_name"]


@data_source_registry.register
class DataSourceMergedServiceGroups(DataSource):
    """Merged groups across sites"""
    @property
    def ident(self):
        return "merged_servicegroups"

    @property
    def title(self):
        return _("Servicegroups, merged")

    @property
    def table(self):
        return RowTableLivestatus("servicegroups")

    @property
    def infos(self):
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


@data_source_registry.register
class DataSourceComments(DataSourceLivestatus):
    @property
    def ident(self):
        return "comments"

    @property
    def title(self):
        return _("Host- and Servicecomments")

    @property
    def infos(self):
        return ["comment", "host", "service"]

    @property
    def keys(self):
        return ["comment_id", "comment_type", "host_name", "service_description"]

    @property
    def id_keys(self):
        return ["comment_id"]


@data_source_registry.register
class DataSourceDowntimes(DataSourceLivestatus):
    @property
    def ident(self):
        return "downtimes"

    @property
    def title(self):
        return _("Scheduled Downtimes")

    @property
    def infos(self):
        return ["downtime", "host", "service"]

    @property
    def keys(self):
        return ["downtime_id", "service_description"]

    @property
    def id_keys(self):
        return ["downtime_id"]


class LogDataSource(DataSourceLivestatus):
    @property
    def ident(self):
        return "log"

    @property
    def table(self):
        return RowTableLivestatus("log")

    @property
    def infos(self):
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


@data_source_registry.register
class DataSourceLog(LogDataSource):
    @property
    def title(self):
        return _("The Logfile")


@data_source_registry.register
class DataSourceLogHostAndServiceEvents(LogDataSource):
    @property
    def ident(self):
        return "log_events"

    @property
    def title(self):
        return _("Host and Service Events")

    @property
    def infos(self):
        return ["log", "host", "service"]

    @property
    def add_headers(self):
        return "Filter: class = 1\nFilter: class = 3\nFilter: class = 8\nOr: 3\n"


@data_source_registry.register
class DataSourceLogHostEvents(LogDataSource):
    @property
    def ident(self):
        return "log_host_events"

    @property
    def title(self):
        return _("Host Events")

    @property
    def infos(self):
        return ["log", "host"]

    @property
    def add_headers(self):
        return "Filter: class = 1\nFilter: class = 3\nFilter: class = 8\nOr: 3\nFilter: service_description = \n"


@data_source_registry.register
class DataSourceLogAlertStatistics(LogDataSource):
    @property
    def ident(self):
        return "alert_stats"

    @property
    def title(self):
        return _("Alert Statistics")

    @property
    def infos(self):
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
        return ['host_name', 'service_description']

    @property
    def ignore_limit(self):
        return True


@data_source_registry.register
class DataSourceServiceDiscovery(DataSource):
    @property
    def ident(self):
        return "service_discovery"

    @property
    def title(self):
        return _("Service discovery")

    @property
    def table(self):
        return ServiceDiscoveryRowTable()

    @property
    def infos(self):
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

    def prepare_lql(self, columns, headers):
        query = "GET services\n"
        query += "Columns: %s\n" % " ".join(columns)
        query += headers
        # Hard code the discovery service filter
        query += "Filter: check_command = check-mk-inventory\n"
        return query

    def query(self, view, columns, headers, only_sites, limit, all_active_filters):

        if "long_plugin_output" not in columns:
            columns.append("long_plugin_output")

        columns = [c for c in columns if c not in view.datasource.add_columns]
        query = self.prepare_lql(columns, headers)
        data = query_livestatus(query, only_sites, limit, "read")

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
                if state not in ["ignored", "vanished", "unmonitored"]:
                    continue

                this_row = row.copy()
                this_row.update({
                    "discovery_state": state,
                    "discovery_check": check,
                    "discovery_service": service_description
                })
                rows.append(this_row)

        return rows
