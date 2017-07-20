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

    declare_filter(200, FilterText("event_id",         _("Event ID"),                        "event",   "event_id",           "event_id",               "="))
    declare_filter(200, FilterText("event_rule_id",    _("ID of rule"),                      "event",   "event_rule_id",      "event_rule_id",          "="))
    declare_filter(201, FilterText("event_text",       _("Message/Text of event"),           "event",   "event_text",         "event_text",             "~~"))
    declare_filter(201, FilterText("event_application",_("Application / Syslog-Tag"),        "event",   "event_application",  "event_application",      "~~"))
    declare_filter(201, FilterText("event_contact",    _("Contact Person"),                  "event",   "event_contact",      "event_contact",          "~~"))
    declare_filter(201, FilterText("event_comment",    _("Comment to the event"),            "event",   "event_comment",      "event_comment",          "~~"))
    declare_filter(201, FilterText("event_host_regex", _("Hostname of original event"),      "event",   "event_host",         "event_host",             "~~"))
    declare_filter(201, FilterText("event_host",       _("Hostname of event, exact match"),  "event",   "event_host",         "event_host",             "="))
    declare_filter(201, FilterText("event_ipaddress",  _("Original IP Address of event"),    "event",   "event_ipaddress",    "event_ipaddress",        "~~"))
    declare_filter(201, FilterText("event_owner",      _("Owner of event"),                  "event",   "event_owner",        "event_owner",            "~~"))
    declare_filter(221, FilterText("history_who",      _("User that performed action"),      "history", "history_who",        "history_who",            "~~"))
    declare_filter(222, FilterText("history_line",     _("Line number in history logfile"),  "history", "history_line",       "history_line",           "="))


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
            f = ""
            if html.var(self._name + "_from"):
                f += "Filter: event_count >= %d\n" % int(html.var(self._name + "_from"))
            if html.var(self._name + "_to"):
                f += "Filter: event_count <= %d\n" % int(html.var(self._name + "_to"))
            return f


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
                    html.br()
                    chars = 0
            html.end_checkbox_group()

        def filter(self, infoname):
            selected = []
            for name, title in self._choices:
                if html.get_checkbox(self._name + "_" + str(name)):
                    selected.append(str(name))

            if not selected:
                return ""

            filters = []
            for sel in selected:
                filters.append("Filter: %s = %s" % (self._name, sel))

            f = "\n".join(filters)
            if len(filters) > 1:
                f += "\nOr: %d" % len(filters)

            return f + "\n"


    declare_filter(206, EventFilterState("event", "event_state", _("State classification"), [ (0, _("OK")), (1, _("WARN")), (2, _("CRIT")), (3,_("UNKNOWN")) ]))
    declare_filter(207, EventFilterState("event", "event_phase", _("Phase"), mkeventd.phase_names.items()))
    declare_filter(209, EventFilterState("event", "event_priority", _("Syslog Priority"), mkeventd.syslog_priorities))
    declare_filter(225, EventFilterState("history", "history_what", _("History action type"), [(k,k) for k in mkeventd.action_whats.keys()]))

    declare_filter(220, FilterTime("event",   "event_first",  _("First occurrance of event"),      "event_first", ))
    declare_filter(221, FilterTime("event",   "event_last",   _("Last occurrance of event"),       "event_last",  ))
    declare_filter(222, FilterTime("history", "history_time", _("Time of entry in event history"), "history_time",))


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
            val = html.var(self._varname)
            if val:
                return "Filter: event_%s %s %s\n" % (self._column, self._operator, val)
            else:
                return ""


    declare_filter(210, EventFilterDropdown("facility", _("Syslog Facility"), mkeventd.syslog_facilities))
    declare_filter(211, EventFilterDropdown("sl", _("Service Level at least"), mkeventd.service_levels, operator='>='))
    declare_filter(211, EventFilterDropdown("sl_max", _("Service Level at most"), mkeventd.service_levels, operator='<=', column="sl"))


    class EventFilterEffectiveContactGroupCombo(FilterGroupCombo):
        def __init__(self, enforce=False):
            # TODO: Cleanup hierarchy here. The FilterGroupCombo constructor needs to be refactored
            FilterGroupCombo.__init__(self,
                what="event_effective_contact",
                title=_("Contact group (effective)"),
                enforce=enforce,
            )
            self.what = "contact"
            self.info = "event"
            self.link_columns = [ "event_contact_groups", "event_contact_groups_precedence", "host_contact_groups" ]


        def filter(self, infoname):
            if not html.has_var(self.htmlvars[0]):
                return "" # Skip if filter is not being set at all

            current_value = self.current_value()
            if not current_value:
                if not self.enforce:
                    return ""
                current_value = sites.live().query_value("GET contactgroups\nCache: reload\nColumns: name\nLimit: 1\n", None)

            if current_value == None:
                return "" # no {what}group exists!

            if not self.enforce and html.var(self.htmlvars[1]):
                negate = "!"
            else:
                negate = ""

            return "Filter: event_contact_groups_precedence = host\n" \
                   "Filter: host_contact_groups %s>= %s\n" \
                   "And: 2\n" \
                   "Filter: event_contact_groups_precedence = rule\n" \
                   "Filter: event_contact_groups %s>= %s\n" \
                   "And: 2\n" \
                   "Or: 2\n" % (negate, lqencode(current_value),
                                negate, lqencode(current_value))


        def variable_settings(self, row):
            return []

    declare_filter(212, EventFilterEffectiveContactGroupCombo())
