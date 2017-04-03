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

import bi

class BIGroupFilter(FilterUnicodeFilter):
    def __init__(self):
        self.column = "aggr_group"
        FilterUnicodeFilter.__init__(self, self.column, _("Aggregation group"), "aggr_group", [self.column], [self.column])

    def variable_settings(self, row):
        return [ (self.htmlvars[0], row[self.column]) ]

    def display(self):
        htmlvar = self.htmlvars[0]
        html.dropdown(htmlvar, [ ("", "") ] + [(g, g) for g in bi.aggregation_groups()])

    def selected_group(self):
        return html.get_unicode_input(self.htmlvars[0])

    def filter_table(self, rows):
        group = self.selected_group()
        if not group:
            return rows
        else:
            return [ row for row in rows if row[self.column] == group ]

    def heading_info(self):
        return html.get_unicode_input(self.htmlvars[0])

declare_filter( 90,  BIGroupFilter())

# how is either "regex" or "exact"
class BITextFilter(FilterUnicodeFilter):
    def __init__(self, what, how="regex", suffix=""):
        self.how = how
        self.column = "aggr_" + what
        label = ''
        if what == 'name':
            label = _('Aggregation name')
        elif what == 'output':
            label = _('Aggregation output')
        if how == "exact":
            label += _(" (exact match)")
        FilterUnicodeFilter.__init__(self, self.column + suffix,
                        label, "aggr", [self.column + suffix], [self.column])

    def variable_settings(self, row):
        return [ (self.htmlvars[0], row[self.column]) ]

    def display(self):
        html.text_input(self.htmlvars[0])

    def heading_info(self):
        return html.get_unicode_input(self.htmlvars[0])

    def filter_table(self, rows):
        val = html.get_unicode_input(self.htmlvars[0])
        if not val:
            return rows
        if self.how == "regex":
            try:
                reg = re.compile(val.lower())
            except re.error, e:
                html.add_user_error(None, "Invalid regular expression: %s" % e)
                return rows

            return [ row for row in rows if reg.search(row[self.column].lower()) ]
        else:
            return [ row for row in rows if row[self.column] == val ]


declare_filter(120, BITextFilter("name", suffix="_regex"))
declare_filter(120, BITextFilter("name", how="exact"))
declare_filter(121, BITextFilter("output"))

class BIHostFilter(Filter):
    def __init__(self):
        self.column = "aggr_hosts"
        Filter.__init__(self, self.column, _("Affected hosts contain"), "aggr", ["aggr_host_site", "aggr_host_host"], [])

    def display(self):
        html.text_input(self.htmlvars[1])

    def heading_info(self):
        return html.var(self.htmlvars[1])

    def find_host(self, host, hostlist):
        for s, h in hostlist:
            if h == host:
                return True
        return False

    # Used for linking
    def variable_settings(self, row):
        return [ ("aggr_host_host", row["host_name"]), ("aggr_host_site", row["site"]) ]

    def filter_table(self, rows):
        val = html.var(self.htmlvars[1])
        if not val:
            return rows
        return [ row for row in rows if self.find_host(val, row["aggr_hosts"]) ]

declare_filter(130, BIHostFilter(), _("Filter for all aggregations that base on status information of that host. Exact match (no regular expression)"))

class BIServiceFilter(Filter):
    def __init__(self):
        Filter.__init__(self, "aggr_service", _("Affected by service"), "aggr", ["aggr_service_site", "aggr_service_host", "aggr_service_service"], [])

    def double_height(self):
        return True

    def display(self):
        html.write(_("Host") + ": ")
        html.text_input(self.htmlvars[1])
        html.write(_("Service") + ": ")
        html.text_input(self.htmlvars[2])

    def heading_info(self):
        return html.get_unicode_input(self.htmlvars[1], "") \
               + " / " + html.get_unicode_input(self.htmlvars[2], "")

    def service_spec(self):
        if html.has_var(self.htmlvars[2]):
            return html.get_unicode_input(self.htmlvars[0]), html.get_unicode_input(self.htmlvars[1]), html.get_unicode_input(self.htmlvars[2])

    # Used for linking
    def variable_settings(self, row):
        return [ ("site", row["site"]), ("host", row["host_name"]), ("service", row["service_description"]) ]

declare_filter(131, BIServiceFilter(), _("Filter for all aggregations that are affected by one specific service on a specific host (no regular expression)"))

class BIStatusFilter(Filter):
    def __init__(self, what):
        title = (what.replace("_", " ") + " state").title()
        self.column = "aggr_" + what + "state"
        if what == "":
            self.code = 'r'
        else:
            self.code = what[0]
        self.prefix = "bi%ss" % self.code
        vars = [ self.prefix + str(x) for x in [ -1, 0, 1, 2, 3 ] ]
        if self.code == 'a':
            vars.append(self.prefix + "n")
        Filter.__init__(self, self.column, title, "aggr", vars, [])

    def filter(self, tablename):
        return ""

    def double_height(self):
        return self.column == "aggr_assumed_state"

    def display(self):
        if html.var("filled_in"):
            defval = ""
        else:
            defval = "on"
        for varend, text in [('0', _('OK')), ('1', _('WARN')), ('2', _('CRIT')),
                             ('3', _('UNKN')), ('-1', _('PENDING')), ('n', _('no assumed state set'))]:
            if self.code != 'a' and varend == 'n':
                continue # no unset for read and effective state
            if varend == 'n':
                html.br()
            var = self.prefix + varend
            html.checkbox(var, defval, label=text)

    def filter_table(self, rows):
        jeaders = []
        if html.var("filled_in"):
            defval = ""
        else:
            defval = "on"

        allowed_states = []
        for i in ['0','1','2','3','-1','n']:
            if html.var(self.prefix + i, defval) == "on":
                if i == 'n':
                    s = None
                else:
                    s = int(i)
                allowed_states.append(s)
        newrows = []
        for row in rows:
            if row[self.column] != None:
                s = row[self.column]["state"]
            else:
                s = None
            if s in allowed_states:
                newrows.append(row)
        return newrows

declare_filter(150,  BIStatusFilter(""))
declare_filter(151,  BIStatusFilter("effective_"))
declare_filter(152,  BIStatusFilter("assumed_"))


