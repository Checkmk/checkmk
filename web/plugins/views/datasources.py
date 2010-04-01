#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2010             mk@mathias-kettner.de |
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

# keys: columns which must be fetched in order to execute commands on 
# the items (= in order to identify the items and gather all information
# needed for constructing Nagios commands)


multisite_datasources["hosts"] = {
    "title"   : "All hosts",
    "table"   : "hosts",
    "infos"   : [ "host" ],
    "keys"    : [ "host_name" ],
}

multisite_datasources["hostsbygroup"] = {
    "title"   : "Hosts grouped by host groups",
    "table"   : "hostsbygroup",
    "infos"   : [ "host", "hostgroup" ],
    "keys"    : [ "host_name" ],
}

multisite_datasources["services"] = {
    "title"   : "All services",
    "table"   : "services",
    "infos"   : [ "host", "service" ],
    "keys"    : [ "host_name", "service_description" ],
}

multisite_datasources["servicesbygroup"] = {
    "title"   : "Services grouped by service groups",
    "table"   : "servicesbygroup",
    "infos"   : [ "host", "service", "servicegroup" ],
    "keys"    : [ "host_name", "service_description" ],
}

multisite_datasources["servicesbyhostgroup"] = {
    "title"   : "Services grouped by host groups",
    "table"   : "servicesbyhostgroup",
    "infos"   : [ "host", "service", "hostgroup" ],
    "keys"    : [ "host_name", "service_description" ],
}

multisite_datasources["hostgroups"] = {
    "title" : "Hostgroups",
    "table" : "hostgroups",
    "infos" : [ "hostgroup" ],
    "keys"    : [ "hostgroup_name" ],
}

multisite_datasources["merged_hostgroups"] = {
    "title"    : "Hostgroups, merged",
    "table"    : "hostgroups",
    "merge_by" : "hostgroup_name",
    "infos"    : [ "hostgroup" ],
    "keys"    : [ "hostgroup_name" ],
}

multisite_datasources["servicegroups"] = {
    "title"    : "Servicegroups",
    "table"    : "servicegroups",
    "infos"    : [ "servicegroup" ],
    "keys"    : [ "servicegroup_name" ],
}

multisite_datasources["merged_servicegroups"] = {
    "title"    : "Servicegroups, merged",
    "table"    : "servicegroups",
    "merge_by" : "servicegroup_name",
    "infos"    : [ "servicegroup" ],
    "keys"    : [ "servicegroup_name" ],
}

multisite_datasources["comments"] = {
    "title"    : "Host- und Servicecomments",
    "table"    : "comments",
    "infos"    : [ "comment", "host", "service" ],
    "keys"    : [ "comment_id", "comment_type" ],
}

multisite_datasources["downtimes"] = {
    "title"    : "Schedules Downtimes",
    "table"    : "downtimes",
    "infos"    : [ "downtime", "host", "service" ],
    "keys"    : [ "downtime_id", "service_description" ],
}

multisite_datasources["log"] = {
    "title"    : "The Logfile",
    "table"    : "log",
    "infos"    : [ "log", "host", "service", "contact", "command" ],
    "keys"     : [],
}

