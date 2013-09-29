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
# A painter computes from information from a data row HTML output and
# a CSS class for one display column. Please note, that there is no
# 1:1 relation between data columns and display columns. A painter can
# make use of more than one data columns. One example is the current
# service state. It uses the columns "service_state" and "has_been_checked".
#
# A painter is a python dictionary with the following keys:
#
# "title":   Title of the column to be displayed in the view editor
#            *and* in views as column header
# "short":   If the key is defined, it is used as column header in views
#            instead of the the title
# "columns": Livestatus columns this painter need. Multisite retrieves
#            only data columns declared in the painters, so make sure
#            you do not leave out something here.
# "paint":   The actual paint function
#
# The paint function gets one argument: A data row, which is a python
# dictionary representing one data object (host, service, ...). Its
# keys are the column names, its values the actual values from livestatus
# (typed: numbers are float or int, not string)
#
# The paint function must return a pair of two strings: The HTML code
# for painting the column and a CSS class for the TD of the column.
# That class is optional and set to "" in most cases. Currently CSS
# styles are not modular and all defined in check_mk.css. This will
# change in future.
# =================================================================== #

#     ____       _       _                          _   _
#    |  _ \ __ _(_)_ __ | |_ ___ _ __    ___  _ __ | |_(_) ___  _ __  ___
#    | |_) / _` | | '_ \| __/ _ \ '__|  / _ \| '_ \| __| |/ _ \| '_ \/ __|
#    |  __/ (_| | | | | | ||  __/ |    | (_) | |_) | |_| | (_) | | | \__ \
#    |_|   \__,_|_|_| |_|\__\___|_|     \___/| .__/ \__|_|\___/|_| |_|___/
#                                            |_|
#
# Painter options influence how painters render their data. Painter options
# are stored together with "refresh" and "columns" as "View options".

import bi # needed for aggregation icon

multisite_painter_options["pnpview"] = {
 "title"   : _("PNP Timerange"),
 "default" : "1",
 "values"  : [ ("0", _("4 Hours")),  ("1", _("25 Hours")),
               ("2", _("One Week")), ("3", _("One Month")),
               ("4", _("One Year")), ("", _("All")) ]
}

multisite_painter_options["ts_format"] = {
 "title"   : _("Time stamp format"),
 "default" : config.default_ts_format,
 "values"  : [
     ("mixed", _("Mixed")),
     ("abs", _("Absolute")),
     ("rel", _("Relative")),
     ("both", _("Both")),
  ]
}

multisite_painter_options["ts_date"] = {
 "title" : _("Date format"),
 "default" : "%Y-%m-%d",
 "values" : [ ("%Y-%m-%d", "1970-12-18"),
              ("%d.%m.%Y", "18.12.1970"),
              ("%m/%d/%Y", "12/18/1970"),
              ("%d.%m.",   "18.12."),
              ("%m/%d",    "12/18") ]
}

# This helper function returns the value of the given custom var
def paint_custom_host_var(what, row):
    custom_vars = dict(zip(row["host_custom_variable_names"],
                           row["host_custom_variable_values"]))

    if what in custom_vars:
        return what, custom_vars[what]
    return what,  ""


#    ___
#   |_ _|___ ___  _ __  ___
#    | |/ __/ _ \| '_ \/ __|
#    | | (_| (_) | | | \__ \
#   |___\___\___/|_| |_|___/
#

import traceback

multisite_icons = []

load_web_plugins('icons', globals())

# Paint column with various icons. The icons use
# a plugin based mechanism so it is possible to
# register own icon "handlers".
# what: either "host" or "service"
# row: the data row of the host or service
def paint_icons(what, row):
    if not row["host_name"]:
        return "", ""# Host probably does not exist

    custom_vars = dict(zip(row["host_custom_variable_names"],
                           row["host_custom_variable_values"]))

    # Extract host tags
    if "TAGS" in custom_vars:
        tags = custom_vars["TAGS"].split()
    else:
        tags = []

    output = ""
    for icon in multisite_icons:
        try:
            icon_output = icon['paint'](what, row, tags, custom_vars)
            if icon_output is not None:
                output += icon_output
        except Exception, e:
            output += 'Exception in icon plugin!<br />' + traceback.format_exc()

    return "icons", output

def iconpainter_columns(what):
    cols = set(['site',
                'host_name',
                'host_custom_variable_names',
                'host_custom_variable_values' ])

    if what == 'service':
        cols.update([
            'service_description',
            'service_custom_variable_names',
            'service_custom_variable_values',
        ])

    for icon in multisite_icons:
        if 'columns' in icon:
            cols.update([ what + '_' + c for c in icon['columns'] ])
        cols.update([ "host_" + c for c in icon.get("host_columns", [])])
        if what == "service":
            cols.update([ "service_" + c for c in icon.get("service_columns", [])])

    return cols

multisite_painters["service_icons"] = {
    "title":   _("Service icons"),
    "short":   _("Icons"),
    "columns": iconpainter_columns("service"),
    "paint":   lambda row: paint_icons("service", row)
}

multisite_painters["host_icons"] = {
    "title":   _("Host icons"),
    "short":   _("Icons"),
    "columns": iconpainter_columns("host"),
    "paint":   lambda row: paint_icons("host", row)
}

# -----------------------------------------------------------------------

def paint_nagios_link(row):
    # We need to use the Nagios-URL as configured
    # in sites.
    baseurl = config.site(row["site"])["url_prefix"] + "nagios/cgi-bin"
    url = baseurl + "/extinfo.cgi?host=" + htmllib.urlencode(row["host_name"])
    svc = row.get("service_description")
    if svc:
        url += "&type=2&service=" + htmllib.urlencode(svc)
        what = "service"
    else:
        url += "&type=1"
        what = "host"
    return "singleicon", "<a href=\"%s\"><img title=\"%s\" src=\"images/icon_nagios.gif\"></a>" % (url, _('Show this %s in Nagios') % what)

def paint_age(timestamp, has_been_checked, bold_if_younger_than, mode=None):
    if not has_been_checked:
        return "age", "-"

    if mode == None:
        mode = get_painter_option("ts_format")

    if mode == "both":
        css, h1 = paint_age(timestamp, has_been_checked, bold_if_younger_than, "abs")
        css, h2 = paint_age(timestamp, has_been_checked, bold_if_younger_than, "rel")
        return css, "%s - %s" % (h1, h2)

    dateformat = get_painter_option("ts_date")
    age = time.time() - timestamp
    if mode == "abs" or \
        (mode == "mixed" and age >= 48 * 3600 or age < -48 * 3600):
        return "age", time.strftime(dateformat + " %H:%M:%S", time.localtime(timestamp))

    # Time delta less than two days => make relative time
    if age < 0:
        age = -age
        prefix = "in "
    else:
        prefix = ""
    if age < bold_if_younger_than:
        age_class = "age recent"
    else:
        age_class = "age"
    return age_class, prefix + html.age_text(age)


def paint_future_time(timestamp):
    if timestamp <= 0:
        return "", "-"
    else:
        return paint_age(timestamp, True, 0)

def paint_day(timestamp):
    return "", time.strftime("%A, %Y-%m-%d", time.localtime(timestamp))

def paint_site_icon(row):
    if row["site"] and config.use_siteicons:
        return None, "<img class=siteicon src=\"icons/site-%s-24.png\">" % row["site"]
    else:
        return None, ""

multisite_painters["sitename_plain"] = {
    "title"   : _("Site id"),
    "short"   : _("Site"),
    "columns" : ["site"],
    "paint"   : lambda row: (None, row["site"]),
    "sorter"  : 'site',
}

multisite_painters["sitealias"] = {
    "title"   : _("Site alias"),
    "columns" : ["site"],
    "paint"   : lambda row: (None, config.site(row["site"])["alias"]),
}

#    ____                  _
#   / ___|  ___ _ ____   _(_) ___ ___  ___
#   \___ \ / _ \ '__\ \ / / |/ __/ _ \/ __|
#    ___) |  __/ |   \ V /| | (_|  __/\__ \
#   |____/ \___|_|    \_/ |_|\___\___||___/
#

def paint_service_state_short(row ):
    if row["service_has_been_checked"] == 1:
        state = row["service_state"]
        name = nagios_short_state_names[row["service_state"]]
    else:
        state = "p"
        name = "PEND"
    return "state svcstate state%s" % state, name

def paint_host_state_short(row):
# return None, str(row)
    if row["host_has_been_checked"] == 1:
        state = row["host_state"]
        name = nagios_short_host_state_names[row["host_state"]]
    else:
        state = "p"
        name = "PEND"
    return "state hstate hstate%s" % state, name

multisite_painters["service_nagios_link"] = {
    "title"   : _("Icon with link to service in Nagios GUI"),
    "short"   : "",
    "columns" : [ "site", "host_name", "service_description" ],
    "paint"   : paint_nagios_link
}

multisite_painters["service_state"] = {
    "title"   : _("Service state"),
    "short"   : _("State"),
    "columns" : ["service_has_been_checked","service_state"],
    "paint"   : paint_service_state_short,
    "sorter"  : 'svcstate',
}


multisite_painters["site_icon"] = {
    "title"   : _("Icon showing the site"),
    "short"   : "",
    "columns" : ["site"],
    "paint"   : paint_site_icon,
    "sorter"  : 'site',
}


multisite_painters["svc_plugin_output"] = {
    "title"   : _("Output of check plugin"),
    "short"   : _("Status detail"),
    "columns" : ["service_plugin_output"],
    "paint"   : lambda row: ("", format_plugin_output(row["service_plugin_output"], row)),
    "sorter"  : 'svcoutput',
}
multisite_painters["svc_long_plugin_output"] = {
    "title"   : _("Long output of check plugin (multiline)"),
    "short"   : _("Status detail"),
    "columns" : ["service_long_plugin_output"],
    "paint"   : lambda row: (None, row["service_long_plugin_output"].replace('\\n', '<br>')),
}
multisite_painters["svc_perf_data"] = {
    "title" : _("Service performance data"),
    "short" : _("Perfdata"),
    "columns" : ["service_perf_data"],
    "paint" : lambda row: (None, row["service_perf_data"])
}

def get_perfdata_nth_value(row, n, remove_unit = False):
    perfdata = row.get("service_perf_data")
    if not perfdata:
        return ''
    try:
        parts = perfdata.split()
        if len(parts) <= n:
            return "" # too few values in perfdata
        varname, rest = parts[n].split("=")
        number = rest.split(';')[0]
        # Remove unit. Why should we? In case of sorter (numeric)
        if remove_unit:
            while len(number) > 0 and not number[-1].isdigit():
                number = number[:-1]
        return number
    except Exception, e:
        return str(e)

def paint_perfdata_nth_value(row, n):
    return "", get_perfdata_nth_value(row, n)

multisite_painters["svc_perf_val01"] = {
    "title" : _("Service performance data - value number  1"),
    "short" : _("Val. 1"),
    "columns" : ["service_perf_data"],
    "paint" : lambda row: paint_perfdata_nth_value(row, 0)
}

multisite_painters["svc_perf_val02"] = {
    "title" : _("Service performance data - value number  2"),
    "short" : _("Val. 2"),
    "columns" : ["service_perf_data"],
    "paint" : lambda row: paint_perfdata_nth_value(row, 1)
}

multisite_painters["svc_perf_val03"] = {
    "title" : _("Service performance data - value number  3"),
    "short" : _("Val. 3"),
    "columns" : ["service_perf_data"],
    "paint" : lambda row: paint_perfdata_nth_value(row, 2)
}

multisite_painters["svc_perf_val04"] = {
    "title" : _("Service performance data - value number  4"),
    "short" : _("Val. 4"),
    "columns" : ["service_perf_data"],
    "paint" : lambda row: paint_perfdata_nth_value(row, 3)
}

multisite_painters["svc_perf_val05"] = {
    "title" : _("Service performance data - value number  5"),
    "short" : _("Val. 5"),
    "columns" : ["service_perf_data"],
    "paint" : lambda row: paint_perfdata_nth_value(row, 4)
}

multisite_painters["svc_perf_val06"] = {
    "title" : _("Service performance data - value number  6"),
    "short" : _("Val. 6"),
    "columns" : ["service_perf_data"],
    "paint" : lambda row: paint_perfdata_nth_value(row, 5)
}

multisite_painters["svc_perf_val07"] = {
    "title" : _("Service performance data - value number  7"),
    "short" : _("Val. 7"),
    "columns" : ["service_perf_data"],
    "paint" : lambda row: paint_perfdata_nth_value(row, 6)
}

multisite_painters["svc_perf_val08"] = {
    "title" : _("Service performance data - value number  8"),
    "short" : _("Val. 8"),
    "columns" : ["service_perf_data"],
    "paint" : lambda row: paint_perfdata_nth_value(row, 7)
}

multisite_painters["svc_perf_val09"] = {
    "title" : _("Service performance data - value number  9"),
    "short" : _("Val. 9"),
    "columns" : ["service_perf_data"],
    "paint" : lambda row: paint_perfdata_nth_value(row, 8)
}

multisite_painters["svc_perf_val10"] = {
    "title" : _("Service performance data - value number 10"),
    "short" : _("Val. 10"),
    "columns" : ["service_perf_data"],
    "paint" : lambda row: paint_perfdata_nth_value(row, 9)
}

multisite_painters["svc_perf_firstval"] = {
    "title" : _("OBSOLETE - DO NOT USE THIS COLUMN"),
    "short" : _("Value"),
    "columns" : ["service_perf_data"],
    "paint" : lambda row: paint_perfdata_nth_value(row, 0)
}

multisite_painters["svc_check_command"] = {
    "title"   : _("Service check command"),
    "short"   : _("Check command"),
    "columns" : ["service_check_command"],
    "paint"   : lambda row: (None, row["service_check_command"]),
}

multisite_painters["svc_check_command_expanded"] = {
    "title"   : _("Service check command expanded"),
    "short"   : _("Check command expanded"),
    "columns" : ["service_check_command_expanded"],
    "paint"   : lambda row: (None, row["service_check_command_expanded"]),
}

multisite_painters["svc_contacts"] = {
    "title"   : _("Service contacts"),
    "short"   : _("Contacts"),
    "columns" : ["service_contacts"],
    "paint"   : lambda row: (None, ", ".join(row["service_contacts"])),
}

multisite_painters["svc_contact_groups"] = {
    "title"   : _("Service contact groups"),
    "short"   : _("Contact groups"),
    "columns" : ["service_contact_groups"],
    "paint"   : lambda row: (None, ", ".join(row["service_contact_groups"])),
}


multisite_painters["service_description"] = {
    "title"   : _("Service description"),
    "short"   : _("Service"),
    "columns" : ["service_description"],
    "paint"   : lambda row: (None, row["service_description"]),
    "sorter"  : 'svcdescr',
}

multisite_painters["svc_state_age"] = {
    "title"   : _("The age of the current service state"),
    "short"   : _("Age"),
    "columns" : [ "service_has_been_checked", "service_last_state_change" ],
    "options" : [ "ts_format", "ts_date" ],
    "paint"   : lambda row: paint_age(row["service_last_state_change"], row["service_has_been_checked"] == 1, 60 * 10),
    "sorter"  : "stateage",
}
multisite_painters["svc_check_age"] = {
    "title"   : _("The time since the last check of the service"),
    "short"   : _("Checked"),
    "columns" : [ "service_has_been_checked", "service_last_check" ],
    "options" : [ "ts_format", "ts_date" ],
    "paint"   : lambda row: paint_age(row["service_last_check"], row["service_has_been_checked"] == 1, 0),
}

multisite_painters["svc_next_check"] = {
    "title"   : _("The time of the next scheduled service check"),
    "short"   : _("Next check"),
    "columns" : [ "service_next_check" ],
    "paint"   : lambda row: paint_future_time(row["service_next_check"]),
}

multisite_painters["svc_next_notification"] = {
    "title"   : _("The time of the next service notification"),
    "short"   : _("Next notification"),
    "columns" : [ "service_next_notification" ],
    "paint"   : lambda row: paint_future_time(row["service_next_notification"]),
}

multisite_painters["svc_last_notification"] = {
    "title"   : _("The time of the last service notification"),
    "short"   : _("last notification"),
    "columns" : [ "service_last_notification" ],
    "options" : [ "ts_format", "ts_date" ],
    "paint"   : lambda row: paint_age(row["service_last_notification"], row["service_last_notification"], 0),
}

multisite_painters["svc_check_latency"] = {
    "title"   : _("Service check latency"),
    "short"   : _("Latency"),
    "columns" : [ "service_latency" ],
    "paint"   : lambda row: ("", "%.3f sec" % row["service_latency"]),
}

multisite_painters["svc_check_duration"] = {
    "title"   : _("Service check duration"),
    "short"   : _("Duration"),
    "columns" : [ "service_execution_time" ],
    "paint"   : lambda row: ("", "%.3f sec" % row["service_execution_time"]),
}

multisite_painters["svc_attempt"] = {
    "title"   : _("Current check attempt"),
    "short"   : _("Att."),
    "columns" : [ "service_current_attempt", "service_max_check_attempts" ],
    "paint"   : lambda row: (None, "%d/%d" % (row["service_current_attempt"], row["service_max_check_attempts"])),
}

multisite_painters["svc_normal_interval"] = {
    "title"   : _("Service normal check interval"),
    "short"   : _("Check int."),
    "columns" : [ "service_check_interval" ],
    "paint"   : lambda row: (None, "%.0fs" % (row["service_check_interval"] * 60.0)),
}
multisite_painters["svc_retry_interval"] = {
    "title"   : _("Service retry check interval"),
    "short"   : _("Retry"),
    "columns" : [ "service_retry_interval" ],
    "paint"   : lambda row: (None, "%.0fs" % (row["service_retry_interval"] * 60.0)),
}
multisite_painters["svc_check_interval"] = {
    "title"   : _("Service normal/retry check interval"),
    "short"   : _("Interval"),
    "columns" : [ "service_check_interval", "service_retry_interval" ],
    "paint"   : lambda row: (None, "%.0fs/%.0fs" % (
            row["service_check_interval"] * 60.0, row["service_retry_interval"] * 60.0)),
}

multisite_painters["svc_check_type"] = {
    "title"   : _("Service check type"),
    "short"   : _("Type"),
    "columns" : [ "service_check_type" ],
    "paint"   : lambda row: (None, row["service_check_type"] == 0 and "ACTIVE" or "PASSIVE"),
}

def paint_nagiosflag(row, field, bold_if_nonzero):
    value = row[field]
    yesno = {True:"yes", False:"no"}[value != 0]
    if (value != 0) == bold_if_nonzero:
        return "badflag", yesno
    else:
        return "goodflag", yesno

multisite_painters["svc_in_downtime"] = {
    "title"   : _("Currently in downtime"),
    "short"   : _("Dt."),
    "columns" : [ "service_scheduled_downtime_depth" ],
    "paint"   : lambda row: paint_nagiosflag(row, "service_scheduled_downtime_depth", True),
}

multisite_painters["svc_in_notifper"] = {
    "title"   : _("In notification period"),
    "short"   : _("in notif. p."),
    "columns" : [ "service_in_notification_period" ],
    "paint"   : lambda row: paint_nagiosflag(row, "service_in_notification_period", False),
}

multisite_painters["svc_notifper"] = {
    "title"   : _("Service notification period"),
    "short"   : _("notif."),
    "columns" : [ "service_notification_period" ],
    "paint"   : lambda row: (None, row["service_notification_period"]),
}

multisite_painters["svc_flapping"] = {
    "title"   : _("Service is flapping"),
    "short"   : _("Flap"),
    "columns" : [ "service_is_flapping" ],
    "paint"   : lambda row: paint_nagiosflag(row, "service_is_flapping", True),
}

multisite_painters["svc_notifications_enabled"] = {
    "title"   : _("Service notifications enabled"),
    "short"   : _("Notif."),
    "columns" : [ "service_notifications_enabled" ],
    "paint"   : lambda row: paint_nagiosflag(row, "service_notifications_enabled", False),
}

multisite_painters["svc_is_active"] = {
    "title"   : _("Service is active"),
    "short"   : _("Active"),
    "columns" : [ "service_active_checks_enabled" ],
    "paint"   : lambda row: paint_nagiosflag(row, "service_active_checks_enabled", None),
}

def paint_service_group_memberlist(row):
    links = []
    for group in row["service_groups"]:
        link = "view.py?view_name=servicegroup&servicegroup=" + group
        links.append('<a href="%s">%s</a>' % (link, group))
    return "", ", ".join(links)

multisite_painters["svc_group_memberlist"] = {
    "title"   : _("Servicegroups the service is member of"),
    "short"   : _("Groups"),
    "columns" : [ "service_groups" ],
    "paint"   : paint_service_group_memberlist,
}

# PNP Graphs
def paint_pnpgraph(sitename, host, service = "_HOST_"):
    container_id = "%s_%s_%s_graph" % (sitename, host, service)
    pnp_url = html.site_status[sitename]["site"]["url_prefix"] + "pnp4nagios/"
    if 'X' in html.display_options:
        with_link = 'true'
    else:
        with_link = 'false'
    pnpview = get_painter_option("pnpview")
    return "pnpgraph", "<div id=\"%s\"></div>" \
                       "<script>render_pnp_graphs('%s', '%s', '%s', '%s', '%s', '%s', '%s', %s)</script>" % \
                          (container_id, container_id, sitename, host, service, pnpview,
                           defaults.url_prefix + "check_mk/", pnp_url, with_link)

multisite_painters["svc_pnpgraph" ] = {
    "title"   : _("PNP service graph"),
    "short"   : _("PNP graph"),
    "columns" : [ "host_name", "service_description" ],
    "options" : [ "pnpview" ],
    "paint"   : lambda row: paint_pnpgraph(row["site"], row["host_name"], row["service_description"]),
}

def paint_check_manpage(row):
    command = row["service_check_command"]
    if not command.startswith("check_mk-"):
	return "", ""
    checktype = command[9:]
    # Honor man-pages in OMD's local structure
    p = None
    if defaults.omd_root:
        p = defaults.omd_root + "/local/share/check_mk/checkman/" + checktype
        if not os.path.isfile(p):
            p = None
    if not p:
        p = defaults.check_manpages_dir + "/" + checktype
    if os.path.isfile(p):
	description = None
	for line in file(p):
	    line = line.rstrip()
	    if line == "description:":
		description = ""
	    elif line.strip() == "" and description != None:
		description += "<p>"
	    elif not line.startswith(' ') and line[-1] == ':':
		break
	    elif description != None:
	        description += " " + line
	if not description:
	    return "", ""
	else:
	    return "", description.replace("{", "<b>").replace("}", "</b>")
    else:
	return "", _("Man-Page: %s not found.") % p

multisite_painters["check_manpage"] = {
    "title"   : _("Check manual (for Check_MK based checks)"),
    "short"   : _("Manual"),
    "columns" : [ "service_check_command" ],
    "paint"   : paint_check_manpage,
}

def paint_comments(prefix, row):
    comments = row[ prefix + "comments_with_info"]
    text = ", ".join(["<i>%s</i>: %s" % (a, htmllib.attrencode(c)) for (id, a, c) in comments ])
    return "", text

multisite_painters["svc_comments"] = {
    "title"   : _("Service Comments"),
    "short"   : _("Comments"),
    "columns" : [ "service_comments_with_info" ],
    "paint"   : lambda row: paint_comments("service_", row)
}

multisite_painters["svc_acknowledged"] = {
    "title"   : _("Service problem acknowledged"),
    "short"   : _("Ack"),
    "columns" : ["service_acknowledged"],
    "paint"   : lambda row: paint_nagiosflag(row, "service_acknowledged", False),
}

def notes_matching_pattern_entries(dirs, item):
    from fnmatch import fnmatch
    matching = []
    for dir in dirs:
        if os.path.isdir(dir):
            entries = filter(lambda d: d[0] != '.', os.listdir(dir))
            entries.sort()
            entries.reverse()
            for pattern in entries:
                if pattern[0] == '.':
                    continue
                if fnmatch(item, pattern):
                    matching.append(dir + "/" + pattern)
    return matching

def paint_custom_notes(row):
    host = row["host_name"]
    svc = row.get("service_description")
    if svc:
        notes_dir = defaults.default_config_dir + "/notes/services"
        dirs = notes_matching_pattern_entries([notes_dir], host)
        item = svc
    else:
        dirs = [ defaults.default_config_dir + "/notes/hosts" ]
        item = host

    files = notes_matching_pattern_entries(dirs, item)
    files.sort()
    files.reverse()
    contents = []
    def replace_tags(text):
        sitename = row["site"]
        site = html.site_status[sitename]["site"]
        return text\
            .replace('$URL_PREFIX$',     site["url_prefix"])\
            .replace('$SITE$',           sitename)\
            .replace('$HOSTNAME$',       host)\
	    .replace('$HOSTNAME_LOWER$', host.lower())\
            .replace('$HOSTNAME_UPPER$', host.upper())\
            .replace('$HOSTNAME_TITLE$', host[0].upper() + host[1:].lower())\
            .replace('$HOSTADDRESS$',    row["host_address"])\
            .replace('$SERVICEOUTPUT$',  row.get("service_plugin_output", ""))\
            .replace('$HOSTOUTPUT$',     row.get("host_plugin_output", ""))\
            .replace('$SERVICEDESC$',    row.get("service_description", ""))

    for f in files:
        contents.append(replace_tags(unicode(file(f).read(), "utf-8").strip()))
    return "", "<hr>".join(contents)

multisite_painters["svc_custom_notes"] = {
    "title"   : _("Custom services notes"),
    "short"   : _("Notes"),
    "columns" : [ "host_name", "host_address", "service_description", "service_plugin_output" ],
    "paint"   : paint_custom_notes,
}

#   _   _           _
#  | | | | ___  ___| |_ ___
#  | |_| |/ _ \/ __| __/ __|
#  |  _  | (_) \__ \ |_\__ \
#  |_| |_|\___/|___/\__|___/
#

multisite_painters["host_state"] = {
    "title"   : _("Host state"),
    "short"   : _("state"),
    "columns" : ["host_has_been_checked","host_state"],
    "paint"   : paint_host_state_short,
    "sorter"  : 'hoststate',
}

multisite_painters["host_state_onechar"] = {
    "title"   : _("Host state (first character)"),
    "short"   : _("S."),
    "columns" : ["host_has_been_checked","host_state"],
    "paint"   : lambda row: paint_host_state_short(row, True),
    "sorter"  : 'hoststate',
}

multisite_painters["host_plugin_output"] = {
    "title"   : _("Output of host check plugin"),
    "short"   : _("Status detail"),
    "columns" : ["host_plugin_output"],
    "paint"   : lambda row: (None, row["host_plugin_output"]),
}

multisite_painters["host_perf_data"] = {
    "title"   : _("Host performance data"),
    "short"   : _("Performance data"),
    "columns" : ["host_perf_data"],
    "paint"   : lambda row: (None, row["host_perf_data"]),
}

multisite_painters["host_check_command"] = {
    "title"   : _("Host check command"),
    "short"   : _("Check command"),
    "columns" : ["host_check_command"],
    "paint"   : lambda row: (None, row["host_check_command"]),
}

multisite_painters["host_check_command_expanded"] = {
    "title"   : _("Host check command expanded"),
    "short"   : _("Check command expanded"),
    "columns" : ["host_check_command_expanded"],
    "paint"   : lambda row: (None, row["host_check_command_expanded"]),
}

multisite_painters["host_state_age"] = {
    "title"   : _("The age of the current host state"),
    "short"   : _("Age"),
    "columns" : [ "host_has_been_checked", "host_last_state_change" ],
    "options" : [ "ts_format", "ts_date" ],
    "paint"   : lambda row: paint_age(row["host_last_state_change"], row["host_has_been_checked"] == 1, 60 * 10),
}

multisite_painters["host_check_age"] = {
    "title"   : _("The time since the last check of the host"),
    "short"   : _("Checked"),
    "columns" : [ "host_has_been_checked", "host_last_check" ],
    "options" : [ "ts_format", "ts_date" ],
    "paint"   : lambda row: paint_age(row["host_last_check"], row["host_has_been_checked"] == 1, 0),
}

multisite_painters["host_next_check"] = {
    "title"   : _("The time of the next scheduled host check"),
    "short"   : _("Next check"),
    "columns" : [ "host_next_check" ],
    "paint"   : lambda row: paint_future_time(row["host_next_check"]),
}

multisite_painters["host_next_notification"] = {
    "title"   : _("The time of the next host notification"),
    "short"   : _("Next notification"),
    "columns" : [ "host_next_notification" ],
    "paint"   : lambda row: paint_future_time(row["host_next_notification"]),
}

multisite_painters["host_last_notification"] = {
    "title"   : _("The time of the last host notification"),
    "short"   : _("last notification"),
    "columns" : [ "host_last_notification" ],
    "options" : [ "ts_format", "ts_date" ],
    "paint"   : lambda row: paint_age(row["host_last_notification"], row["host_last_notification"], 0),
}

multisite_painters["host_check_latency"] = {
    "title"   : _("Host check latency"),
    "short"   : _("Latency"),
    "columns" : [ "host_latency" ],
    "paint"   : lambda row: ("", "%.3f sec" % row["host_latency"]),
}

multisite_painters["host_check_duration"] = {
    "title"   : _("Host check duration"),
    "short"   : _("Duration"),
    "columns" : [ "host_execution_time" ],
    "paint"   : lambda row: ("", "%.3f sec" % row["host_execution_time"]),
}

multisite_painters["host_attempt"] = {
    "title"   : _("Current host check attempt"),
    "short"   : _("Att."),
    "columns" : [ "host_current_attempt", "host_max_check_attempts" ],
    "paint"   : lambda row: (None, "%d/%d" % (row["host_current_attempt"], row["host_max_check_attempts"])),
}

multisite_painters["host_normal_interval"] = {
    "title"   : _("Normal check interval"),
    "short"   : _("Check int."),
    "columns" : [ "host_check_interval" ],
    "paint"   : lambda row: (None, "%.0fs" % (row["host_check_interval"] * 60.0)),
}
multisite_painters["host_retry_interval"] = {
    "title"   : _("Retry check interval"),
    "short"   : _("Retry"),
    "columns" : [ "host_retry_interval" ],
    "paint"   : lambda row: (None, "%.0fs" % (row["host_retry_interval"] * 60.0)),
}
multisite_painters["host_check_interval"] = {
    "title"   : _("Normal/retry check interval"),
    "short"   : _("Interval"),
    "columns" : [ "host_check_interval", "host_retry_interval" ],
    "paint"   : lambda row: (None, "%.0fs/%.0fs" % (
            row["host_check_interval"] * 60.0, row["host_retry_interval"] * 60.0)),
}

multisite_painters["host_check_type"] = {
    "title"   : _("Host check type"),
    "short"   : _("Type"),
    "columns" : [ "host_check_type" ],
    "paint"   : lambda row: (None, row["host_check_type"] == 0 and "ACTIVE" or "PASSIVE"),
}

multisite_painters["host_in_notifper"] = {
    "title"   : _("Host in notif. period"),
    "short"   : _("in notif. p."),
    "columns" : [ "host_in_notification_period" ],
    "paint"   : lambda row: paint_nagiosflag(row, "host_in_notification_period", False),
}

multisite_painters["host_notifper"] = {
    "title"   : _("Host notification period"),
    "short"   : _("notif."),
    "columns" : [ "host_notification_period" ],
    "paint"   : lambda row: (None, row["host_notification_period"]),
}

multisite_painters["host_flapping"] = {
    "title"   : _("Host is flapping"),
    "short"   : _("Flap"),
    "columns" : [ "host_is_flapping" ],
    "paint"   : lambda row: paint_nagiosflag(row, "host_is_flapping", True),
}

multisite_painters["host_is_active"] = {
    "title"   : _("Host is active"),
    "short"   : _("Active"),
    "columns" : [ "host_active_checks_enabled" ],
    "paint"   : lambda row: paint_nagiosflag(row, "host_active_checks_enabled", None),
}

multisite_painters["host_pnpgraph" ] = {
    "title"   : _("PNP host graph"),
    "short"   : _("PNP graph"),
    "columns" : [ "host_name" ],
    "options" : [ "pnpview" ],
    "paint"   : lambda row: paint_pnpgraph(row["site"], row["host_name"])
}

def paint_host_black(row):
    state = row["host_state"]
    if state != 0:
        return None, "<div class=hostdown>%s</div>" % row["host_name"]
    else:
        return None, row["host_name"]

multisite_painters["host_black"] = {
    "title"   : _("Hostname, red background if down or unreachable"),
    "short"   : _("Host"),
    "columns" : ["site", "host_name", "host_state"],
    "paint"   : paint_host_black,
    "sorter"  : 'site_host',
}

def paint_host_black_with_link_to_old_nagios_services(row):
    host = row["host_name"]
    baseurl = config.site(row["site"])["url_prefix"] + "nagios/cgi-bin"
    url = baseurl + "/status.cgi?host=" + htmllib.urlencode(host)
    state = row["host_state"]
    if state != 0:
        return None, '<div class=hostdown><a href="%s">%s</a></div>' % (url, host)
    else:
        return None, '<a href="%s">%s</a>' % (url, host)


multisite_painters["host_black_nagios"] = {
    "title"   : _("Hostname, red background if down, link to Nagios services"),
    "short"   : _("Host"),
    "columns" : ["site", "host_name", "host_state"],
    "paint"   : paint_host_black_with_link_to_old_nagios_services,
    "sorter"  : 'site_host',
}


multisite_painters["host_nagios_link"] = {
    "title"   : _("Icon with link to host to Nagios GUI"),
    "short"   : "",
    "columns" : [ "site", "host_name" ],
    "paint"   : paint_nagios_link,
}

def paint_host_with_state(row):
    if row["host_has_been_checked"]:
        state = row["host_state"]
    else:
        state = "p"
    if state != 0:
        return "state hstate hstate%s" % state, row["host_name"]
    else:
        return "", row["host_name"]

multisite_painters["host_with_state"] = {
    "title"   : _("Hostname, marked red if down"),
    "short"   : _("Host"),
    "columns" : ["site", "host_name", "host_state", "host_has_been_checked" ],
    "paint"   : paint_host_with_state,
    "sorter"  : 'site_host',
}

multisite_painters["host"] = {
    "title"   : _("Hostname"),
    "short"   : _("Host"),
    "columns" : ["host_name"],
    "paint"   : lambda row: ("", row["host_name"]),
    "sorter"  : 'site_host',
}

multisite_painters["alias"] = {
    "title"   : _("Host alias"),
    "short"   : _("Alias"),
    "columns" : ["host_alias"],
    "paint"   : lambda row: ("", row["host_alias"]),
}

multisite_painters["host_address"] = {
    "title"   : _("Host IP address"),
    "short"   : _("IP address"),
    "columns" : ["host_address"],
    "paint"   : lambda row: ("", row["host_address"]),
}

def paint_svc_count(id, count):
    if count > 0:
        return "count svcstate state%s" % id, str(count)
    else:
        return "count svcstate statex", "0"

def paint_host_count(id, count):
    if count > 0:
        if id != None:
            return "count hstate hstate%s" % id, str(count)
        else: # pending
            return "count hstate hstatep", str(count)

    else:
        return "count hstate hstatex", "0"

multisite_painters["num_services"] = {
    "title"   : _("Number of services"),
    "short"   : "",
    "columns" : [ "host_num_services" ],
    "paint"   : lambda row: (None, str(row["host_num_services"])),
}

multisite_painters["num_services_ok"] = {
    "title"   : _("Number of services in state OK"),
    "short"   : _("OK"),
    "columns" : [ "host_num_services_ok" ],
    "paint"   : lambda row: paint_svc_count(0, row["host_num_services_ok"]),
}

multisite_painters["num_problems"] = {
    "title"   : _("Number of problems"),
    "short"   : _("Pro."),
    "columns" : [ "host_num_services", "host_num_services_ok", "host_num_services_pending" ],
    "paint"   : lambda row: paint_svc_count('s', row["host_num_services"] - row["host_num_services_ok"] - row["host_num_services_pending"]),
}

multisite_painters["num_services_warn"] = {
    "title"   : _("Number of services in state WARN"),
    "short"   : _("Wa"),
    "columns" : [ "host_num_services_warn" ],
    "paint"   : lambda row: paint_svc_count(1, row["host_num_services_warn"]),
}

multisite_painters["num_services_crit"] = {
    "title"   : _("Number of services in state CRIT"),
    "short"   : _("Cr"),
    "columns" : [ "host_num_services_crit" ],
    "paint"   : lambda row: paint_svc_count(2, row["host_num_services_crit"]),
}

multisite_painters["num_services_unknown"] = {
    "title"   : _("Number of services in state UNKNOWN"),
    "short"   : _("Un"),
    "columns" : [ "host_num_services_unknown" ],
    "paint"   : lambda row: paint_svc_count(3, row["host_num_services_unknown"]),
}

multisite_painters["num_services_pending"] = {
    "title"   : _("Number of services in state PENDING"),
    "short"   : _("Pd"),
    "columns" : [ "host_num_services_pending" ],
    "paint"   : lambda row: paint_svc_count("p", row["host_num_services_pending"]),
}

def paint_service_list(row, columnname):
    h = "<div class=objectlist>"
    for entry in row[columnname]:
        if columnname.startswith("servicegroup"):
            host, svc, state, checked = entry
            text = host + " ~ " + svc
        else:
            svc, state, checked = entry
            host = row["host_name"]
            text = svc
        link = "view.py?view_name=service&site=%s&host=%s&service=%s" % (
                htmllib.urlencode(row["site"]),
                htmllib.urlencode(host),
                htmllib.urlencode(svc))
        if checked:
            css = "state%d" % state
        else:
            css = "statep"
        h += "<div class=\"%s\"><a href=\"%s\">%s</a></div>" % (css, link, text)
    h += "</div>"
    return "", h

multisite_painters["host_services"] = {
    "title"   : _("Services colored according to state"),
    "short"   : _("Services"),
    "columns" : [ "host_name", "host_services_with_state" ],
    "paint"   : lambda row: paint_service_list(row, "host_services_with_state"),
}

multisite_painters["host_parents"] = {
    "title"   : _("Host's parents"),
    "short"   : _("Parents"),
    "columns" : [ "host_parents" ],
    "paint"   : lambda row: paint_host_list(row["site"], row["host_parents"]),
}

multisite_painters["host_childs"] = {
    "title"   : _("Host's childs"),
    "short"   : _("childs"),
    "columns" : [ "host_childs" ],
    "paint"   : lambda row: paint_host_list(row["site"], row["host_childs"]),
}

def paint_host_group_memberlist(row):
    links = []
    for group in row["host_groups"]:
        link = "view.py?view_name=hostgroup&hostgroup=" + group
        if html.var("display_options"):
            link += "&display_options=%s" % html.var("display_options")
        links.append('<a href="%s">%s</a>' % (link, group))
    return "", ", ".join(links)

multisite_painters["host_group_memberlist"] = {
    "title"   : _("Hostgroups the host is member of"),
    "short"   : _("Groups"),
    "columns" : [ "host_groups" ],
    "paint"   : paint_host_group_memberlist,
}

multisite_painters["host_contacts"] = {
    "title"   : _("Host contacts"),
    "short"   : _("Contacts"),
    "columns" : ["host_contacts"],
    "paint"   : lambda row: (None, ", ".join(row["host_contacts"])),
}

multisite_painters["host_contact_groups"] = {
    "title"   : _("Host contact groups"),
    "short"   : _("Contact groups"),
    "columns" : ["host_contact_groups"],
    "paint"   : lambda row: (None, ", ".join(row["host_contact_groups"])),
}

multisite_painters["host_custom_notes"] = {
    "title"   : _("Custom host notes"),
    "short"   : _("Notes"),
    "columns" : [ "host_name", "host_address", "host_plugin_output" ],
    "paint"   : paint_custom_notes,
}

def paint_host_tags(row):
    return "", get_host_tags(row)

multisite_painters["host_tags"] = {
    "title"   : _("Host Tags (Check_MK)"),
    "short"   : _("Tags"),
    "columns" : [ "host_custom_variable_names", "host_custom_variable_values" ],
    "paint"   : paint_host_tags,
}

multisite_painters["host_comments"] = {
    "title"   : _("Host Comments"),
    "short"   : _("Comments"),
    "columns" : [ "host_comments_with_info" ],
    "paint"   : lambda row: paint_comments("host_", row),
}

multisite_painters["host_in_downtime"] = {
    "title"   : _("Host in downtime"),
    "short"   : _("Downtime"),
    "columns" : ["host_scheduled_downtime_depth"],
    "paint"   : lambda row: paint_nagiosflag(row, "host_scheduled_downtime_depth", True),
}

multisite_painters["host_acknowledged"] = {
    "title"   : _("Host problem acknowledged"),
    "short"   : _("Ack"),
    "columns" : ["host_acknowledged"],
    "paint"   : lambda row: paint_nagiosflag(row, "host_acknowledged", False),
}


#    _   _           _
#   | | | | ___  ___| |_ __ _ _ __ ___  _   _ _ __  ___
#   | |_| |/ _ \/ __| __/ _` | '__/ _ \| | | | '_ \/ __|
#   |  _  | (_) \__ \ || (_| | | | (_) | |_| | |_) \__ \
#   |_| |_|\___/|___/\__\__, |_|  \___/ \__,_| .__/|___/
#                       |___/                |_|
#
def paint_hg_host_list(row):
    h = "<div class=objectlist>"
    for host, state, checked in row["hostgroup_members_with_state"]:
        link = "view.py?view_name=host&site=%s&host=%s" % (
                htmllib.urlencode(row["site"]),
                htmllib.urlencode(host))
        if checked:
            css = "hstate%d" % state
        else:
            css = "hstatep"
        h += "<div class=\"%s\"><a href=\"%s\">%s</a></div>" % (css, link, host)
    h += "</div>"
    return "", h

multisite_painters["hostgroup_hosts"] = {
    "title"   : _("Hosts colored according to state"),
    "short"   : _("Hosts"),
    "columns" : [ "hostgroup_members_with_state" ],
    "paint"   : paint_hg_host_list,
}

multisite_painters["hg_num_services"] = {
    "title"   : _("Number of services"),
    "short"   : "",
    "columns" : [ "hostgroup_num_services" ],
    "paint"   : lambda row: (None, str(row["hostgroup_num_services"])),
}

multisite_painters["hg_num_services_ok"] = {
    "title"   : _("Number of services in state OK"),
    "short"   : _("O"),
    "columns" : [ "hostgroup_num_services_ok" ],
    "paint"   : lambda row: paint_svc_count(0, row["hostgroup_num_services_ok"]),
}

multisite_painters["hg_num_services_warn"] = {
    "title"   : _("Number of services in state WARN"),
    "short"   : _("W"),
    "columns" : [ "hostgroup_num_services_warn" ],
    "paint"   : lambda row: paint_svc_count(1, row["hostgroup_num_services_warn"]),
}

multisite_painters["hg_num_services_crit"] = {
    "title"   : _("Number of services in state CRIT"),
    "short"   : _("C"),
    "columns" : [ "hostgroup_num_services_crit" ],
    "paint"   : lambda row: paint_svc_count(2, row["hostgroup_num_services_crit"]),
}

multisite_painters["hg_num_services_unknown"] = {
    "title"   : _("Number of services in state UNKNOWN"),
    "short"   : _("U"),
    "columns" : [ "hostgroup_num_services_unknown" ],
    "paint"   : lambda row: paint_svc_count(3, row["hostgroup_num_services_unknown"]),
}

multisite_painters["hg_num_services_pending"] = {
    "title"   : _("Number of services in state PENDING"),
    "short"   : _("P"),
    "columns" : [ "hostgroup_num_services_pending" ],
    "paint"   : lambda row: paint_svc_count("p", row["hostgroup_num_services_pending"]),
}

multisite_painters["hg_num_hosts_up"] = {
    "title"   : _("Number of hosts in state UP"),
    "short"   : _("Up"),
    "columns" : [ "hostgroup_num_hosts_up" ],
    "paint"   : lambda row: paint_host_count(0, row["hostgroup_num_hosts_up"]),
}

multisite_painters["hg_num_hosts_down"] = {
    "title"   : _("Number of hosts in state DOWN"),
    "short"   : _("Dw"),
    "columns" : [ "hostgroup_num_hosts_down" ],
    "paint"   : lambda row: paint_host_count(1, row["hostgroup_num_hosts_down"]),
}

multisite_painters["hg_num_hosts_unreach"] = {
    "title"   : _("Number of hosts in state UNREACH"),
    "short"   : _("Un"),
    "columns" : [ "hostgroup_num_hosts_unreach" ],
    "paint"   : lambda row: paint_host_count(2, row["hostgroup_num_hosts_unreach"]),
}

multisite_painters["hg_num_hosts_pending"] = {
    "title"   : _("Number of hosts in state PENDING"),
    "short"   : _("Pd"),
    "columns" : [ "hostgroup_num_hosts_pending" ],
    "paint"   : lambda row: paint_host_count(None, row["hostgroup_num_hosts_pending"]),
}

multisite_painters["hg_name"] = {
    "title"   : _("Hostgroup name"),
    "short"   : _("Name"),
    "columns" : ["hostgroup_name"],
    "paint"   : lambda row: (None, row["hostgroup_name"]),
}

multisite_painters["hg_alias"] = {
    "title"   : _("Hostgroup alias"),
    "short"   : _("Alias"),
    "columns" : ["hostgroup_alias"],
    "paint"   : lambda row: (None, row["hostgroup_alias"]),
}

#    ____                  _
#   / ___|  ___ _ ____   _(_) ___ ___  __ _ _ __ ___  _   _ _ __  ___
#   \___ \ / _ \ '__\ \ / / |/ __/ _ \/ _` | '__/ _ \| | | | '_ \/ __|
#    ___) |  __/ |   \ V /| | (_|  __/ (_| | | | (_) | |_| | |_) \__ \
#   |____/ \___|_|    \_/ |_|\___\___|\__, |_|  \___/ \__,_| .__/|___/
#                                     |___/                |_|

multisite_painters["sg_services"] = {
    "title"   : _("Services colored according to state"),
    "short"   : _("Services"),
    "columns" : [ "servicegroup_members_with_state" ],
    "paint"   : lambda row: paint_service_list(row, "servicegroup_members_with_state"),
}

multisite_painters["sg_num_services"] = {
    "title"   : _("Number of services"),
    "short"   : "",
    "columns" : [ "servicegroup_num_services" ],
    "paint"   : lambda row: (None, str(row["servicegroup_num_services"])),
}

multisite_painters["sg_num_services_ok"] = {
    "title"   : _("Number of services in state OK"),
    "short"   : _("O"),
    "columns" : [ "servicegroup_num_services_ok" ],
    "paint"   : lambda row: paint_svc_count(0, row["servicegroup_num_services_ok"])
}

multisite_painters["sg_num_services_warn"] = {
    "title"   : _("Number of services in state WARN"),
    "short"   : _("W"),
    "columns" : [ "servicegroup_num_services_warn" ],
    "paint"   : lambda row: paint_svc_count(1, row["servicegroup_num_services_warn"])
}

multisite_painters["sg_num_services_crit"] = {
    "title"   : _("Number of services in state CRIT"),
    "short"   : _("C"),
    "columns" : [ "servicegroup_num_services_crit" ],
    "paint"   : lambda row: paint_svc_count(2, row["servicegroup_num_services_crit"])
}

multisite_painters["sg_num_services_unknown"] = {
    "title"   : _("Number of services in state UNKNOWN"),
    "short"   : _("U"),
    "columns" : [ "servicegroup_num_services_unknown" ],
    "paint"   : lambda row: paint_svc_count(3, row["servicegroup_num_services_unknown"])
}

multisite_painters["sg_num_services_pending"] = {
    "title"   : _("Number of services in state PENDING"),
    "short"   : _("P"),
    "columns" : [ "servicegroup_num_services_pending" ],
    "paint"   : lambda row: paint_svc_count("p", row["servicegroup_num_services_pending"])
}
multisite_painters["sg_name"] = {
    "title" : _("Servicegroup name"),
    "short" : _("Name"),
    "columns" : ["servicegroup_name"],
    "paint" : lambda row: (None, row["servicegroup_name"])
}
multisite_painters["sg_alias"] = {
    "title" : _("Servicegroup alias"),
    "short" : _("Alias"),
    "columns" : ["servicegroup_alias"],
    "paint" : lambda row: (None, row["servicegroup_alias"])
}


multisite_painters["link_to_pnp_service"] = {
    "title"   : _("(obsolete) Link to PNP4Nagios"),
    "short"   : _("PNP"),
    "columns" : [ "site", "host_name", "service_description", "service_perf_data"],
    "paint"   : lambda row: ("", "")
}

#     ____                                     _
#    / ___|___  _ __ ___  _ __ ___   ___ _ __ | |_ ___
#   | |   / _ \| '_ ` _ \| '_ ` _ \ / _ \ '_ \| __/ __|
#   | |__| (_) | | | | | | | | | | |  __/ | | | |_\__ \
#    \____\___/|_| |_| |_|_| |_| |_|\___|_| |_|\__|___/
#

multisite_painters["comment_id"] = {
    "title"   : _("Comment id"),
    "short"   : _("ID"),
    "columns" : ["comment_id"],
    "paint"   : lambda row: (None, row["comment_id"]),
}
multisite_painters["comment_author"] = {
    "title"   : _("Comment author"),
    "short"   : _("Author"),
    "columns" : ["comment_author"],
    "paint"   : lambda row: (None, row["comment_author"]),
}

multisite_painters["comment_comment"] = {
    "title"   : _("Comment text"),
    "columns" : ["comment_comment"],
    "paint"   : lambda row: (None, htmllib.attrencode(row["comment_comment"])),
}

multisite_painters["comment_what"] = {
    "title"   : _("Comment type (host/service)"),
    "short"   : _("Type"),
    "columns" : ["comment_type"],
    "paint"   : lambda row: (None, row["comment_type"] == 1 and _("Host") or _("Service")),
}

multisite_painters["comment_time"] = {
    "title"   : _("Comment entry time"),
    "short"   : _("Time"),
    "columns" : ["comment_entry_time"],
    "options" : [ "ts_format", "ts_date" ],
    "paint"   : lambda row: paint_age(row["comment_entry_time"], True, 3600),
}

multisite_painters["comment_expires"] = {
    "title"   : _("Comment expiry time"),
    "short"   : _("Expires"),
    "columns" : ["comment_expire_time"],
    "options" : [ "ts_format", "ts_date" ],
    "paint"   : lambda row: paint_age(row["comment_expire_time"], row["comment_expire_time"] != 0, 3600),
}

def paint_comment_entry_type(row):
    t = row["comment_entry_type"]
    linkview = None
    if t == 1:   icon = "comment"
    elif t == 2:
        icon = "downtime"
        if row["service_description"]:
            linkview = "downtimes_of_service"
        else:
            linkview = "downtimes_of_host"

    elif t == 3: icon = "flapping"
    elif t == 4: icon = "ack"
    else:
        return "", ""
    code = '<img class=icon src="images/icon_%s.gif">' % icon
    if linkview:
        code = link_to_view(code, row, linkview)
    return "icons", code

multisite_painters["comment_entry_type"] = {
    "title"   : _("Comment entry type (user/downtime/flapping/ack)"),
    "short"   : _("E.Type"),
    "columns" : ["comment_entry_type", "host_name", "service_description" ],
    "paint"   : paint_comment_entry_type,
}

#    ____                      _   _
#   |  _ \  _____      ___ __ | |_(_)_ __ ___   ___  ___
#   | | | |/ _ \ \ /\ / / '_ \| __| | '_ ` _ \ / _ \/ __|
#   | |_| | (_) \ V  V /| | | | |_| | | | | | |  __/\__ \
#   |____/ \___/ \_/\_/ |_| |_|\__|_|_| |_| |_|\___||___/
#


multisite_painters["downtime_id"] = {
    "title"   : _("Downtime id"),
    "short"   : _("ID"),
    "columns" : ["downtime_id"],
    "paint"   : lambda row: (None, row["downtime_id"]),
}

multisite_painters["downtime_author"] = {
    "title"   : _("Downtime author"),
    "short"   : _("Author"),
    "columns" : ["downtime_author"],
    "paint"   : lambda row: (None, row["downtime_author"]),
}

multisite_painters["downtime_comment"] = {
    "title"   : _("Downtime comment"),
    "short"   : _("Comment"),
    "columns" : ["downtime_comment"],
    "paint"   : lambda row: (None, htmllib.attrencode(row["downtime_comment"])),
}

multisite_painters["downtime_fixed"] = {
    "title"   : _("Downtime is fixed"),
    "short"   : _("Fixed"),
    "columns" : ["downtime_fixed"],
    "paint"   : lambda row: (None, row["downtime_fixed"] == 0 and _("flexible") or _("fixed")),
}

multisite_painters["downtime_what"] = {
    "title"   : _("Downtime type (host/service)"),
    "short"   : _("Type"),
    "columns" : ["is_service"],
    "paint"   : lambda row: (None, row["is_service"] and _("Service") or _("Host")),
}

multisite_painters["downtime_type"] = {
    "title"   : _("Downtime active or pending"),
    "short"   : _("act/pend"),
    "columns" : ["downtime_type"],
    "paint"   : lambda row: (None, row["downtime_type"] == 0 and _("active") or _("pending")),
}

multisite_painters["downtime_entry_time"] = {
    "title"   : _("Downtime entry time"),
    "short"   : _("Entry"),
    "columns" : ["downtime_entry_time"],
    "options" : [ "ts_format", "ts_date" ],
    "paint"   : lambda row: paint_age(row["downtime_entry_time"], True, 3600),
}

multisite_painters["downtime_start_time"] = {
    "title"   : _("Downtime start time"),
    "short"   : _("Start"),
    "columns" : ["downtime_start_time"],
    "options" : [ "ts_format", "ts_date" ],
    "paint"   : lambda row: paint_age(row["downtime_start_time"], True, 3600),
}

multisite_painters["downtime_end_time"] = {
    "title"   : _("Downtime end time"),
    "short"   : _("End"),
    "columns" : ["downtime_end_time"],
    "options" : [ "ts_format", "ts_date" ],
    "paint"   : lambda row: paint_age(row["downtime_end_time"], True, 3600),
}

def paint_downtime_duration(row):
    if row["downtime_fixed"] == 1:
        return None, ""
    else:
        return None, "%02d:%02d" % divmod(row["downtime_duration"] / 60, 60)

multisite_painters["downtime_duration"] = {
    "title"   : _("Downtime duration (if flexible)"),
    "short"   : _("Duration"),
    "columns" : ["downtime_duration", "downtime_fixed"],
    "paint"   : paint_downtime_duration,
}

#    _
#   | |    ___   __ _
#   | |   / _ \ / _` |
#   | |__| (_) | (_| |
#   |_____\___/ \__, |
#               |___/

multisite_painters["log_message"] = {
    "title"   : _("Log: complete message"),
    "short"   : _("Message"),
    "columns" : ["log_message"],
    "paint"   : lambda row: ("", htmllib.attrencode(row["log_message"])),
}

def paint_log_plugin_output(row):
    output = row["log_plugin_output"]
    if output:
        return "", format_plugin_output(output, row)
    else:
        log_type = row["log_type"]
        lst = row["log_state_type"]
        if "FLAPPING" in log_type:
            if "HOST" in log_type:
                what = _("host")
            else:
                what = _("service")
            if lst == "STOPPED":
                return "", _("The %s stopped flapping") % what
            else:
                return "", _("The %s started flapping") % what

        return "", (lst + " - " + log_type)


multisite_painters["log_plugin_output"] = {
    "title"   : _("Log: output of check plugin"),
    "short"   : _("Check output"),
    "columns" : ["log_plugin_output", "log_type", "log_state_type" ],
    "paint"   : paint_log_plugin_output,
}

multisite_painters["log_attempt"] = {
    "title"   : _("Log: number of check attempt"),
    "short"   : _("Att."),
    "columns" : ["log_attempt"],
    "paint"   : lambda row: ("", row["log_attempt"]),
}
multisite_painters["log_state_type"] = {
    "title"   : _("Log: type of state (hard/soft/stopped/started)"),
    "short"   : _("Type"),
    "columns" : ["log_state_type"],
    "paint"   : lambda row: ("", row["log_state_type"]),
}
multisite_painters["log_type"] = {
    "title"   : _("Log: event"),
    "short"   : _("Event"),
    "columns" : ["log_type"],
    "paint"   : lambda row: ("nowrap", row["log_type"]),
}
multisite_painters["log_contact_name"] = {
    "title"   : _("Log: contact name"),
    "short"   : _("Contact"),
    "columns" : ["log_contact_name"],
    "paint"   : lambda row: ("nowrap", row["log_contact_name"]),
}
def paint_log_icon(row):
    img = None
    log_type = row["log_type"]
    if log_type == "SERVICE ALERT":
        img = { 0: "ok", 1: "warn", 2:"crit", 3:"unknown" }.get(row["log_state"])
    elif log_type == "HOST ALERT":
        img = { 0: "up", 1: "down", 2:"unreach" }.get(row["log_state"])
    elif "DOWNTIME" in log_type:
        if row["log_state_type"] == "STOPPED":
            img = "downtimestop"
        else:
            img = "downtime"
    elif log_type.endswith("NOTIFICATION"):
        img = "notify"
    elif log_type == "EXTERNAL COMMAND":
        img = "command"
    elif "restarting..." in log_type:
        img = "restart"
    elif "starting..." in log_type:
        img = "start"
    elif "shutdown..." in log_type:
        img = "stop"
    elif " FLAPPING " in log_type:
        img = "flapping"

    if img:
        return "icon", '<img src="images/alert_%s.png">' % img
    else:
        return "icon", ""

multisite_painters["log_icon"] = {
    "title"   : _("Log: event icon"),
    "short"   : "",
    "columns" : ["log_type", "log_state", "log_state_type"],
    "paint"   : paint_log_icon,
}

multisite_painters["log_options"] = {
    "title"   : _("Log: informational part of message"),
    "short"   : _("Info"),
    "columns" : ["log_options"],
    "paint"   : lambda row: ("", htmllib.attrencode(row["log_options"])),
}

def paint_log_comment(msg):
    if ';' in msg:
        parts = msg.split(';')
        if len(parts) > 6:
          return ("", htmllib.attrencode(parts[-1]))
    return ("", "")

multisite_painters["log_comment"] = {
    "title"   : _("Log: comment"),
    "short"   : _("Comment"),
    "columns" : ["log_options"],
    "paint"   : lambda row: paint_log_comment(row['log_options']),
}

multisite_painters["log_time"] = {
    "title"   : _("Log: entry time"),
    "short"   : _("Time"),
    "columns" : ["log_time"],
    "options" : [ "ts_format", "ts_date" ],
    "paint"   : lambda row: paint_age(row["log_time"], True, 3600 * 24),
}

multisite_painters["log_lineno"] = {
    "title"   : _("Log: line number in log file"),
    "short"   : _("Line"),
    "columns" : ["log_lineno"],
    "paint"   : lambda row: ("number", str(row["log_lineno"])),
}

multisite_painters["log_date"] = {
    "title"   : _("Log: day of entry"),
    "short"   : _("Date"),
    "columns" : ["log_time"],
    "groupby" : lambda row: paint_day(row["log_time"])[1],
    "paint"   : lambda row: paint_day(row["log_time"]),
}

def paint_log_state(row):
    state = row["log_state"]
    if row["log_service_description"]:
        return paint_service_state_short({"service_has_been_checked":1, "service_state" : state})
    else:
        return paint_host_state_short({"host_has_been_checked":1, "host_state" : state})

multisite_painters["log_state"] = {
    "title"   : _("Log: state of host/service at log time"),
    "short"   : _("State"),
    "columns" : ["log_state", "log_service_description"],
    "paint"   : paint_log_state,
}

# Alert statistics

multisite_painters["alert_stats_ok"] = {
    "title"   : _("Alert Statistics: Number of recoveries"),
    "short"   : _("OK"),
    "columns" : [ "alerts_ok" ],
    "paint"   : lambda row: ("", str(row["alerts_ok"])),
}

multisite_painters["alert_stats_warn"] = {
    "title"   : _("Alert Statistics: Number of warnings"),
    "short"   : _("WARN"),
    "columns" : [ "alerts_warn" ],
    "paint"   : lambda row: paint_svc_count(1, row["alerts_warn"]),
}

multisite_painters["alert_stats_crit"] = {
    "title" : _("Alert Statistics: Number of critical alerts"),
    "short" : _("CRIT"),
    "columns" : [ "alerts_crit" ],
    "paint" : lambda row: paint_svc_count(2, row["alerts_crit"])
}

multisite_painters["alert_stats_unknown"] = {
    "title" : _("Alert Statistics: Number of unknown alerts"),
    "short" : _("UNKN"),
    "columns" : [ "alerts_unknown" ],
    "paint" : lambda row: paint_svc_count(3, row["alerts_unknown"])
}

multisite_painters["alert_stats_problem"] = {
    "title" : _("Alert Statistics: Number of problem alerts"),
    "short" : _("PROB"),
    "columns" : [ "alerts_problem" ],
    "paint" : lambda row: paint_svc_count('s', row["alerts_problem"])
}
