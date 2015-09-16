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
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import mkeventd

try:
    mkeventd_enabled = config.mkeventd_enabled
except:
    mkeventd_enabled = False

# Declare datasource only if the event console is activated. We do
# not want to irritate users that do not know anything about the EC.
if mkeventd_enabled:

    #   .--Infos---------------------------------------------------------------.
    #   |                       ___        __                                  |
    #   |                      |_ _|_ __  / _| ___  ___                        |
    #   |                       | || '_ \| |_ / _ \/ __|                       |
    #   |                       | || | | |  _| (_) \__ \                       |
    #   |                      |___|_| |_|_|  \___/|___/                       |
    #   |                                                                      |
    #   +----------------------------------------------------------------------+
    #   |                                                                      |
    #   '----------------------------------------------------------------------'

    infos['event'] = {
        'title'       : _('Event Console Event'),
        'title_plural': _('Event Console Events'),
        'single_spec' : [
            ('event_id', Integer(
                title = _('Event ID'),
            )),
        ]
    }

    infos['history'] = {
        'title'       : _('Historic Event Console Event'),
        'title_plural': _('Historic Event Console Events'),
        'single_spec' : [
            ('event_id', Integer(
                title = _('Event ID'),
            )),
            ('history_line', Integer(
                title = _('History Line Number'),
            )),
        ]
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
    declare_filter(201, EventFilterText("event",   "event_host_regex", "event_host",        _("Hostname of original event"),            "~~"))
    declare_filter(201, EventFilterText("event",   "event_host",       "event_host",        _("Hostname of event, exact match"),        "="))
    declare_filter(201, EventFilterText("event",   "event_ipaddress",  "event_ipaddress",   _("Original IP Address of event"),          "~~"))
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
            chars = 0
            for name, title in self._choices:
                chars += len(title) + 2
                html.checkbox(self._name + "_" + str(name), True, label=title)
                if (title[0].isupper() and chars > 24) or \
                    (title[0].islower() and chars > 36):
                    html.write("<br>")
                    chars = 0
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
        def __init__(self, name, title, choices, operator = '=', column=None):
            if column == None:
                column = name
            self._varname = "event_" + name
            Filter.__init__(self, "event_" + name, title, "event", [ self._varname ], [ "event_" + column ])
            self._choices = choices
            self._column = column
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
                return "Filter: event_%s %s %s\n" % (self._column, self._operator, val)



    declare_filter(210, EventFilterDropdown("facility", _("Syslog Facility"), mkeventd.syslog_facilities))
    declare_filter(211, EventFilterDropdown("sl", _("Service Level at least"), mkeventd.service_levels, operator='>='))
    declare_filter(211, EventFilterDropdown("sl_max", _("Service Level at most"), mkeventd.service_levels, operator='<=', column="sl"))
