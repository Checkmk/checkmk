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

import mkeventd
from  valuespec import *

try:
    mkeventd_enabled = config.mkeventd_enabled
except:
    mkeventd_enabled = False

#   .--Datasources---------------------------------------------------------.
#   |       ____        _                                                  |
#   |      |  _ \  __ _| |_ __ _ ___  ___  _   _ _ __ ___ ___  ___         |
#   |      | | | |/ _` | __/ _` / __|/ _ \| | | | '__/ __/ _ \/ __|        |
#   |      | |_| | (_| | || (_| \__ \ (_) | |_| | | | (_|  __/\__ \        |
#   |      |____/ \__,_|\__\__,_|___/\___/ \__,_|_|  \___\___||___/        |
#   |                                                                      |
#   '----------------------------------------------------------------------'

def table_events(what, columns, add_headers, only_sites, limit, filters):
    # First we wetch the list of all events from mkeventd - either current
    # or historic ones. We ignore any filters for host_ here. Note:
    # event_host and host_name needn't be compatible. They might differ
    # in case. Also in the events table instead of the host name there
    # might be the IP address of the host - while in the monitoring we
    # name. We will join later.
    rows = get_all_events(what, filters, limit)

    # Now we join the stuff with the host information. Therefore we
    # get the information about all hosts that are referred to in 
    # any of the events.
    required_hosts = set()
    for row in rows:
        host = row.get("event_host")
        if host:
            required_hosts.add(host.lower())

    # Get information about these hosts via Livestatus. We
    # allow event_host to match either the host_name or 
    # the host_address.
    host_filters = ""
    for host in required_hosts:
        host_filters += "Filter: host_name =~ %s\n" \
                        "Filter: host_address = %s\n" % (host.encode("utf-8"), host.encode("utf-8"))
    if len(required_hosts) > 0:
        host_filters += "Or: %d\n" % (len(required_hosts) * 2)

    # Make sure that the host name is fetched. We need it for
    # joining. The event columns are always fetched all. The event
    # daemon currently does not implement any Columns: header.
    if "host_name" not in columns:
        columns.append("host_name")
    if "host_address" not in columns:
        columns.append("host_address")

    # Fetch list of hosts. Here is much room for optimization.
    # If no host filter is set, then the data of all hosts would
    # be fetched before we even know if there are any events
    # for those hosts. Better would be first fetching all events
    # and later fetch the data of the relevant hosts.
    hostrows = event_hostrows(columns, only_sites, filters, host_filters)

    # Create lookup dict from hostname/address to the dataset of the host.
    # This speeds up the mapping to the events.
    hostdict = {}
    for row in hostrows:
        hostdict[row["host_name"].lower()] = row
        hostdict[row["host_address"]] = row

    # If there is at least one host filter, then we do not show event
    # entries with an empty host information
    have_host_filter = False
    for filt in filters:
        if filt.info == "host":
            filter_code = filt.filter('event')
            if filter_code:
                have_host_filter = True
            break

    if not have_host_filter:
        # Create empty host for outer join on host table
        empty_host = dict([ (c, "") for c in columns if c.startswith("host_") ])
        empty_host["site"] = ''
        empty_host["host_state"] = 0
        empty_host["host_has_been_checked"] = 0


    # We're ready to join the host-data with the event data now. The question
    # is what to do with events that cannot be mapped to a host...
    new_rows = []
    for event in rows:
        host = event["event_host"].lower()

        if host in hostdict:
            event.update(hostdict[host])
            new_rows.append(event)
        elif not have_host_filter:
            # This event does not belong to any host known by
            # the monitoring. We need to create the columns nevertheless.
            # TODO: If there are any host filters, these events should
            # be dropped.
            # Hier könnten wir Leerdaten eintragen. Dann
            # kann man auch Events sehen, die keinem
            # Host zugeordnet sind. Wenn wir nichts machen,
            # dann fehlen Spalten und die Painter fallen
            # auf die Nase.
            event.update(empty_host)
            new_rows.append(event)

    return new_rows


def event_hostrows(columns, only_sites, filters, host_filters):
    filter_code = ""
    for filt in filters: 
        header = filt.filter("event")
        if not header.startswith("Sites:"):
            filter_code += header
    filter_code += host_filters

    host_columns = filter(lambda c: c.startswith("host_"), columns)
    return get_host_table(filter_code, only_sites, host_columns)


def get_host_table(filter_header, only_sites, add_columns):
    columns = [ "host_name" ] + add_columns

    html.live.set_only_sites(only_sites)
    html.live.set_prepend_site(True)
    data = html.live.query(
            "GET hosts\n" +
            "Columns: " + (" ".join(columns)) + "\n" +
            filter_header)
    html.live.set_prepend_site(False)
    html.live.set_only_sites(None)

    headers = [ "site" ] + columns
    rows = [ dict(zip(headers, row)) for row in data ]
    return rows

def get_all_events(what, filters, limit):
    headers = ""
    for f in filters:
        try:
            headers += f.event_headers()
        except:
            pass
    if limit:
        headers += "Limit: %d\n" % limit

    query = "GET %s\n%s" % (what, headers)
    try:
        debug = config.debug_mkeventd_queries
    except:
        debug = False
    if debug \
            and html.output_format == "html" and 'W' in html.display_options:
        html.write('<div class="livestatus message" onmouseover="this.style.display=\'none\';">'
                   '<tt>%s</tt></div>\n' % (query.replace('\n', '<br>\n')))
    response = mkeventd.query(query)

    # First line of the response is the list of column names. 
    headers = response[0]
    rows = []
    for r in response[1:]:
        rows.append(dict(zip(headers, r)))
    return rows
    
    
# Declare datasource only if the event console is activated. We do
# not want to irritate users that do not know anything about the EC.
if mkeventd_enabled:
    multisite_datasources["mkeventd_events"] = {
        "title"       : _("Event Console: Current Events"),
        "table"       : lambda *args: table_events('events', *args),
        "infos"       : [ "event", "host" ],
        "keys"        : [],
        "idkeys"      : [ 'site', 'host_name', 'event_id' ],
    }
    
    multisite_datasources["mkeventd_history"] = {
        "title"       : _("Event Console: Event History"),
        "table"       : lambda *args: table_events('history', *args),
        "infos"       : [ "history", "event", "host" ],
        "keys"        : [],
        "idkeys"      : [ 'site', 'host_name', 'event_id', 'history_line' ],
    }
    
    #.
    #   .--Filters-------------------------------------------------------------.
    #   |                     _____ _ _ _                                      |
    #   |                    |  ___(_) | |_ ___ _ __ ___                       |
    #   |                    | |_  | | | __/ _ \ '__/ __|                      |
    #   |                    |  _| | | | ||  __/ |  \__ \                      |
    #   |                    |_|   |_|_|\__\___|_|  |___/                      |
    #   |                                                                      |
    #   '----------------------------------------------------------------------'
    
    # All filters for events define a function event_headers, that
    # returns header lines for the event daemon, if the filter is in
    # use.
    class EventFilterText(FilterText):
        def __init__(self, table, filter_name, column, title, op):
           FilterText.__init__(self, filter_name, title, table, column, filter_name, op)
           self._table = table
    
        # Disable Livestatus filter
        def filter(self, infoname):
            return ""
    
        def event_headers(self):
            return FilterText.filter(self, self._table)
    
    declare_filter(200, EventFilterText("event",   "event_id",         "event_id",          _("Event ID"),                              "="))
    declare_filter(200, EventFilterText("event",   "event_rule_id",    "event_rule_id",     _("ID of rule"),                            "="))
    declare_filter(201, EventFilterText("event",   "event_text",       "event_text",        _("Message/Text of event"),                 "~~"))
    declare_filter(201, EventFilterText("event",   "event_application","event_application", _("Application / Syslog-Tag"),              "~~"))
    declare_filter(201, EventFilterText("event",   "event_contact",    "event_contact",     _("Contact Person"),                        "~~"))
    declare_filter(201, EventFilterText("event",   "event_comment",    "event_comment",     _("Comment to the event"),                  "~~"))
    declare_filter(201, EventFilterText("event",   "event_host_regex", "event_host",        _("Hostname/IP-Address of original event"), "~~"))
    declare_filter(201, EventFilterText("event",   "event_host",       "event_host",        _("Hostname/IP-Address of event, exact match"), "="))
    declare_filter(201, EventFilterText("event",   "event_owner",      "event_owner",       _("Owner of event"),                        "~~"))
    declare_filter(221, EventFilterText("history", "history_who",      "history_who",       _("User that performed action"),            "~~"))
    declare_filter(222, EventFilterText("history", "history_line",     "history_line",      _("Line number in history logfile"),        "="))
    
    
    class EventFilterCount(Filter):
        def __init__(self, name, title):
            Filter.__init__(self, name, title, "event", [name + "_from", name + "_to"], [name])
            self._name = name
    
        def display(self):
            html.write("from: ")
            html.number_input(self._name + "_from", "")
            html.write(" to: ")
            html.number_input(self._name + "_to", "")
    
        def filter(self, infoname):
            return ""
    
        def event_headers(self):
            try:
                f = ""
                if html.var(self._name + "_from"):
                    f += "Filter: event_count >= %d\n" % int(html.var(self._name + "_from"))
                if html.var(self._name + "_to"):
                    f += "Filter: event_count <= %d\n" % int(html.var(self._name + "_to"))
                return f
            except:
                return ""
    
    
    declare_filter(205, EventFilterCount("event_count", _("Message count")))
    
    class EventFilterState(Filter):
        def __init__(self, table, name, title, choices):
            varnames = [ name + "_" + str(c[0]) for c in choices ]
            Filter.__init__(self, name, title, table, varnames, [name])
            self._name = name
            self._choices = choices
    
        def double_height(self):
            return len(self._choices) >= 5
    
        def display(self):
            html.begin_checkbox_group()
            c = 0
            for name, title in self._choices:
                c += 1
                html.checkbox(self._name + "_" + str(name), True, label=title)
                if c == 3:
                    html.write("<br>")
                    c = 0
            html.end_checkbox_group()
    
        def filter(self, infoname):
            return ""
    
        def event_headers(self):
            sel = []
            for name, title in self._choices:
                if html.get_checkbox(self._name + "_" + str(name)):
                    sel.append(str(name))
            if len(sel) > 0 and len(sel) < len(self._choices):
                return "Filter: %s in %s\n" % (self._name, " ".join(sel))
    
    
    
    declare_filter(206, EventFilterState("event", "event_state", _("State classification"), [ (0, _("OK")), (1, _("WARN")), (2, _("CRIT")), (3,_("UNKNOWN")) ]))
    declare_filter(207, EventFilterState("event", "event_phase", _("Phase"), mkeventd.phase_names.items()))
    declare_filter(209, EventFilterState("event", "event_priority", _("Syslog Priority"), mkeventd.syslog_priorities))
    declare_filter(225, EventFilterState("history", "history_what", _("History action type"), [(k,k) for k in mkeventd.action_whats.keys()]))
    
    
    class EventFilterTime(FilterTime):
        def __init__(self, table, name, title):
            FilterTime.__init__(self, table, name, title, name)
            self._table = table
    
        def filter(self, infoname):
            return ""
    
        def event_headers(self):
            return FilterTime.filter(self, self._table)
    
    declare_filter(220, EventFilterTime("event", "event_first", _("First occurrance of event")))
    declare_filter(221, EventFilterTime("event", "event_last", _("Last occurrance of event")))
    declare_filter(222, EventFilterTime("history", "history_time", _("Time of entry in event history")))
    
    
    class EventFilterDropdown(Filter):
        def __init__(self, name, title, choices, operator = '='):
            Filter.__init__(self, "event_" + name, title, "event", [ "event_" + name ], [ "event_" + name ])
            self._choices = choices
            self._varname = "event_" + name
            self._operator = operator
    
        def display(self):
            if type(self._choices) == list:
                choices = self._choices
            else:
                choices = self._choices()
            html.select(self._varname, [ ("", "") ] + [(str(n),t) for (n,t) in choices])
    
        def filter(self, infoname):
            return ""
    
        def event_headers(self):
            val = html.var(self._varname)
            if val:
                return "Filter: %s %s %s\n" % (self._varname, self._operator, val)
    
    
    declare_filter(210, EventFilterDropdown("facility", _("Syslog Facility"), mkeventd.syslog_facilities))
    declare_filter(211, EventFilterDropdown("sl", _("Service Level at least"), mkeventd.service_levels, operator='>='))
    
    #.
    #   .--Painters------------------------------------------------------------.
    #   |                 ____       _       _                                 |
    #   |                |  _ \ __ _(_)_ __ | |_ ___ _ __ ___                  |
    #   |                | |_) / _` | | '_ \| __/ _ \ '__/ __|                 |
    #   |                |  __/ (_| | | | | | ||  __/ |  \__ \                 |
    #   |                |_|   \__,_|_|_| |_|\__\___|_|  |___/                 |
    #   |                                                                      |
    #   '----------------------------------------------------------------------'
    
    def paint_event_host(row):
        if row["host_name"]:
            return "", row["host_name"]
        else:
            return "", row["event_host"]
    
    multisite_painters["event_id"] = {
        "title"   : _("ID of the event"),
        "short"   : _("ID"),
        "columns" : ["event_id"],
        "paint"   : lambda row: ("number", row["event_id"]),
    }
    
    multisite_painters["event_count"] = {
        "title"   : _("Count (number of recent occurrances)"),
        "short"   : _("Cnt."),
        "columns" : ["event_count"],
        "paint"   : lambda row: ("number", row["event_count"]),
    }
    
    multisite_painters["event_text"] = {
        "title"   : _("Text/Message of the event"),
        "short"   : _("Message"),
        "columns" : ["event_text"],
        "paint"   : lambda row: ("", row["event_text"]),
    }
    
    multisite_painters["event_first"] = {
        "title"   : _("Time of first occurrance of this serial"),
        "short"   : _("First"),
        "columns" : ["event_first"],
        "options" : [ "ts_format", "ts_date" ],
        "paint"   : lambda row: paint_age(row["event_first"], True, True),
    }
    
    multisite_painters["event_last"] = {
        "title"   : _("Time of last occurrance"),
        "short"   : _("Last"),
        "columns" : ["event_last"],
        "options" : [ "ts_format", "ts_date" ],
        "paint"   : lambda row: paint_age(row["event_last"], True, True),
    }
    
    multisite_painters["event_comment"] = {
        "title"   : _("Comment to the event"),
        "short"   : _("Comment"),
        "columns" : ["event_comment"],
        "paint"   : lambda row: ("", row["event_comment"]),
    }
    
    def mkeventd_paint_sl(row):
        try:
            return "", dict(config.mkeventd_service_levels)[row["event_sl"]]
        except:
            return "", row["event_sl"]
    
    multisite_painters["event_sl"] = {
        "title"   : _("Service-Level"),
        "short"   : _("Level"),
        "columns" : ["event_sl"],
        "paint"   : mkeventd_paint_sl,
    }
    
    multisite_painters["event_host"] = {
        "title"   : _("Hostname/IP-Address"),
        "short"   : _("Host"),
        "columns" : ["event_host", "host_name"],
        "paint"   : paint_event_host,
    }
    
    multisite_painters["event_owner"] = {
        "title"   : _("Owner of event"),
        "short"   : _("owner"),
        "columns" : ["event_owner"],
        "paint"   : lambda row: ("", row["event_owner"]),
    }
    
    multisite_painters["event_contact"] = {
        "title"   : _("Contact Person"),
        "short"   : _("Contact"),
        "columns" : ["event_contact" ],
        "paint"   : lambda row: ("", row["event_contact"]),
    }
    
    multisite_painters["event_application"] = {
        "title"   : _("Application / Syslog-Tag"),
        "short"   : _("Application"),
        "columns" : ["event_application" ],
        "paint"   : lambda row: ("", row["event_application"]),
    }
    
    multisite_painters["event_pid"] = {
        "title"   : _("Process ID"),
        "short"   : _("PID"),
        "columns" : ["event_pid" ],
        "paint"   : lambda row: ("", row["event_pid"]),
    }
    
    multisite_painters["event_priority"] = {
        "title"   : _("Syslog-Priority"),
        "short"   : _("Prio"),
        "columns" : ["event_priority" ],
        "paint"   : lambda row: ("", dict(mkeventd.syslog_priorities)[row["event_priority"]]),
    }
    
    multisite_painters["event_facility"] = {
        "title"   : _("Syslog-Facility"),
        "short"   : _("Facility"),
        "columns" : ["event_facility" ],
        "paint"   : lambda row: ("", dict(mkeventd.syslog_facilities)[row["event_facility"]]),
    }
    
    def paint_rule_id(row):
        rule_id = row["event_rule_id"]
        if config.may("mkeventd.edit"):
            urlvars = htmllib.urlencode_vars([("mode", "mkeventd_edit_rule"), ("rule_id", rule_id)])
            return "", '<a href="wato.py?%s">%s</a>' % (urlvars, rule_id)
        else:
            return "", rule_id
    
    multisite_painters["event_rule_id"] = {
        "title"   : _("Rule-ID"),
        "short"   : _("Rule"),
        "columns" : ["event_rule_id" ],
        "paint"   : paint_rule_id,
    }
    
    def paint_event_state(row):
        state = row["event_state"]
        name = nagios_short_state_names[row["event_state"]]
        return "state svcstate state%s" % state, name
    
    multisite_painters["event_state"] = {
        "title"   : _("State (severity) of event"),
        "short"   : _("State"),
        "columns" : ["event_state"],
        "paint"   : paint_event_state,
    }
    
    multisite_painters["event_phase"] = {
        "title"   : _("Phase of event (open, counting, etc.)"),
        "short"   : _("Phase"),
        "columns" : ["event_phase" ],
        "paint"   : lambda row: ("", mkeventd.phase_names.get(row["event_phase"], ''))
    }
    
    def paint_event_icons(row):
        phase = row["event_phase"]
        if phase == "ack":
            title = _("This event has been acknowledged.")
        elif phase == "counting":
            title = _("This event has not reached the target count yet.")
        elif phase == "delayed":
            title = _("The action of this event is still delayed in the hope of a cancelling event.")
        else:
            return "", ""
        return 'icons', '<img class=icon title="%s" src="images/icon_%s.png">' % (title, phase)
    
    multisite_painters["event_icons"] = {
        "title"   : _("Event Icons"),
        "short"   : _("Icons"),
        "columns" : [ "event_phase" ],
        "paint"   : paint_event_icons,
    }
    
    # Event History
    
    multisite_painters["history_line"] = {
        "title"   : _("Line number in log file"),
        "short"   : _("Line"),
        "columns" : ["history_line" ],
        "paint"   : lambda row: ("number", row["history_line"]),
    }
    
    multisite_painters["history_time"] = {
        "title"   : _("Time of entry in logfile"),
        "short"   : _("Time"),
        "columns" : ["history_time" ],
        "options" : [ "ts_format", "ts_date" ],
        "paint"   : lambda row: paint_age(row["history_time"], True, True),
    }
    
    multisite_painters["history_what"] = {
        "title"   : _("Type of event action"),
        "short"   : _("Action"),
        "columns" : ["history_what" ],
        "paint"   : lambda row: ("", row["history_what"]),
    }
    
    multisite_painters["history_what_explained"] = {
        "title"   : _("Explanation for event action"),
        "columns" : ["history_what" ],
        "paint"   : lambda row: ("", mkeventd.action_whats[row["history_what"]]),
    }
    
    
    multisite_painters["history_who"] = {
        "title"   : _("User who performed action"),
        "short"   : _("Who"),
        "columns" : ["history_who" ],
        "paint"   : lambda row: ("", row["history_who"]),
    }
    
    multisite_painters["history_addinfo"] = {
        "title"   : _("Additional Information"),
        "short"   : _("Info"),
        "columns" : ["history_addinfo" ],
        "paint"   : lambda row: ("", row["history_addinfo"]),
    }
    
    #.
    #   .--Commands------------------------------------------------------------.
    #   |         ____                                          _              |
    #   |        / ___|___  _ __ ___  _ __ ___   __ _ _ __   __| |___          |
    #   |       | |   / _ \| '_ ` _ \| '_ ` _ \ / _` | '_ \ / _` / __|         |
    #   |       | |__| (_) | | | | | | | | | | | (_| | | | | (_| \__ \         |
    #   |        \____\___/|_| |_| |_|_| |_| |_|\__,_|_| |_|\__,_|___/         |
    #   |                                                                      |
    #   '----------------------------------------------------------------------'
    
    def command_executor_mkeventd(command, site):
        response = mkeventd.query("COMMAND %s" % command)
    
    
    # Acknowledge and update comment and contact
    config.declare_permission("mkeventd.update",
            _("Update an event"),
            _("Needed for acknowledging and changing the comment and contact of an event"),
            [ "user", "admin" ])

    # Sub-Permissions for Changing Comment, Contact and Acknowledgement
    config.declare_permission("mkeventd.update_comment",
            _("Update an event: change comment"),
            _("Needed for changing a comment when updating an event"),
            [ "user", "admin" ])
    config.declare_permission("mkeventd.update_contact",
            _("Update an event: change contact"),
            _("Needed for changing a contact when updating an event"),
            [ "user", "admin" ])
    
    def render_mkeventd_update():
        html.write('<table border=0 cellspacing=3 cellpadding=0>')
        if config.may("mkeventd.update_comment"):
            html.write('<tr><td>%s</td><td>' % _("Change comment:"))
            html.text_input('_mkeventd_comment', size=50)
            html.write('</td></tr>')
        if config.may("mkeventd.update_contact"):
            html.write('<tr><td>%s</td><td>' % _("Change contact:"))
            html.text_input('_mkeventd_contact', size=50)
            html.write('</td></tr>')
        html.write('<td></td><td>')
        html.checkbox('_mkeventd_acknowledge', True, label=_("Set event to acknowledged"))
        html.write('</td></tr>')
        html.write('</table>')
        html.button('_mkeventd_update', _("Update"))
    
    def command_mkeventd_update(cmdtag, spec, row):
        if html.var('_mkeventd_update'):
            if config.may("mkeventd.update_comment"):
                comment = html.var_utf8("_mkeventd_comment").strip().replace(";",",")
            else:
                comment = ""
            if config.may("mkeventd.update_contact"):
                contact = html.var_utf8("_mkeventd_contact").strip().replace(":",",")
            else:
                contact = ""
            ack = html.get_checkbox("_mkeventd_acknowledge")
            return "UPDATE;%s;%s;%s;%s;%s" % \
                (row["event_id"], config.user_id, ack and 1 or 0, comment, contact), \
                _("update")
    
    multisite_commands.append({
        "tables"      : [ "event" ],
        "permission"  : "mkeventd.update",
        "title"       : _("Update &amp; Acknowledge"),
        "render"      : render_mkeventd_update,
        "action"      : command_mkeventd_update,
        "executor"    : command_executor_mkeventd,
    })

    # Change event state
    config.declare_permission("mkeventd.changestate",
            _("Change event state"),
            _("This permission allows to change the state classification of an event "
              "(e.g. from CRIT to WARN)."),
            [ "user", "admin" ])

    def render_mkeventd_changestate():
        html.button('_mkeventd_changestate', _("Change Event state to:"))
        html.write("&nbsp;")
        MonitoringState().render_input("_mkeventd_state", 2)

    def command_mkeventd_changestate(cmdtag, spec, row):
        if html.var('_mkeventd_changestate'):
            state = MonitoringState().from_html_vars("_mkeventd_state")
            return "CHANGESTATE;%s;%s;%s" % \
                (row["event_id"], config.user_id, state), \
                _("change the state")

    multisite_commands.append({
        "tables"      : [ "event" ],
        "permission"  : "mkeventd.changestate",
        "title"       : _("Change State"),
        "render"      : render_mkeventd_changestate,
        "action"      : command_mkeventd_changestate,
        "executor"    : command_executor_mkeventd,
    })
    
    
    # Perform custom actions
    config.declare_permission("mkeventd.actions",
            _("Perform custom action"),
            _("This permission is needed for performing the configured actions "
              "(execution of scripts and sending emails)."),
            [ "user", "admin" ])
    
    def render_mkeventd_actions():
        for action_id, title in mkeventd.action_choices(omit_hidden = True):
            html.button("_action_" + action_id, title)
            html.write("<br>")
    
    def command_mkeventd_action(cmdtag, spec, row):
        for action_id, title in mkeventd.action_choices(omit_hidden = True):
            if html.var("_action_" + action_id):
                return "ACTION;%s;%s;%s" % (row["event_id"], config.user_id, action_id), \
                  (_("execute that action &quot;%s&quot") % title)
    
    multisite_commands.append({
        "tables"      : [ "event" ],
        "permission"  : "mkeventd.actions",
        "title"       : _("Custom Action"),
        "render"      : render_mkeventd_actions,
        "action"      : command_mkeventd_action,
        "executor"    : command_executor_mkeventd,
    })
    
    
    # Delete events
    config.declare_permission("mkeventd.delete",
            _("Archive an event"),
            _("Finally archive an event without any further action"),
            [ "user", "admin" ])
    
    
    def command_mkeventd_delete(cmdtag, spec, row):
        if html.var("_delete_event"):
            command = "DELETE;%s;%s" % (row["event_id"], config.user_id)
            title = _("<b>delete</b>")
            return command, title
    
    
    multisite_commands.append({
        "tables"      : [ "event" ],
        "permission"  : "mkeventd.delete",
        "title"       : _("Archive Event"),
        "render"      : lambda: \
            html.button("_delete_event", _("Archive Event")),
        "action"      : command_mkeventd_delete,
        "executor"    : command_executor_mkeventd,
    })
    
    #.
    #   .--Sorters-------------------------------------------------------------.
    #   |                  ____             _                                  |
    #   |                 / ___|  ___  _ __| |_ ___ _ __ ___                   |
    #   |                 \___ \ / _ \| '__| __/ _ \ '__/ __|                  |
    #   |                  ___) | (_) | |  | ||  __/ |  \__ \                  |
    #   |                 |____/ \___/|_|   \__\___|_|  |___/                  |
    #   |                                                                      |
    #   '----------------------------------------------------------------------'
    
    def cmp_simple_state(column, ra, rb):
        a = ra.get(column, -1)
        b = rb.get(column, -1)
        if a == 3: 
            a = 1.5
        if b == 3: 
            b = 1.5
        return cmp(a, b)
    
    
    declare_1to1_sorter("event_id", cmp_simple_number)
    declare_1to1_sorter("event_count", cmp_simple_number)
    declare_1to1_sorter("event_text", cmp_simple_string)
    declare_1to1_sorter("event_first", cmp_simple_number)
    declare_1to1_sorter("event_last", cmp_simple_number)
    declare_1to1_sorter("event_comment", cmp_simple_string)
    declare_1to1_sorter("event_sl", cmp_simple_number)
    declare_1to1_sorter("event_host", cmp_simple_string)
    declare_1to1_sorter("event_contact", cmp_simple_string)
    declare_1to1_sorter("event_application", cmp_simple_string)
    declare_1to1_sorter("event_pid", cmp_simple_number)
    declare_1to1_sorter("event_priority", cmp_simple_number)
    declare_1to1_sorter("event_facility", cmp_simple_number) # maybe convert to text
    declare_1to1_sorter("event_rule_id", cmp_simple_string)
    declare_1to1_sorter("event_state", cmp_simple_state)
    declare_1to1_sorter("event_phase", cmp_simple_string)
    declare_1to1_sorter("event_owner", cmp_simple_string)
    
    declare_1to1_sorter("history_line", cmp_simple_number)
    declare_1to1_sorter("history_time", cmp_simple_number)
    declare_1to1_sorter("history_what", cmp_simple_string)
    declare_1to1_sorter("history_who", cmp_simple_string)
    declare_1to1_sorter("history_addinfo", cmp_simple_string)
    
    #.
    #   .--Views---------------------------------------------------------------.
    #   |                    __     ___                                        |
    #   |                    \ \   / (_) _____      _____                      |
    #   |                     \ \ / /| |/ _ \ \ /\ / / __|                     |
    #   |                      \ V / | |  __/\ V  V /\__ \                     |
    #   |                       \_/  |_|\___| \_/\_/ |___/                     |
    #   |                                                                      |
    #   '----------------------------------------------------------------------'
    
    def mkeventd_view(d):
        x = {
            'topic':           u'Event Console',
            'browser_reload':  60,
            'column_headers':  'pergroup',
            'icon':            'mkeventd',
            'mobile':          False,
            'hidden':          False,
            'mustsearch':      False,
            'group_painters':  [],
            'num_columns':     1,
            'hidebutton':      False,
            'play_sounds':     False,
            'public':          True,
            'sorters':         [],
            'user_sortable':   'on',
            'show_filters':    [],
            'hard_filters':    [],
            'hide_filters':    [],
            'hard_filtervars': [],
        }
        x.update(d)
        return x
    
    # Table of all open events
    multisite_builtin_views['ec_events'] = mkeventd_view({
        'title':       u'Events',
        'description': u'Table of all currently open events (handled and unhandled)',
        'datasource':  'mkeventd_events',
        'layout':      'table',
        'painters': [
            ('event_id',     'ec_event', ''),
            ('event_icons', None, ''),
            ('event_state',   None, ''),
            ('event_sl',      None, ''),
            ('event_host',   'ec_events_of_host', ''),
            ('event_rule_id', None, ''),
            ('event_application', None, ''),
            ('event_text',    None, ''),
            ('event_last',    None, ''),
            ('event_count',   None, ''),
        ],
        'show_filters': [
            'event_id',
            'event_rule_id',
            'event_text',
            'event_application',
            'event_contact',
            'event_comment',
            'event_host_regex',
            'event_count',
            'event_phase',
            'event_state',
            'event_first',
            'event_last',
            'event_priority',
            'event_facility',
            'event_sl',
            'hostregex',
        ],
        'hard_filtervars': [
            ( 'event_phase_open',     "on" ),
            ( 'event_phase_ack',      "on" ),
            ( 'event_phase_counting', ""   ),
            ( 'event_phase_delayed',  ""   ),
        ],
    })
    
    multisite_builtin_views['ec_events_of_monhost'] = mkeventd_view({
        'title':       u'Events of Monitored Host',
        'description': u'Currently open events of a host that is monitored',
        'datasource':  'mkeventd_events',
        'layout':      'table',
        'hidden':      True,
        'painters': [
            ('event_id',     'ec_event', ''),
            ('event_icons', None, ''),
            ('event_state',   None, ''),
            ('event_sl',      None, ''),
            ('event_rule_id', None, ''),
            ('event_application', None, ''),
            ('event_text',    None, ''),
            ('event_last',    None, ''),
            ('event_count',   None, ''),
        ],
        'show_filters': [
            'event_id',
            'event_rule_id',
            'event_text',
            'event_application',
            'event_contact',
            'event_comment',
            'event_count',
            'event_phase',
            'event_state',
            'event_first',
            'event_last',
            'event_priority',
            'event_facility',
            'event_sl',
        ],
        'hide_filters': [
            'site',
            'host',
        ],
    })
    multisite_builtin_views['ec_events_of_host'] = mkeventd_view({
        'title':       u'Events of Host',
        'description': u'Currently open events of one specific host',
        'datasource':  'mkeventd_events',
        'layout':      'table',
        'hidden':      True,
        'painters': [
            ('event_id',     'ec_event', ''),
            ('event_icons', None, ''),
            ('event_state',   None, ''),
            ('event_sl',      None, ''),
            ('event_rule_id', None, ''),
            ('event_application', None, ''),
            ('event_text',    None, ''),
            ('event_last',    None, ''),
            ('event_count',   None, ''),
        ],
        'show_filters': [
            'event_id',
            'event_rule_id',
            'event_text',
            'event_application',
            'event_contact',
            'event_comment',
            'event_count',
            'event_phase',
            'event_state',
            'event_first',
            'event_last',
            'event_priority',
            'event_facility',
            'event_sl',
        ],
        'hide_filters': [
            'site',
            'event_host',
        ],
    })
    
    multisite_builtin_views['ec_event'] = mkeventd_view({
        'title':        u'Event Details',
        'description':  u'Details about one event',
        'linktitle':    'Event Details',
        'datasource':   'mkeventd_events',
        'layout':       'dataset',
    
        'hidden':       True,
        'browser_reload': 0,
        'hide_filters': [
            'event_id',
        ],
        'painters': [
            ('event_state', None, ''),
            ('event_host', None, ''),
            ('host_address', 'hoststatus', ''),
            ('host_contacts', None, ''),
            ('host_icons', None, ''),
            ('event_text', None, ''),
            ('event_comment', None, ''),
            ('event_owner', None, ''),
            ('event_first', None, ''),
            ('event_last', None, ''),
            ('event_id', None, ''),
            ('event_icons', None, ''),
            ('event_count', None, ''),
            ('event_sl', None, ''),
            ('event_contact', None, ''),
            ('event_application', None, ''),
            ('event_pid', None, ''),
            ('event_priority', None, ''),
            ('event_facility', None, ''),
            ('event_rule_id', None, ''),
            ('event_phase', None, ''),
            ('host_services', None, ''),
        ],
    })
    
    multisite_builtin_views['ec_history_recent'] = mkeventd_view({
        'title':       u'Recent Event History',
        'description': u'Information about events and actions on events during the '
                       u'recent 24 hours.',
        'datasource':  'mkeventd_history',
        'layout':      'table',
    
        'painters': [
            ('history_time', None, ''),
            ('event_id',     'ec_historyentry', ''),
            ('history_who',  None, ''),
            ('history_what', None, ''),
            ('event_icons', None, ''),
            ('event_state',   None, ''),
            ('event_phase',   None, ''),
            ('event_sl',      None, ''),
            ('event_host',   'ec_history_of_host', ''),
            ('event_rule_id', None, ''),
            ('event_application', None, ''),
            ('event_text',    None, ''),
            ('event_last',    None, ''),
            ('event_count',   None, ''),
        ],
        'show_filters': [
            'event_id',
            'event_rule_id',
            'event_text',
            'event_application',
            'event_contact',
            'event_comment',
            'event_host_regex',
            'event_count',
            'event_phase',
            'event_state',
            'event_first',
            'event_last',
            'event_priority',
            'event_facility',
            'event_sl',
            'history_time',
            'history_who',
            'history_what',
        ],
        'hard_filtervars': [
           ('history_time_from', '1'),
           ('history_time_from_range', '86400'),
        ],
        'sorters': [
            ('history_time', False),
        ],
    })
    
    multisite_builtin_views['ec_historyentry'] = mkeventd_view({
        'title':        u'Event History Entry',
        'description':  u'Details about a historical event history entry',
        'datasource':   'mkeventd_history',
        'layout':       'dataset',
    
        'hidden':       True,
        'browser_reload': 0,
        'hide_filters': [
            'event_id',
            'history_line',
        ],
        'painters': [
            ('history_time', None, ''),
            ('history_line', None, ''),
            ('history_what', None, ''),
            ('history_what_explained', None, ''),
            ('history_who', None, ''),
            ('history_addinfo', None, ''),
            ('event_state', None, ''),
            ('event_host', 'ec_history_of_host', ''),
            ('event_text', None, ''),
            ('event_comment', None, ''),
            ('event_owner', None, ''),
            ('event_first', None, ''),
            ('event_last', None, ''),
            ('event_id', 'ec_history_of_event', ''),
            ('event_icons', None, ''),
            ('event_count', None, ''),
            ('event_sl', None, ''),
            ('event_contact', None, ''),
            ('event_application', None, ''),
            ('event_pid', None, ''),
            ('event_priority', None, ''),
            ('event_facility', None, ''),
            ('event_rule_id', None, ''),
            ('event_phase', None, ''),
        ],
    })
    
    multisite_builtin_views['ec_history_of_event'] = mkeventd_view({
        'title':        u'History of Event',
        'description':  u'History entries of one specific event',
        'datasource':   'mkeventd_history',
        'layout':       'table',
        'columns':      1,
    
        'hidden':       True,
        'browser_reload': 0,
        'hide_filters': [
            'event_id',
        ],
        'painters': [
            ('history_time', None, ''),
            ('history_line', 'ec_historyentry', ''),
            ('history_what', None, ''),
            ('history_what_explained', None, ''),
            ('history_who', None, ''),
            ('event_state', None, ''),
            ('event_host', None, ''),
            ('event_application', None, ''),
            ('event_text', None, ''),
            ('event_sl', None, ''),
            ('event_priority', None, ''),
            ('event_facility', None, ''),
            ('event_phase', None, ''),
            ('event_count', None, ''),
        ],
        'sorters': [
            ('history_time', False),
        ],
    })

    multisite_builtin_views['ec_history_of_host'] = mkeventd_view({
        'title':        u'Event History of Host',
        'description':  u'History entries of one specific host',
        'datasource':   'mkeventd_history',
        'layout':       'table',
        'columns':      1,
    
        'hidden':       True,
        'browser_reload': 0,
        'hide_filters': [
            'event_host',
        ],
        'show_filters': [
            'event_id',
            'event_rule_id',
            'event_text',
            'event_application',
            'event_contact',
            'event_comment',
            'event_count',
            'event_phase',
            'event_state',
            'event_first',
            'event_last',
            'event_priority',
            'event_facility',
            'event_sl',
            'history_time',
            'history_who',
            'history_what',
        ],
        'painters': [
            ('history_time', None, ''),
            ('event_id', 'ec_history_of_event', ''),
            ('history_line', 'ec_historyentry', ''),
            ('history_what', None, ''),
            ('history_what_explained', None, ''),
            ('history_who', None, ''),
            ('event_state', None, ''),
            ('event_host', None, ''),
            ('event_application', None, ''),
            ('event_text', None, ''),
            ('event_sl', None, ''),
            ('event_priority', None, ''),
            ('event_facility', None, ''),
            ('event_phase', None, ''),
            ('event_count', None, ''),
        ],
        'sorters': [
            ('history_time', False),
        ],
    })
