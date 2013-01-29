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

import time

def paint_state_statehistory(row):
    if row["statehist_state"] == -1:
        return "state svcstate statep", "UNMON"
    is_host = row["service_description"] == "" 

    state = row["statehist_state"]
    if is_host:
        if state in nagios_short_host_state_names:
            name = nagios_short_state_names[row["statehist_state"]]
            return "state hstate hstate%s" % state, name
    else:
        if state in nagios_short_state_names:
            name = nagios_short_state_names[row["statehist_state"]]
            return "state svcstate state%s" % state, name
    return "state svcstate statep", "PEND"

def paint_state_duration(duration):
    days    = int(duration / 86400)
    days_text = days > 0 and "%s days " % days or ""
    
    hours   = int(duration % 86400 / 3600)
    hours_text = ((days > 0 or hours > 0) and "%s hrs " % hours) or ""
   
    minutes = int(duration % 86400 % 3600 / 60)
    minutes_text = ((days > 0 or hours > 0 or minutes > 0) and "%s min " % minutes) or ""

    seconds = int(duration % 86400 % 3600 % 60)
    seconds_text = (days > 0 or hours > 0 or minutes > 0) and " " or "%s sec" % seconds
    
    return "number", "%s%s%s%s" % (days_text, hours_text, minutes_text, seconds_text)  

def paint_float_to_percent(value):
    return "number", "%.2f %%" %  (100 * float(value)),

# From / Until 
multisite_painters["statehist_from"] = {
    "title"   : _("State history: interval start"),
    "short"   : _("From"),
    "columns" : [ "statehist_from", "statehist_time" ],  
    "options" : [ "ts_format", "ts_date" ],
    "paint"   : lambda row: paint_age(row["statehist_from"], row["statehist_time"], 0),
}

multisite_painters["statehist_until"] = { 
    "title"   : _("State history: interval end"),
    "short"   : _("Until"),
    "columns" : ["statehist_until", "statehist_time"],
    "options" : ["ts_format", "ts_date"],
    "paint"   : lambda row: paint_age(row["statehist_until"], row["statehist_time"], 0),
}

# check_output
multisite_painters["statehist_check_output"] = {
    "title"   : _("State history: log output"),
    "short"   : _("Log output"),
    "columns" : [ "statehist_log_output" ],
    "paint"   : lambda row: ("", row["log_output"]),
}

multisite_painters["statehist_trigger"] = {
    "title"   : _("State history: debug information (triggered by)"),
    "short"   : _("Trigger"),
    "columns" : [ "statehist_debug_info" ],
    "paint"   : lambda row: ("", row["statehist_debug_info"]),
}

# states
multisite_painters["statehist_state"] = { 
    "title"   : _("State history: state"),
    "short"   : _("State"),
    "columns" : [ "statehist_state" ],
    "paint"   : paint_state_statehistory
}

multisite_painters["statehist_in_downtime"] = {
    "title"   : _("State history: host or service in downtime"),
    "short"   : _("Downtime"),
    "columns" : [ "statehist_in_downtime" ],
    "paint"   : lambda row: ("", row["statehist_in_downtime"]),
}

multisite_painters["statehist_in_host_downtime"] = {
    "title"   : _("State history: host in downtime"),
    "short"   : _("Host downtime"),
    "columns" : [ "statehist_in_host_downtime" ],
    "paint"   : lambda row: ("", row["statehist_in_host_downtime"]), 
}

multisite_painters["statehist_host_down"] = {
    "title"   : _("State history: host down"),
    "short"   : _("Host down"),
    "columns" : [ "statehist_host_down" ],
    "paint"   : lambda row: ("", row["statehist_host_down"]), 
}

multisite_painters["statehist_is_flapping"] = {
    "title"   : _("State history: host or service flapping"),
    "short"   : _("Flapping"),
    "columns" : [ "statehist_is_flapping" ],
    "paint"   : lambda row: ("", row["statehist_is_flapping"]),
}

multisite_painters["statehist_in_notification_period"] = {
    "title"   : _("State history: host or service in notification period"),
    "short"   : _("In notification"),
    "columns" : [ "statehist_in_notification_period" ],
    "paint"   : lambda row: ("", row["statehist_in_notification_period"]),
}

multisite_painter_options["statehist_duration_format"] = {
 "title"   : _("State duration format"),
 "default" : "percent",
 "values"  : [
     ("percent",   _("Percent of query interval")),
     ("seconds",   _("Seconds")),
     ("timestamp", _("Timestamp")),
  ]
}

def paint_statehist_duration(in_seconds, in_part):
    mode = get_painter_option("statehist_duration_format")
    if mode == "seconds":
        return "number", in_seconds
    if mode == "timestamp":
        return paint_state_duration(in_seconds)
    if mode == "percent": 
        return paint_float_to_percent(in_part)


# duration
multisite_painters["statehist_duration"] = {
    "title"   : _("State history: state duration"),
    "short"   : _("Duration"),
    "columns" : [ "statehist_duration", "statehist_duration_part" ],
    "options" : [ "statehist_duration_format" ],
    "paint"   : lambda row: paint_statehist_duration(row["statehist_duration"], row["statehist_duration_part"])
}

#multisite_painters["statehist_duration_ok"] = {
#    "title"   : _("State history: state duration OK"),
#    "short"   : _("Duration OK"),
#    "columns" : ["statehist_duration_ok", "statehist_duration_part_ok"],
#    "options" : ["statehist_duration_format"],
#    "paint"   : lambda row: paint_statehist_duration(row["statehist_duration_ok"], row["statehist_duration_part_ok"])
#}
#multisite_painters["statehist_duration_warning"] = {
#    "title"   : _("State history: state duration WARNING"),
#    "short"   : _("Duration WARN"),
#    "columns" : ["statehist_duration_warning", "statehist_duration_part_warning"],
#    "options" : ["statehist_duration_format"],
#    "paint"   : lambda row: paint_statehist_duration(row["statehist_duration_warning"], row["statehist_duration_part_warning"])
#}
#multisite_painters["statehist_duration_critical"] = {
#    "title"   : _("State history: state duration CRITICAL"),
#    "short"   : _("Duration CRIT"),
#    "columns" : ["statehist_duration_critical", "statehist_duration_part_critical"],
#    "options" : ["statehist_duration_format"],
#    "paint"   : lambda row: paint_statehist_duration(row["statehist_duration_critical"], row["statehist_duration_part_critical"])
#}
#multisite_painters["statehist_duration_unknown"] = {
#    "title"   : _("State history: state duration UNKNOWN"),
#    "short"   : _("Duration UNKNOWN"),
#    "columns" : ["statehist_duration_unknown", "statehist_duration_part_unknown"],
#    "options" : ["statehist_duration_format"],
#    "paint"   : lambda row: paint_statehist_duration(row["statehist_duration_unknown"], row["statehist_duration_part_unknown"])
#}
#multisite_painters["statehist_duration_unmonitored"] = {
#    "title"   : _("State history: state duration UNMONITORED"),
#    "short"   : _("Duration UNMONITORED"),
#    "columns" : ["statehist_duration_unmonitored", "statehist_duration_part_unmonitored"],
#    "options" : ["statehist_duration_format"],
#    "paint"   : lambda row: paint_statehist_duration(row["statehist_duration_unmonitored"], row["statehist_duration_part_unmonitored"])
#}

# stats duration ( sum duration )
multisite_painters["statehist_stats_duration_ok"] = {
    "title"   : _("State history: sum of duration OK"),
    "short"   : _("OK"),
    "columns" : ["stats_ok", "stats_part_ok"],
    "options" : ["statehist_duration_format"],
    "paint"   : lambda row: paint_statehist_duration(row["stats_ok"], row["stats_part_ok"])
}

multisite_painters["statehist_stats_duration_warning"] = {
    "title"   : _("State history: sum of duration WARNING"),
    "short"   : _("WARN"),
    "columns" : ["stats_warning", "stats_part_warning"],
    "options" : ["statehist_duration_format"],
    "paint"   : lambda row: paint_statehist_duration(row["stats_warning"], row["stats_part_warning"])
}

multisite_painters["statehist_stats_duration_critical"] = {
    "title"   : _("State history: sum of duration CRITICAL"),
    "short"   : _("CRIT"),
    "columns" : [ "stats_critical", "stats_part_critical"],
    "options" : [ "statehist_duration_format" ],
    "paint"   : lambda row: paint_statehist_duration(row["stats_critical"], row["stats_part_critical"])
}

multisite_painters["statehist_stats_duration_unknown"] = {
    "title"   : _("State history: sum of duration UNKNOWN"),
    "short"   : _("UNKNOWN"),
    "columns" : ["stats_unknown", "stats_part_unknown"],
    "options" : ["statehist_duration_format"],
    "paint"   : lambda row: paint_statehist_duration(row["stats_unknown"], row["stats_part_unknown"])
}

multisite_painters["statehist_stats_duration_unmonitored"] = {
    "title"   : _("State history: sum of duration UNMONITORED"),
    "short"   : _("UNMONITORED"),
    "columns" : ["stats_unmonitored", "stats_part_unmonitored"],
    "options" : ["statehist_duration_format"],
    "paint"   : lambda row: paint_statehist_duration(row["stats_unmonitored"], row["stats_part_unmonitored"])
}

# datasources
multisite_datasources["statehist"] = {
    "title"    : _("State history"),
    "table"    : "statehist",
    "infos"    : [ "statehist", "statehist_time", "host", "service", "log" ],
    "keys"     : [],
    "idkeys"   : [],
    "ignore_limit": True
}

multisite_datasources["statehist_stats"] = {
    "title"    : _("State history statistics"),
    "table"    : "statehist",
    "infos"    : [ "statehist_time", "host", "service", "log" ],
    "add_headers" : "Stats: sum duration_ok\nStats: sum duration_part_ok\n"
                    "Stats: sum duration_warning\nStats: sum duration_part_warning\n"
                    "Stats: sum duration_critical\nStats: sum duration_part_critical\n" 
                    "Stats: sum duration_unknown\nStats: sum duration_part_unknown\n" 
                    "Stats: sum duration_unmonitored\nStats: sum duration_part_unmonitored\n",   
    "add_columns" : [ "stats_ok", "stats_part_ok", "stats_warning", "stats_part_warning", 
                      "stats_critical", "stats_part_critical", "stats_unknown", "stats_part_unknown",
                      "stats_unmonitored", "stats_part_unmonitored"],  
    "keys"     : [],
    "idkeys"   : [],
    "ignore_limit": True
}

# filters
declare_filter(251, FilterTime("statehist_time", "filter_statehist_time", _("Statehistory query interval"), "time")) 

multisite_builtin_views.update({'availability_stats': {'browser_reload': 0,
                        'column_headers': 'off',
                        'datasource': 'statehist_stats',
                        'description': u'',
                        'group_painters': [],
                        'hard_filters': [],
                        'hard_filtervars': [('filter_statehist_time_from',
                                             '24'),
                                            ('filter_statehist_time_from_range',
                                             '3600'),
                                            ('filter_statehist_time_until',
                                             ''),
                                            ('filter_statehist_time_until_range',
                                             '3600'),
                                            ('host', ''),
                                            ('service', '')],
                        'hidden': False,
                        'hide_filters': [],
                        'hidebutton': False,
                        'icon': None,
                        'layout': 'boxed',
                        'linktitle': u'Availabliltiy Statistics',
                        'mobile': False,
                        'mustsearch': True,
                        'name': 'availability_stats',
                        'num_columns': 1,
                        'owner': 'demo123',
                        'painters': [('host', None, ''),
                                     ('service_description', None, ''),
                                     ('statehist_stats_duration_ok',
                                      None,
                                      ''),
                                     ('statehist_stats_duration_warning',
                                      None,
                                      ''),
                                     ('statehist_stats_duration_critical',
                                      None,
                                      ''),
                                     ('statehist_stats_duration_unmonitored',
                                      None,
                                      '')],
                        'play_sounds': False,
                        'public': False,
                        'show_checkboxes': None,
                        'show_filters': ['filter_statehist_time',
                                         'hostregex',
                                         'serviceregex'],
                        'sorters': [],
                        'title': u'Availabliltiy Statistics',
                        'topic': u'Other',
                        'user_sortable': 'on'}})
