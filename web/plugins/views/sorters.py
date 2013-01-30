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
    return cmp(cmp_state_equiv(r1), cmp_state_equiv(r2))

def cmp_hst_states(r1, r2):
    return cmp(cmp_host_state_equiv(r1), cmp_host_state_equiv(r2))


multisite_sorters["svcstate"] = {
    "title"   : _("Service state"),
    "columns" : ["service_state", "service_has_been_checked"],
    "cmp"     : cmp_svc_states
}

multisite_sorters["hoststate"] = {
    "title"   : _("Host state"),
    "columns" : ["host_state", "host_has_been_checked"],
    "cmp"     : cmp_hst_states
}

def cmp_site_host(r1, r2):
    c = cmp(r1["site"], r2["site"])
    if c != 0:
        return c
    else:
        return cmp_simple_string("host_name", r1, r2)

multisite_sorters["site_host"] = {
    "title"   : _("Host"),
    "columns" : ["site", "host_name" ],
    "cmp"     : cmp_site_host
}

def cmp_site_alias(r1, r2):
    return cmp(config.site(r1["site"])["alias"], config.site(r2["site"])["alias"])

multisite_sorters["sitealias"] = {
    "title"   : _("Site Alias"),
    "columns" : ["site" ],
    "cmp"     : cmp_site_alias
}

def cmp_host_tags(r1, r2):
    return cmp(get_host_tags(r1), get_host_tags(r2))

multisite_sorters["host"] = {
    "title"   : _("Host Tags (Check_MK)"),
    "columns" : [ "host_custom_variable_names", "host_custom_variable_values" ],
    "cmp"     : cmp_host_tags,
}

#                      name           title                    column                       sortfunction
declare_simple_sorter("svcdescr",                _("Service description"),         "service_description",        cmp_simple_string)
declare_simple_sorter("svcoutput",               _("Service plugin output"),       "service_plugin_output",      cmp_simple_string)
declare_simple_sorter("svc_long_plugin_output",  _("Long output of check plugin"), "service_long_plugin_output", cmp_simple_string)
declare_simple_sorter("site",                    _("Site"),                        "site",                       cmp_simple_string)
declare_simple_sorter("stateage",                _("Service state age"),           "service_last_state_change",  cmp_simple_number)
declare_simple_sorter("servicegroup",            _("Servicegroup"),                "servicegroup_alias",         cmp_simple_string)
declare_simple_sorter("hostgroup",               _("Hostgroup"),                   "hostgroup_alias",            cmp_simple_string)

# Service
declare_1to1_sorter("svc_check_command",          cmp_simple_string)
declare_1to1_sorter("svc_contacts",               cmp_string_list)
declare_1to1_sorter("svc_contact_groups",         cmp_string_list)
declare_1to1_sorter("svc_check_age",              cmp_simple_number, col_num = 1)
declare_1to1_sorter("svc_next_check",             cmp_simple_number, reverse = True)
declare_1to1_sorter("svc_next_notification",      cmp_simple_number, reverse = True)
declare_1to1_sorter("svc_last_notification",      cmp_simple_number)
declare_1to1_sorter("svc_check_latency",          cmp_simple_number)
declare_1to1_sorter("svc_check_duration",         cmp_simple_number)
declare_1to1_sorter("svc_attempt",                cmp_simple_number)
declare_1to1_sorter("svc_check_type",             cmp_simple_number)
declare_1to1_sorter("svc_in_downtime",            cmp_simple_number)
declare_1to1_sorter("svc_in_notifper",            cmp_simple_number)
declare_1to1_sorter("svc_notifper",               cmp_simple_string)
declare_1to1_sorter("svc_flapping",               cmp_simple_number)
declare_1to1_sorter("svc_notifications_enabled",  cmp_simple_number)
declare_1to1_sorter("svc_is_active",              cmp_simple_number)
declare_1to1_sorter("svc_group_memberlist",       cmp_string_list)
declare_1to1_sorter("svc_acknowledged",           cmp_simple_number)

def cmp_perfdata_nth_value(r1, r2, n):
    return cmp(savefloat(get_perfdata_nth_value(r1, n)), savefloat(get_perfdata_nth_value(r2, n)))

multisite_sorters['svc_perf_val01'] = {
    "title"   : _("Service performance data - value number %02d" % 1),
    "columns" : [ 'service_perf_data' ],
    "cmp"     : lambda r1, r2: cmp_perfdata_nth_value(r1, r2, 0),
}
multisite_sorters['svc_perf_val02'] = {
    "title"   : _("Service performance data - value number %02d" % 2),
    "columns" : [ 'service_perf_data' ],
    "cmp"     : lambda r1, r2: cmp_perfdata_nth_value(r1, r2, 1),
}
multisite_sorters['svc_perf_val03'] = {
    "title"   : _("Service performance data - value number %02d" % 3),
    "columns" : [ 'service_perf_data' ],
    "cmp"     : lambda r1, r2: cmp_perfdata_nth_value(r1, r2, 2),
}
multisite_sorters['svc_perf_val04'] = {
    "title"   : _("Service performance data - value number %02d" % 4),
    "columns" : [ 'service_perf_data' ],
    "cmp"     : lambda r1, r2: cmp_perfdata_nth_value(r1, r2, 3),
}
multisite_sorters['svc_perf_val05'] = {
    "title"   : _("Service performance data - value number %02d" % 5),
    "columns" : [ 'service_perf_data' ],
    "cmp"     : lambda r1, r2: cmp_perfdata_nth_value(r1, r2, 4),
}
multisite_sorters['svc_perf_val06'] = {
    "title"   : _("Service performance data - value number %02d" % 6),
    "columns" : [ 'service_perf_data' ],
    "cmp"     : lambda r1, r2: cmp_perfdata_nth_value(r1, r2, 5),
}
multisite_sorters['svc_perf_val07'] = {
    "title"   : _("Service performance data - value number %02d" % 7),
    "columns" : [ 'service_perf_data' ],
    "cmp"     : lambda r1, r2: cmp_perfdata_nth_value(r1, r2, 6),
}
multisite_sorters['svc_perf_val08'] = {
    "title"   : _("Service performance data - value number %02d" % 8),
    "columns" : [ 'service_perf_data' ],
    "cmp"     : lambda r1, r2: cmp_perfdata_nth_value(r1, r2, 7),
}
multisite_sorters['svc_perf_val09'] = {
    "title"   : _("Service performance data - value number %02d" % 9),
    "columns" : [ 'service_perf_data' ],
    "cmp"     : lambda r1, r2: cmp_perfdata_nth_value(r1, r2, 8),
}
multisite_sorters['svc_perf_val10'] = {
    "title"   : _("Service performance data - value number %02d" % 10),
    "columns" : [ 'service_perf_data' ],
    "cmp"     : lambda r1, r2: cmp_perfdata_nth_value(r1, r2, 9),
}


# Host
declare_1to1_sorter("alias",                  cmp_simple_string)
declare_1to1_sorter("host_address",           cmp_simple_string)
declare_1to1_sorter("host_plugin_output",     cmp_simple_string)
declare_1to1_sorter("host_perf_data",         cmp_simple_string)
declare_1to1_sorter("host_check_command",     cmp_simple_string)
declare_1to1_sorter("host_state_age",         cmp_simple_number, col_num = 1)
declare_1to1_sorter("host_check_age",         cmp_simple_number, col_num = 1)
declare_1to1_sorter("host_next_check",        cmp_simple_number, reverse = True)
declare_1to1_sorter("host_next_notification", cmp_simple_number, reverse = True)
declare_1to1_sorter("host_last_notification", cmp_simple_number)
declare_1to1_sorter("host_check_latency",     cmp_simple_number)
declare_1to1_sorter("host_check_duration",    cmp_simple_number)
declare_1to1_sorter("host_attempt",           cmp_simple_number)
declare_1to1_sorter("host_check_type",        cmp_simple_number)
declare_1to1_sorter("host_in_notifper",       cmp_simple_number)
declare_1to1_sorter("host_notifper",          cmp_simple_string)
declare_1to1_sorter("host_flapping",          cmp_simple_number)
declare_1to1_sorter("host_is_active",         cmp_simple_number)
declare_1to1_sorter("host_in_downtime",       cmp_simple_number)
declare_1to1_sorter("host_acknowledged",      cmp_simple_number)
declare_1to1_sorter("num_services",           cmp_simple_number)
declare_1to1_sorter("num_services_ok",        cmp_simple_number)
declare_1to1_sorter("num_services_warn",      cmp_simple_number)
declare_1to1_sorter("num_services_crit",      cmp_simple_number)
declare_1to1_sorter("num_services_unknown",   cmp_simple_number)
declare_1to1_sorter("num_services_pending",   cmp_simple_number)
declare_1to1_sorter("host_parents",           cmp_string_list)
declare_1to1_sorter("host_childs",            cmp_string_list)
declare_1to1_sorter("host_group_memberlist",  cmp_string_list)
declare_1to1_sorter("host_contacts",          cmp_string_list)
declare_1to1_sorter("host_contact_groups",    cmp_string_list)

def cmp_host_problems(r1, r2):
    return cmp(r1["host_num_services"] - r1["host_num_services_ok"] - r1["host_num_services_pending"],
               r2["host_num_services"] - r2["host_num_services_ok"] - r2["host_num_services_pending"])

multisite_sorters["num_problems"] = {
    "title"   : _("Number of problems"),
    "columns" : [ "host_num_services", "host_num_services_ok", "host_num_services_pending" ],
    "cmp"     : cmp_host_problems,
}

# Hostgroup
declare_1to1_sorter("hg_num_services",         cmp_simple_number)
declare_1to1_sorter("hg_num_services_ok",      cmp_simple_number)
declare_1to1_sorter("hg_num_services_warn",    cmp_simple_number)
declare_1to1_sorter("hg_num_services_crit",    cmp_simple_number)
declare_1to1_sorter("hg_num_services_unknown", cmp_simple_number)
declare_1to1_sorter("hg_num_services_pending", cmp_simple_number)
declare_1to1_sorter("hg_num_hosts_up",         cmp_simple_number)
declare_1to1_sorter("hg_num_hosts_down",       cmp_simple_number)
declare_1to1_sorter("hg_num_hosts_unreach",    cmp_simple_number)
declare_1to1_sorter("hg_num_hosts_pending",    cmp_simple_number)
declare_1to1_sorter("hg_name",                 cmp_simple_string)
declare_1to1_sorter("hg_alias",                cmp_simple_string)

# Servicegroup
declare_1to1_sorter("sg_num_services",         cmp_simple_number)
declare_1to1_sorter("sg_num_services_ok",      cmp_simple_number)
declare_1to1_sorter("sg_num_services_warn",    cmp_simple_number)
declare_1to1_sorter("sg_num_services_crit",    cmp_simple_number)
declare_1to1_sorter("sg_num_services_unknown", cmp_simple_number)
declare_1to1_sorter("sg_num_services_pending", cmp_simple_number)
declare_1to1_sorter("sg_name",                 cmp_simple_string)
declare_1to1_sorter("sg_alias",                cmp_simple_string)

# Comments
declare_1to1_sorter("comment_id",              cmp_simple_number)
declare_1to1_sorter("comment_author",          cmp_simple_string)
declare_1to1_sorter("comment_comment",         cmp_simple_string)
declare_1to1_sorter("comment_time",            cmp_simple_number)
declare_1to1_sorter("comment_expires",         cmp_simple_number, reverse = True)
declare_1to1_sorter("comment_what",            cmp_simple_number)
declare_simple_sorter("comment_type",   _("Comment type"),        "comment_type",              cmp_simple_number)

# Downtimes
declare_1to1_sorter("downtime_id",             cmp_simple_number)
declare_1to1_sorter("downtime_author",         cmp_simple_string)
declare_1to1_sorter("downtime_comment",        cmp_simple_string)
declare_1to1_sorter("downtime_fixed",          cmp_simple_number)
declare_1to1_sorter("downtime_type",           cmp_simple_number)
declare_simple_sorter("downtime_what",         _("Downtime type (host/service)"),  "is_service",            cmp_simple_number)
declare_simple_sorter("downtime_start_time",   _("Downtime start"),                "downtime_start_time",   cmp_simple_number)
declare_simple_sorter("downtime_end_time",     _("Downtime end"),                  "downtime_end_time",     cmp_simple_number)
declare_simple_sorter("downtime_entry_time",   _("Downtime entry time"),           "downtime_entry_time",   cmp_simple_number)

# Log
declare_1to1_sorter("log_plugin_output",       cmp_simple_string)
declare_1to1_sorter("log_attempt",             cmp_simple_string)
declare_1to1_sorter("log_state_type",          cmp_simple_string)
declare_1to1_sorter("log_type",                cmp_simple_string)
declare_1to1_sorter("log_contact_name",        cmp_simple_string)
declare_1to1_sorter("log_time",                cmp_simple_number)
declare_1to1_sorter("log_lineno",              cmp_simple_number)

import time
def get_day_start_timestamp(t):
    st    = time.localtime(int(t))
    start = int(time.mktime(time.struct_time((st[0], st[1], st[2], 0, 0, 0, st[6], st[7], st[8]))))
    end   = start + 86399
    return start, end

def cmp_date(column, r1, r2):
    # need to calculate with the timestamp of the day. Using 00:00:00 at the given day.
    # simply calculating with 86400 does not work because of timezone problems
    r1_date = get_day_start_timestamp(r1[column])
    r2_date = get_day_start_timestamp(r2[column])
    return cmp(r2_date, r1_date)

declare_1to1_sorter("log_date",                cmp_date)

# Alert statistics
declare_simple_sorter("alerts_ok",       _("Number of recoveries"),      "alerts_ok",      cmp_simple_number)
declare_simple_sorter("alerts_warn",     _("Number of warnings"),        "alerts_warn",    cmp_simple_number)
declare_simple_sorter("alerts_crit",     _("Number of critical alerts"), "alerts_crit",    cmp_simple_number)
declare_simple_sorter("alerts_unknown",  _("Number of unknown alerts"),  "alerts_unknown", cmp_simple_number)
declare_simple_sorter("alerts_problem",  _("Number of problem alerts"),  "alerts_problem", cmp_simple_number)

# Aggregations
declare_simple_sorter("aggr_name",   _("Aggregation name"),  "aggr_name",       cmp_simple_string)
declare_simple_sorter("aggr_group",  _("Aggregation group"),  "aggr_group",       cmp_simple_string)
