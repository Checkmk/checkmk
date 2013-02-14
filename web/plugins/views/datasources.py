#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2013             mk@mathias-kettner.de |
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
# ails.  You should have  received  a copy of the  GNU  General Public
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
# idkeys: these are used to generate a key which is uniq for each data row
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

multisite_datasources["hosts"] = {
    "title"   : _("All hosts"),
    "table"   : "hosts",
    "infos"   : [ "host" ],
    "keys"    : [ "host_name", "host_downtimes" ],
    "join"    : ( "services", "host_name" ),
    "idkeys"  : [ "site", "host_name" ],
}

multisite_datasources["hostsbygroup"] = {
    "title"   : _("Hosts grouped by host groups"),
    "table"   : "hostsbygroup",
    "infos"   : [ "host", "hostgroup" ],
    "keys"    : [ "host_name", "host_downtimes" ],
    "join"    : ( "services", "host_name" ),
    "idkeys"  : [ "site", "hostgroup_name", "host_name" ],
}

multisite_datasources["services"] = {
    "title"   : _("All services"),
    "table"   : "services",
    "infos"   : [ "service", "host" ],
    "keys"    : [ "host_name", "service_description", "service_downtimes" ],
    "joinkey" : "service_description",
    "idkeys"  : [ "site", "host_name", "service_description" ],
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
    "keys"     : [ "comment_id", "comment_type" ],
    "idkeys"   : [ "comment_id" ],
}

multisite_datasources["downtimes"] = {
    "title"    : _("Schedules Downtimes"),
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
}

multisite_datasources["log_events"] = {
    "title"       : _("Host and Service Events"),
    "table"       : "log",
    "add_headers" : "Filter: class = 1\nFilter: class = 3\nOr: 2\n",
    "infos"       : [ "log", "host", "service" ],
    "keys"        : [],
    "idkeys"      : [ "log_lineno" ],
}

multisite_datasources["log_host_events"] = {
    "title"       : _("Host Events"),
    "table"       : "log",
    "add_headers" : "Filter: class = 1\nFilter: class = 3\nOr: 2\nFilter: service_description = \n",
    "infos"       : [ "log", "host" ],
    "keys"        : [],
    "idkeys"      : [ "log_lineno" ],
}

multisite_datasources["alert_stats"] = {
    "title"        : _("Alert Statistics"),
    "table"        : "log",
    "add_headers"  : "Filter: class = 1\nStats: state = 0\nStats: state = 1\nStats: state = 2\nStats: state = 3\nStats: state != 0\n",
    "add_columns"  : [ "alerts_ok", "alerts_warn", "alerts_crit", "alerts_unknown", "alerts_problem" ],
    "infos"        : [ "log", "host", "service", "contact", "command" ],
    "keys"         : [],
    "idkeys"       : [ 'host_name', 'service_description' ],
    "ignore_limit" : True,
}
