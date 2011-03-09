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


# =================================================================== #
#        _    ____ ___      ____                                      #
#       / \  |  _ \_ _|    |  _ \  ___   ___ _   _                    #
#      / _ \ | |_) | |_____| | | |/ _ \ / __| | | |                   #
#     / ___ \|  __/| |_____| |_| | (_) | (__| |_| |                   #
#    /_/   \_\_|  |___|    |____/ \___/ \___|\__,_|                   #
#                                                                     #
# =================================================================== #
#
# A sorter is used for allowing the user to sort the queried data
# according to a certain logic. All sorters declare in plugins/views/*.py
# are available for the user.
#
# Each sorter is a dictionary with the following keys:
#
# "title":    Name of the sorter to be displayed in view editor
# "columns":  Livestatus-columns needed be the sort algorithm
# "cmp":      Comparison function
#
# The function cmp does the actual sorting. During sorting it
# will be called with two data rows as arguments and must
# return -1, 0 or 1:
#
# -1: The first row is smaller than the second (should be output first)
#  0: Both rows are equivalent
#  1: The first row is greater than the second.
#
# The rows are dictionaries from column names to values. Each row
# represents one item in the Livestatus table, for example one host,
# one service, etc.
# =================================================================== #

# Helper functions
# return -1, if r1 < r2, 0 if they are equal, 1 otherwise
def cmp_atoms(s1, s2):
    if s1 < s2:
        return -1
    elif s1 == s2:
        return 0
    else:
        return 1

def cmp_state_equiv(r):
    if r["service_has_been_checked"] == 0:
        return -1
    s = r["service_state"]
    if s <= 1:
        return s
    else:
        return 5 - s # swap crit and unknown

def cmp_host_state_equiv(r):
    if r["host_has_been_checked"] == 0:
        return -1
    s = r["host_state"]
    if s == 0:
        return 0
    else:
        return 2 - s # swap down und unreachable

def cmp_svc_states(r1, r2):
    return cmp_atoms(cmp_state_equiv(r1), cmp_state_equiv(r2))

def cmp_hst_states(r1, r2):
    return cmp_atoms(cmp_host_state_equiv(r1), cmp_host_state_equiv(r2))

def cmp_simple_string(column, r1, r2):
    v1, v2 = r1[column], r2[column]
    c = cmp_atoms(v1.lower(), v2.lower())
    # force a strict order in case of equal spelling but different
    # case!
    if c == 0:
        return cmp_atoms(v1, v2)
    else:
        return c

def cmp_simple_number(column, r1, r2):
    return cmp_atoms(r1[column], r2[column])

multisite_sorters["svcstate"] = {
    "title"   : "Service state",
    "columns" : ["service_state", "service_has_been_checked"],
    "cmp"     : cmp_svc_states
}

multisite_sorters["hoststate"] = {
    "title"   : "Host state",
    "columns" : ["host_state", "host_has_been_checked"],
    "cmp"     : cmp_hst_states
}

def cmp_site_host(r1, r2):
    c = cmp_atoms(r1["site"], r2["site"])
    if c != 0:
        return c
    else:
        return cmp_simple_string("host_name", r1, r2)

multisite_sorters["site_host"] = {
    "title"   : "Host",
    "columns" : ["site", "host_name" ],
    "cmp"     : cmp_site_host
}

def declare_simple_sorter(name, title, column, func):
    multisite_sorters[name] = {
        "title"   : title,
        "columns" : [ column ],
        "cmp"     : lambda r1, r2: func(column, r1, r2)
    }

#                      name           title                    column                       sortfunction
declare_simple_sorter("svcdescr",     "Service description",   "service_description",       cmp_simple_string)
declare_simple_sorter("svcoutput",    "Service plugin output", "service_plugin_output",     cmp_simple_string)
declare_simple_sorter("site",         "Site",                  "site",                      cmp_simple_string)
declare_simple_sorter("stateage",     "Service state age",     "service_last_state_change", cmp_simple_number)
declare_simple_sorter("servicegroup", "Servicegroup",          "servicegroup_alias",        cmp_simple_string)
declare_simple_sorter("hostgroup",    "Hostgroup",             "hostgroup_alias",           cmp_simple_string)

# Comments
declare_simple_sorter("comment_author", "Comment author",      "comment_author",            cmp_simple_string)
declare_simple_sorter("comment_type",   "Comment type",        "comment_type",              cmp_simple_number)

# Downtimes
declare_simple_sorter("downtime_what",   "Downtime type (host/service)",  "is_service",   cmp_simple_number)
declare_simple_sorter("downtime_start_time",   "Downtime start",    "downtime_start_time",            cmp_simple_number)
declare_simple_sorter("downtime_end_time",     "Downtime end",       "downtime_end_time",             cmp_simple_number)
declare_simple_sorter("downtime_entry_time", "Downtime entry time",  "downtime_entry_time", cmp_simple_number)

# Alert statistics
declare_simple_sorter("alerts_ok",       "Number of recoveries",      "alerts_ok",      cmp_simple_number)
declare_simple_sorter("alerts_warn",     "Number of warnings",        "alerts_warn",    cmp_simple_number)
declare_simple_sorter("alerts_crit",     "Number of critical alerts", "alerts_crit",    cmp_simple_number)
declare_simple_sorter("alerts_unknown",  "Number of unknown alerts",  "alerts_unknown", cmp_simple_number)
declare_simple_sorter("alerts_problem",  "Number of problem alerts",  "alerts_problem", cmp_simple_number)

# Aggregations
declare_simple_sorter("aggr_name",   "Aggregation name",  "aggr_name",       cmp_simple_string)
