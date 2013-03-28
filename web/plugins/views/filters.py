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



# Filters for substring search, displaying a text input field
class FilterText(Filter):
    def __init__(self, name, title, info, column, htmlvar, op):
        Filter.__init__(self, name, title, info, [htmlvar], [column])
        self.op = op
        self.column = column

    def display(self):
        htmlvar = self.htmlvars[0]
        current_value = html.var(htmlvar, "")
        html.text_input(htmlvar, current_value)

    def filter(self, infoname):
        htmlvar = self.htmlvars[0]
        current_value = html.var(htmlvar)
        if current_value:
            return "Filter: %s %s %s\n" % (self.column, self.op, current_value)
        else:
            return ""

    def variable_settings(self, row):
        return [ (self.htmlvars[0], row[self.column]) ]

    def heading_info(self, infoname):
        return html.var(self.htmlvars[0])

#                               filter          title              info       column           htmlvar
declare_filter(100, FilterText("hostregex",    _("Hostname"),        "host",    "host_name",      "host",    "~~"),
                          _("Search field allowing regular expressions and partial matches"))

declare_filter(101, FilterText("host",    _("Hostname (exact match)"),             "host",    "host_name",          "host",    "="),
                          _("Exact match, used for linking"))

declare_filter(200, FilterText("serviceregex", _("Service"),         "service", "service_description",   "service", "~~"),
                          _("Search field allowing regular expressions and partial matches"))

declare_filter(201, FilterText("service", _("Service (exact match)"),              "service", "service_description",   "service", "="),
                          _("Exact match, used for linking"))


declare_filter(101, FilterText("servicegroupnameregex", _("Servicegroup"),   "servicegroup", "servicegroup_name",   "servicegroup_name", "~~"),
                          _("Search field allowing regular expression and partial matches"))

declare_filter(101, FilterText("servicegroupname", _("Servicegroup (enforced)"),   "servicegroup", "servicegroup_name",   "servicegroup_name", "="),
                          _("Exact match, used for linking"))

declare_filter(202, FilterText("output",  _("Status detail"), "service", "service_plugin_output", "service_output", "~~"))



class FilterIPAddress(Filter):
    def __init__(self):
        Filter.__init__(self, "host_address", _("Host IP Address"), "host", ["host_address", "host_address_prefix"], ["host_address"])

    def display(self):
        html.text_input("host_address")
        html.write("<br><br>")
        html.begin_radio_group()
        html.radiobutton("host_address_prefix", "yes", True, _("Prefix match"))
        html.radiobutton("host_address_prefix", "no", False, _("Exact match"))
        html.end_radio_group()

    def double_height(self):
        return True

    def filter(self, infoname):
        address = html.var("host_address")
        if address:
            if html.var("host_address_prefix") == "yes":
                return "Filter: host_address ~ ^%s\n" % address
            else:
                return "Filter: host_address = %s\n" % address
        else:
            return ""

    def variable_settings(self, row):
        return [ ("host_address", row["host_address"]) ]

    def heading_info(self, infoname):
        return html.var("host_address")

declare_filter(102, FilterIPAddress())


# Helper that retrieves the list of host/service/contactgroups via Livestatus
def all_groups(what):
    groups = dict(html.live.query("GET %sgroups\nColumns: name alias\n" % what))
    names = groups.keys()
    names.sort()
    # use alias by default but fallback to name if no alias defined
    return [ (name, groups[name] or name) for name in names ]

class FilterGroupCombo(Filter):
    def __init__(self, what, title, enforce):
        self.enforce = enforce
        self.prefix = not self.enforce and "opt" or ""
        htmlvars = [ self.prefix + what + "group" ]
        if not enforce:
            htmlvars.append("neg_" + htmlvars[0])
        Filter.__init__(self, self.prefix + what + "group", # name,     e.g. "hostgroup"
                title,                                      # title,    e.g. "Hostgroup"
                what.split("_")[0],                         # info,     e.g. "host"
                htmlvars,                                   # htmlvars, e.g. "hostgroup"
                [ what + "group_name" ])                    # rows needed to fetch for link information
        self.what = what

    def display(self):
        choices = all_groups(self.what.split("_")[-1])
        if not self.enforce:
            choices = [("", "")] + choices
        html.select(self.htmlvars[0], choices)
        if not self.enforce:
            html.write(" <nobr>")
            html.checkbox(self.htmlvars[1], label=_("negate"))
            html.write("</nobr>")

    def current_value(self, infoname):
        htmlvar = self.htmlvars[0]
        return html.var(htmlvar)

    def filter(self, infoname):
        current_value = self.current_value(infoname)
        if not current_value:
            if not self.enforce:
                return ""
            # Take first group with the name we search
            current_value = html.live.query_value("GET %sgroups\nColumns: name\nLimit: 1\n" % self.what, None)

        if current_value == None:
            return "" # no {what}group exists!

        col = self.what + "_groups"
        if not self.enforce and html.var(self.htmlvars[1]):
            negate = "!"
        else:
            negate = ""
        return "Filter: %s %s>= %s\n" % (col, negate, current_value)

    def variable_settings(self, row):
        varname = self.htmlvars[0]
        value = row.get(self.what + "group_name")
        if value:
            s = [(varname, value)]
            if not self.enforce:
                negvar = self.htmlvars[1]
                if html.var(negvar):
                    s.append((negvar, html.var(negvar)))
            return s
        else:
            return []

    def heading_info(self, infoname):
        current_value = self.current_value(infoname)
        if current_value:
            alias = html.live.query_value("GET %sgroups\nColumns: alias\nFilter: name = %s\n" %
                (self.what, current_value), current_value)
            return alias


declare_filter(104, FilterGroupCombo("host",            _("Hostgroup"),            False), _("Optional selection of host group"))
declare_filter(104, FilterGroupCombo("host",            _("Hostgroup (enforced)"),            True),  _("Dropdown list, selection of host group is <b>enforced</b>"))
declare_filter(204, FilterGroupCombo("service",         _("Servicegroup"),         False), _("Optional selection of service group"))
declare_filter(205, FilterGroupCombo("service",         _("Servicegroup (enforced)"),         True),  _("Dropdown list, selection of service group is <b>enforced</b>"))
declare_filter(106, FilterGroupCombo("host_contact",    _("Host Contactgroup"),    False), _("Optional selection of host contact group group"))
declare_filter(206, FilterGroupCombo("service_contact", _("Service Contactgroup"), False), _("Optional selection of service contact group group"))

declare_filter(107, FilterText("host_ctc", _("Host Contact"), "host", "host_contacts", "host_ctc", ">="))
declare_filter(207, FilterText("service_ctc", _("Service Contact"), "service", "service_contacts", "service_ctc", ">="))


# Livestatus still misses "contact_groups" column.
# declare_filter(FilterGroupCombo("contact"))

class FilterQueryDropdown(Filter):
    def __init__(self, name, title, info, query, filterline):
        Filter.__init__(self, name, title, info, [ name ], [])
        self.query = query
        self.filterline = filterline

    def display(self):
        selection = html.live.query_column_unique(self.query)
        html.sorted_select(self.name, [("", "")] + [(x,x) for x in selection])

    def filter(self, infoname):
        current = html.var(self.name)
        if current:
            return self.filterline % current
        else:
            return ""

declare_filter(110, FilterQueryDropdown("host_check_command", _("Host check command"), "host", \
        "GET commands\nColumns: name\n", "Filter: host_check_command = %s\n"))
declare_filter(210, FilterQueryDropdown("check_command", _("Service check command"), "service", \
        "GET commands\nColumns: name\n", "Filter: service_check_command = %s\n"))

class FilterServiceState(Filter):
    def __init__(self, name, title, prefix):
        Filter.__init__(self, name, title,
                "service", [ prefix + "st0", prefix + "st1", prefix + "st2", prefix + "st3", prefix + "stp" ], [])
        self.prefix = prefix

    def display(self):
        html.begin_checkbox_group()
        for var, text in [(self.prefix + "st0", "OK"), (self.prefix + "st1", "WARN"), \
                          (self.prefix + "st2", "CRIT"), (self.prefix + "st3", "UNKNOWN"),
                          (self.prefix + "stp", "PEND.")]:
	    #if html.mobile:
	        #text = text[:1]
            html.checkbox(var, True, label=text)
            # html.write(" %s " % text)
        html.end_checkbox_group()

    def filter(self, infoname):
        headers = []
        for i in [0,1,2,3]:
            if html.get_checkbox(self.prefix + "st%d" % i) == False:
                if self.prefix == "hd":
                    column = "service_last_hard_state"
                else:
                    column = "service_state"
                headers.append("Filter: %s = %d\n"
                               "Filter: service_has_been_checked = 1\n"
                               "And: 2\nNegate:\n" % (column, i))
        if html.get_checkbox(self.prefix + "stp") == False:
            headers.append("Filter: service_has_been_checked = 1\n")
        if len(headers) == 5: # none allowed = all allowed (makes URL building easier)
            return ""
        else:
            return "".join(headers)

declare_filter(215, FilterServiceState("svcstate",     _("Service states"),      ""))
declare_filter(216, FilterServiceState("svchardstate", _("Service hard states"), "hd"))

class FilterHostState(Filter):
    def __init__(self):
        Filter.__init__(self, "hoststate", _("Host states"),
                "host", [ "hst0", "hst1", "hst2", "hstp" ], [])

    def display(self):
        html.begin_checkbox_group()
        for var, text in [("hst0", _("UP")), ("hst1", _("DOWN")),
                          ("hst2", _("UNREACH")), ("hstp", _("PENDING"))]:
            html.checkbox(var, True, label=text)
        html.end_checkbox_group()

    def filter(self, infoname):
        headers = []
        for i in [0,1,2]:
            if html.get_checkbox("hst%d" % i) == False:
                headers.append("Filter: host_state = %d\n"
                               "Filter: host_has_been_checked = 1\n"
                               "And: 2\nNegate:\n" % i)
        if html.get_checkbox("hstp") == False:
            headers.append("Filter: host_has_been_checked = 1\n")
        if len(headers) == 4: # none allowed = all allowed (makes URL building easier)
            return ""
        else:
            return "".join(headers)

declare_filter(115, FilterHostState())

class FilterTristate(Filter):
    def __init__(self, name, title, info, column, deflt = -1):
        self.column = column
        self.varname = "is_" + name
        Filter.__init__(self, name, title, info, [ self.varname ], [])
        self.deflt = deflt

    def display(self):
        current = html.var(self.varname)
        html.begin_radio_group(horizontal = True)
        for value, text in [("1", _("yes")), ("0", _("no")), ("-1", _("(ignore)"))]:
            checked = current == value or (current in [ None, ""] and int(value) == self.deflt)
            html.radiobutton(self.varname, value, checked, text + " &nbsp; ")
        html.end_radio_group()

    def tristate_value(self):
        current = html.var(self.varname)
        if current in [ None, "" ]:
            return self.deflt
        return int(current)

    def filter(self, infoname):
        current = self.tristate_value()
        if current == -1: # ignore
            return ""
        elif current == 1:
            return self.filter_code(infoname, True)
        else:
            return self.filter_code(infoname, False)

class FilterNagiosFlag(FilterTristate):
    def __init__(self, info, column, title, deflt = -1):
        FilterTristate.__init__(self, column, title, info, column, deflt)

    def filter_code(self, infoname, positive):
        if positive:
            return "Filter: %s != 0\n" % self.column
        else:
            return "Filter: %s = 0\n" % self.column

class FilterNagiosExpression(FilterTristate):
    def __init__(self, info, name, title, pos, neg, deflt = -1):
        FilterTristate.__init__(self, name, title, info, None, deflt)
        self.pos = pos
        self.neg = neg

    def filter_code(self, infoname, positive):
        return positive and self.pos or self.neg

declare_filter(120, FilterNagiosExpression("host", "summary_host", _("Is summary host"),
            "Filter: host_custom_variable_names >= _REALNAME\n",
            "Filter: host_custom_variable_names < _REALNAME\n"))

declare_filter(250, FilterNagiosFlag("service",       "service_process_performance_data", _("Processes performance data")))
declare_filter(251, FilterNagiosExpression("service", "has_performance_data",             _("Has performance data"),
            "Filter: service_perf_data != \n",
            "Filter: service_perf_data = \n"))

declare_filter(130, FilterNagiosFlag("host",    "host_in_notification_period",      _("Host in notif. period")))
declare_filter(131, FilterNagiosFlag("host",    "host_acknowledged",                _("Host problem has been acknowledged")))
declare_filter(132, FilterNagiosFlag("host",    "host_active_checks_enabled",       _("Host active checks enabled")))
declare_filter(133, FilterNagiosFlag("host",    "host_notifications_enabled",       _("Host notifications enabled")))
declare_filter(230, FilterNagiosFlag("service", "service_acknowledged",             _("Problem acknowledged")))
declare_filter(231, FilterNagiosFlag("service", "service_in_notification_period",   _("Service in notif. per.")))
declare_filter(232, FilterNagiosFlag("service", "service_active_checks_enabled",    _("Active checks enabled")))
declare_filter(233, FilterNagiosFlag("service", "service_notifications_enabled",    _("Notifications enabled")))
declare_filter(236, FilterNagiosFlag("service", "service_is_flapping",              _("Flapping")))
declare_filter(231, FilterNagiosFlag("service", "service_scheduled_downtime_depth", _("Service in downtime")))
declare_filter(132, FilterNagiosFlag("host",    "host_scheduled_downtime_depth",    _("Host in downtime")))
declare_filter(232, FilterNagiosExpression("service", "in_downtime",                _("Host/service in downtime"),
            "Filter: service_scheduled_downtime_depth > 0\nFilter: host_scheduled_downtime_depth > 0\nOr: 2\n",
            "Filter: service_scheduled_downtime_depth = 0\nFilter: host_scheduled_downtime_depth = 0\nAnd: 2\n"))


class FilterSite(Filter):
    def __init__(self, name, enforce):
        Filter.__init__(self, name, _("Site") + (enforce and _( " (enforced)") or ""), None, ["site"], [])
        self.enforce = enforce

    def visible(self):
        return config.is_multisite()

    def display(self):
        site_selector(html, "site", self.enforce)

    def filter(self, infoname):
        if config.is_multisite():
            site = html.var("site")
            if site:
                return "Sites: %s\n" % (html.var("site", ""))
            elif not self.enforce:
                return ""
            else:
                return "Sites:\n" # no site at all
        else:
            return ""

    def heading_info(self, infoname):
        current_value = html.var("site")
        if current_value:
            alias = config.site(current_value)["alias"]
            return alias

    def variable_settings(self, row):
        return [("site", row["site"])]

declare_filter(500, FilterSite("siteopt", False), _("Optional selection of a site"))
declare_filter(501, FilterSite("site",    True),  _("Selection of site is enforced, use this filter for joining"))

# Filter for setting time ranges, e.g. on last_state_change and last_check
# Variante eins:
# age [  ] seconds  [  ] minutes  [  ] hours  [  ] days
# Variante zwei: (not implemented)
# since [2010-01-02] [00:00:00]
# Variante drei: (not implemented)
# from [2010-01-02] [00:00:00] until [2010-01-02] [00:00:00]
class FilterTime(Filter):
    def __init__(self, info, name, title, column):
        self.column = column
        self.name = name
        self.ranges = [
           (86400, _("days")),
           (3600,  _("hours")),
           (60,    _("min")),
           (1,     _("sec")),
        ]
        varnames = [ name + "_from", name + "_from_range",
                     name + "_until", name + "_until_range" ]

        Filter.__init__(self, name, title, info, varnames, [column])

    def double_height(self):
        return True

    def display(self):
        choices = [ (str(sec), title + " " + _("ago")) for sec, title in self.ranges ] + \
                  [ ("abs", _("Date (YYYY-MM-DD)")) ]

        html.write("<table class=filtertime>")
        for what, whatname in [
            ( "from", _("From") ),
            ( "until", _("Until") ) ]:
            varprefix = self.name + "_" + what
            html.write("<tr><td>%s:</td>" % whatname)
            html.write("<td>")
            html.text_input(varprefix, style="width: 116px;")
            html.write("</td><td>")
            html.select(varprefix + "_range", choices, "3600")
            html.write("</td></tr>")
        html.write("</table>")


    def filter(self, infoname):
        fromsecs, untilsecs = self.get_time_range()
        filtertext = ""
        if fromsecs != None:
            filtertext += "Filter: %s >= %d\n" % (self.column, fromsecs)
        if untilsecs != None:
            filtertext += "Filter: %s <= %d\n" % (self.column, untilsecs)
        return filtertext


    # Extract timerange user has selected from HTML variables
    def get_time_range(self):
        range = []
        for what in [ "from", "until" ]:
            varprefix = self.name + "_" + what
            count = html.var(varprefix)
            if count == "":
                range.append(None)
            else:
                rangename = html.var(varprefix + "_range")
                if rangename == "abs":
                    try:
                        range.append(time.mktime(time.strptime(count, "%Y-%m-%d")))
                    except:
                        html.add_user_error(varprefix, _("Please enter the date in the format YYYY-MM-DD."))
                        range.append(None)
                else:
                    try:
                        count = int(count)
                        secs = count * int(rangename)
                        range.append(int(time.time()) - secs)
                    except:
                        range.append(None)
                        html.set_var(varprefix, "")

        return range

    # I'm not sure if this function is useful or ever been called.
    # Problem is, that it is not clear wether to use "since" or "before"
    # here.
    # def variable_settings(self, row):
    #     vars = []
    #     secs = int(time.time()) - row[self.column]
    #     for s, n in self.ranges[::-1]:
    #         v = secs / s
    #         secs -= v * s
    #         vars.append((self.name + "_" + n, secs))
    #     return vars

    # def heading_info(self, infoname):
    #     return _("since the last couple of seconds")

declare_filter(250, FilterTime("service", "svc_last_state_change", _("Last service state change"), "service_last_state_change"))
declare_filter(251, FilterTime("service", "svc_last_check", _("Last service check"), "service_last_check"))

declare_filter(250, FilterTime("host", "host_last_state_change", _("Last host state change"), "host_last_state_change"))
declare_filter(251, FilterTime("host", "host_last_check", _("Last host check"), "host_last_check"))

#    _
#   | |    ___   __ _
#   | |   / _ \ / _` |
#   | |__| (_) | (_| |
#   |_____\___/ \__, |
#               |___/

declare_filter(252, FilterTime("log", "logtime", _("Time of log entry"), "log_time"))
# INFO          0 // all messages not in any other class
# ALERT         1 // alerts: the change service/host state
# PROGRAM       2 // important programm events (restart, ...)
# NOTIFICATION  3 // host/service notifications
# PASSIVECHECK  4 // passive checks
# COMMAND       5 // external commands
# STATE         6 // initial or current states

class FilterLogClass(Filter):
    def __init__(self):
        self.log_classes = [
            (0, _("Informational")), (1, _("Alerts")), (2, _("Program")),
            (3, _("Notifications")), (4, _("Passive checks")),
            (5, _("Commands")),      (6, _("States")) ]

        Filter.__init__(self, "log_class", _("Logentry class"),
                "log", [ "logclass%d" % l for l, c in self.log_classes ], [])

    def double_height(self):
        return True

    def display(self):
        if html.var("filled_in"):
            defval = ""
        else:
            defval = "on"
        html.write("<table cellspacing=0 cellpadding=0>")
        if config.filter_columns == 1:
            num_cols = 4
        else:
            num_cols = 2
        col = 1
        for l, c in self.log_classes:
            if col == 1:
                html.write("<tr>")
            html.write("<td>")
            html.checkbox("logclass%d" % l, defval)
            html.write(c)
            html.write("</td>")
            if col == num_cols:
                html.write("</tr>\n")
                col = 1
            else:
                col += 1
        if col < num_cols:
            html.write("<td></td></tr>")
        html.write("</table>\n")

    def filter(self, infoname):
        headers = []
        if html.var("filled_in"):
            defval = ""
        else:
            defval = "on"

        for l, c in self.log_classes:
            if html.var("logclass%d" % l, defval) == "on":
                headers.append("Filter: class = %d\n" % l)
        if len(headers) == 0:
            return "Limit: 0\n" # no class allowed
        else:
            return "".join(headers) + ("Or: %d\n" % len(headers))

declare_filter(255, FilterLogClass())
declare_filter(202, FilterText("log_plugin_output",  _("Log: plugin output"), "log", "log_plugin_output", "log_plugin_output", "~~"))
declare_filter(260, FilterText("log_contact_name",   _("Log: contact name"),  "log", "log_contact_name",  "log_contact_name",  "="),
                                                                                                  _("Exact match, used for linking"))

class FilterLogState(Filter):
    def __init__(self):
        self._items = [ ("h0", "host", 0, _("Up")),("h1", "host", 1, _("Down")),("h2", "host", 2, _("Unreachable")),
                        ("s0", "service", 0, _("OK")), ("s1", "service", 1, _("Warning")),
                        ("s2", "service", 2, _("Critical")),("s3", "service", 3, _("Unknown")) ]

        Filter.__init__(self, "log_state", _("Type of alerts of hosts and services"),
                "log", [ "logst_" + e[0] for e in self._items ], [])

    def double_height(self):
        return True

    def display(self):
        html.write("<table class=alertstatefilter><tr><td>")
        html.begin_checkbox_group()
        for varsuffix, what, state, text in self._items:
            if state == 0:
                html.write("<u>%s:</u></td><td>" % (_(what.title())))
            html.write("&nbsp; ")
            html.checkbox("logst_" + varsuffix, True, label=text)
            if not html.mobile:
                html.write("<br>")
            if varsuffix == "h2":
                html.write("</td><td>")
        html.end_checkbox_group()
        html.write("</td></tr></table>")

    def filter(self, infoname):
        headers = []
        for varsuffix, what, state, text in self._items:
            if html.get_checkbox("logst_" + varsuffix) != False: # None = form not filled in = allow
                headers.append("Filter: log_type ~ %s .*\nFilter: log_state = %d\nAnd: 2\n" %
                            (what.upper(), state))
        if len(headers) == 0:
            return "Limit: 0\n" # no allowed state
        elif len(headers) == len(self._items):
            return "" # all allowed or form not filled in
        else:
            return "".join(headers) + ("Or: %d\n" % len(headers))

declare_filter(270, FilterLogState())

class BIServiceIsUsedFilter(FilterTristate):
    def __init__(self):
	FilterTristate.__init__(self, "aggr_service_used", _("Used in BI aggregate"), "service", None)

    def filter(self, infoname):
	return ""

    def filter_table(self, rows):
        current = self.tristate_value()
        if current == -1:
	    return rows
        new_rows = []
        for row in rows:
	    is_part = bi.is_part_of_aggregation(
                   "service", row["site"], row["host_name"], row["service_description"])
	    if (is_part and current == 1) or \
               (not is_part and current == 0):
	        new_rows.append(row)
	return new_rows

declare_filter(300, BIServiceIsUsedFilter())
