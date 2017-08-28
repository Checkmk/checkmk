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


##################################################################################
# Data sources
##################################################################################
# title: Used as display-string for the datasource in multisite (e.g. view editor)
#
# table: Might be a string which refers to a livestatus table or a function
#        which is called instead of the livestatus function query_data().
#
# infos: A key to be used to create groups out of single painters and filters.
#        e.g. 'host' groups all painters and filters which begin with "host_".
#        Out of this declaration multisite knows which filters or painters are
#        available for the single datasources.
#
# merge_by:
#  1. Results in fetching these columns from the datasource.
#  2. Rows from different sites are merged together. For example members
#     of hostgroups which exist on different sites are merged together to
#     show the user one big hostgroup.
#
# add_columns: list of columns the datasource is known to add itself
#
# add_headers: additional livestatus headers to add to each call
#
# keys: columns which must be fetched in order to execute commands on
# the items (= in order to identify the items and gather all information
# needed for constructing Nagios commands)
# those columns are always fetched from the datasource for each item
#
# idkeys: these are used to generate a key which is unique for each data row
# is used to identify an item between http requests
#
# join: A view can display e.g. host-rows and include information from e.g.
#       the service table to create a column which shows e.g. the state of one
#       service.
#       With this attibute it is configured which tables can be joined into
#       this table and by which attribute. It must be given as tuple, while
#       the first argument is the name of the table to be joined and the second
#       argument is the column in the master table (in this case hosts) which
#       is used to match the rows of the master and slave table.
#
# joinkey: Each joined column in the view can have a 4th attribute which is
#          used as value for this column to filter the datasource query
#          to get the matching row of the slave table.
#
# ignore_limit: Ignore the soft/hard query limits in view.py/query_data(). This
#               fixes stats queries on e.g. the log table.
#
# auth_domain: Querying a table might require to use another auth domain than
#              the default one (read). When this is set, the given auth domain
#              will be used while fetching the data for this datasource from
#              livestatus.
#

multisite_datasources["hosts"] = {
    "title"   : _("All hosts"),
    "table"   : "hosts",
    "infos"   : [ "host" ],
    "keys"    : [ "host_name", "host_downtimes" ],
    "join"    : ( "services", "host_name" ),
    "idkeys"  : [ "site", "host_name" ],
    "description"  : _("Displays a list of hosts."),
    # When the single info "hostgroup" is used, use the "opthostgroup" filter
    # to handle the data provided by the single_spec value of the "hostgroup"
    # info, which is in fact the name of the wanted hostgroup
    "link_filters" : { "hostgroup": "opthostgroup" },
    # When these filters are set, the site hint will not be added to urls
    # which link to views using this datasource, because the resuling view
    # should show the objects spread accross the sites
    "multiple_site_filters" : [
        "hostgroup",
        "servicegroup",
    ],
}

multisite_datasources["hostsbygroup"] = {
    "title"   : _("Hosts grouped by host groups"),
    "table"   : "hostsbygroup",
    "infos"   : [ "host", "hostgroup" ],
    "keys"    : [ "host_name", "host_downtimes" ],
    "join"    : ( "services", "host_name" ),
    "idkeys"  : [ "site", "hostgroup_name", "host_name" ],
    "description" : _("This datasource has a separate row for each group membership that a host has."),
}

multisite_datasources["services"] = {
    "title"   : _("All services"),
    "table"   : "services",
    "infos"   : [ "service", "host" ],
    "keys"    : [ "host_name", "service_description", "service_downtimes" ],
    "joinkey" : "service_description",
    "idkeys"  : [ "site", "host_name", "service_description" ],
    # When the single info "hostgroup" is used, use the "opthostgroup" filter
    # to handle the data provided by the single_spec value of the "hostgroup"
    # info, which is in fact the name of the wanted hostgroup
    "link_filters" : {
        "hostgroup"    : "opthostgroup",
        "servicegroup" : "optservicegroup",
    },
    # When these filters are set, the site hint will not be added to urls
    # which link to views using this datasource, because the resuling view
    # should show the objects spread accross the sites
    "multiple_site_filters" : [
        "hostgroup",
        "servicegroup",
    ],
}

multisite_datasources["servicesbygroup"] = {
    "title"   : _("Services grouped by service groups"),
    "table"   : "servicesbygroup",
    "infos"   : [ "service", "host", "servicegroup" ],
    "keys"    : [ "host_name", "service_description", "service_downtimes" ],
    "idkeys"  : [ "site", "servicegroup_name", "host_name", "service_description" ],
}

multisite_datasources["servicesbyhostgroup"] = {
    "title"   : _("Services grouped by host groups"),
    "table"   : "servicesbyhostgroup",
    "infos"   : [ "service", "host", "hostgroup" ],
    "keys"    : [ "host_name", "service_description", "service_downtimes" ],
    "idkeys"  : [ "site", "hostgroup_name", "host_name", "service_description" ],
}

multisite_datasources["hostgroups"] = {
    "title"   : _("Hostgroups"),
    "table"   : "hostgroups",
    "infos"   : [ "hostgroup" ],
    "keys"    : [ "hostgroup_name" ],
    "idkeys"  : [ "site", "hostgroup_name" ],
}

# Merged groups across sites
multisite_datasources["merged_hostgroups"] = {
    "title"    : _("Hostgroups, merged"),
    "table"    : "hostgroups",
    "merge_by" : "hostgroup_name",
    "infos"    : [ "hostgroup" ],
    "keys"     : [ "hostgroup_name" ],
    "idkeys"   : [ "hostgroup_name" ],
}

multisite_datasources["servicegroups"] = {
    "title"    : _("Servicegroups"),
    "table"    : "servicegroups",
    "infos"    : [ "servicegroup" ],
    "keys"     : [ "servicegroup_name" ],
    "idkeys"   : [ "site", "servicegroup_name" ],
}

# Merged groups across sites
multisite_datasources["merged_servicegroups"] = {
    "title"    : _("Servicegroups, merged"),
    "table"    : "servicegroups",
    "merge_by" : "servicegroup_name",
    "infos"    : [ "servicegroup" ],
    "keys"     : [ "servicegroup_name" ],
    "idkeys"   : [ "servicegroup_name" ],
}

multisite_datasources["comments"] = {
    "title"    : _("Host- and Servicecomments"),
    "table"    : "comments",
    "infos"    : [ "comment", "host", "service" ],
    "keys"     : [ "comment_id", "comment_type", "host_name", "service_description" ],
    "idkeys"   : [ "comment_id" ],
}

multisite_datasources["downtimes"] = {
    "title"    : _("Scheduled Downtimes"),
    "table"    : "downtimes",
    "infos"    : [ "downtime", "host", "service" ],
    "keys"     : [ "downtime_id", "service_description" ],
    "idkeys"   : [ "downtime_id" ],
}

multisite_datasources["log"] = {
    "title"    : _("The Logfile"),
    "table"    : "log",
    "infos"    : [ "log", "host", "service", "contact", "command" ],
    "keys"     : [],
    "idkeys"   : [ "log_lineno" ],
    "time_filters" : [ "logtime" ],
}

multisite_datasources["log_events"] = {
    "title"       : _("Host and Service Events"),
    "table"       : "log",
    "add_headers" : "Filter: class = 1\nFilter: class = 3\nFilter: class = 8\nOr: 3\n",
    "infos"       : [ "log", "host", "service" ],
    "keys"        : [],
    "idkeys"      : [ "log_lineno" ],
    "time_filters" : [ "logtime" ],
}

multisite_datasources["log_host_events"] = {
    "title"       : _("Host Events"),
    "table"       : "log",
    "add_headers" : "Filter: class = 1\nFilter: class = 3\nFilter: class = 8\nOr: 3\nFilter: service_description = \n",
    "infos"       : [ "log", "host" ],
    "keys"        : [],
    "idkeys"      : [ "log_lineno" ],
    "time_filters" : [ "logtime" ],
}

multisite_datasources["alert_stats"] = {
    "title"        : _("Alert Statistics"),
    "table"        : "log",
    "add_headers"  : "Filter: class = 1\nStats: state = 0\nStats: state = 1\nStats: state = 2\nStats: state = 3\nStats: state != 0\n",
    "add_columns"  : [ "log_alerts_ok", "log_alerts_warn", "log_alerts_crit", "log_alerts_unknown", "log_alerts_problem" ],
    "infos"        : [ "log", "host", "service", "contact", "command" ],
    "keys"         : [],
    "idkeys"       : [ 'host_name', 'service_description' ],
    "ignore_limit" : True,
    "time_filters" : [ "logtime" ],
}

# The livestatus query constructed by the filters of the view may
# contain filters that are related to the discovery info and should only be
# handled here. We need to extract them from the query, hand over the regular
# filters to the host livestatus query and apply the others during the discovery
# service query.
def query_service_discovery(columns, query, only_sites, limit, all_active_filters):
    # Hard code the discovery service filter
    query += "Filter: check_command = check-mk-inventory\n"

    if "long_plugin_output" not in columns:
        columns.append("long_plugin_output")

    service_rows = do_query_data("GET services\n", columns, [], [], query, only_sites, limit, "read")

    rows = []
    for row in service_rows:
        for service_line in row["long_plugin_output"].split("\n"):
            if not service_line:
                continue

            parts = map(lambda s: s.strip(), service_line.split(":", 2))
            if len(parts) != 3:
                continue

            state, check, service_description = parts
            if state not in ["ignored", "vanished", "unmonitored"]:
                continue

            this_row = row.copy()
            this_row.update({
                "discovery_state"   : state,
                "discovery_check"   : check,
                "discovery_service" : service_description
            })
            rows.append(this_row)

    return rows


multisite_datasources["service_discovery"] = {
    "title"       : _("Service discovery"),
    "table"       : query_service_discovery,
    "add_columns" : [ "discovery_state", "discovery_check", "discovery_service" ],
    "infos"       : [ "host", "discovery" ],
    "keys"        : [],
    "idkeys"      : [ "host_name" ]
}
