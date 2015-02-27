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



# Filters for substring search, displaying a text input field
class FilterText(Filter):
    def __init__(self, name, title, info, column, htmlvar, op, negateable=False):
        htmlvars = [htmlvar]
        if negateable:
            htmlvars.append("neg_" + htmlvar)
        Filter.__init__(self, name, title, info, htmlvars, [column])
        self.op = op
        self.column = column
        self.negateable = negateable

    def _current_value(self):
        htmlvar = self.htmlvars[0]
        return html.var(htmlvar, "")

    def display(self):
        current_value = self._current_value()
        html.text_input(self.htmlvars[0], current_value, self.negateable and 'neg' or '')
        if self.negateable:
            html.write(" <nobr>")
            html.checkbox(self.htmlvars[1], label=_("negate"))
            html.write("</nobr>")

    def filter(self, infoname):
        current_value = self._current_value()

        if self.negateable and html.get_checkbox(self.htmlvars[1]):
            negate = "!"
        else:
            negate = ""

        if current_value:
            return "Filter: %s %s%s %s\n" % (self.column, negate, self.op, lqencode(current_value))
        else:
            return ""

    def variable_settings(self, row):
        return [ (self.htmlvars[0], row[self.column]) ]

    def heading_info(self):
        return self._current_value()


class FilterUnicode(FilterText):
    def _current_value(self):
        htmlvar = self.htmlvars[0]
        return html.var_utf8(htmlvar, "")

    def filter(self, infoname):
        current_value = self._current_value()
        if current_value:
            return "Filter: %s %s %s\n" % (self.column, self.op, lqencode(current_value.encode('utf-8')))
        else:
            return ""

#                               filter          title              info       column           htmlvar
declare_filter(100, FilterText("hostregex",    _("Hostname"),        "host",    "host_name",      "host_regex",    "~~"),
                          _("Search field allowing regular expressions and partial matches"))

declare_filter(101, FilterText("host",    _("Hostname (exact match)"),             "host",    "host_name",          "host",    "="),
                          _("Exact match, used for linking"))

declare_filter(102, FilterUnicode("hostalias",   _("Hostalias"),      "host",     "host_alias",      "hostalias",    "~~"),
                          _("Search field allowing regular expressions and partial matches"))

declare_filter(200, FilterUnicode("serviceregex", _("Service"),         "service", "service_description",   "service_regex", "~~"),
                          _("Search field allowing regular expressions and partial matches"))

declare_filter(201, FilterUnicode("service", _("Service (exact match)"),              "service", "service_description",   "service", "="),
                          _("Exact match, used for linking"))

declare_filter(202, FilterUnicode("service_display_name", _("Service alternative display name"),   "service", "service_display_name",   "service_display_name", "~~"),
                          _("Alternative display name of the service, regex match"))

declare_filter(202, FilterUnicode("output",  _("Status detail"), "service", "service_plugin_output", "service_output", "~~"))

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
                return "Filter: host_address ~ ^%s\n" % lqencode(address)
            else:
                return "Filter: host_address = %s\n" % lqencode(address)
        else:
            return ""

    def variable_settings(self, row):
        return [ ("host_address", row["host_address"]) ]

    def heading_info(self):
        return html.var("host_address")

declare_filter(102, FilterIPAddress())


# Helper that retrieves the list of host/service/contactgroups via Livestatus
# use alias by default but fallback to name if no alias defined
def all_groups(what):
    groups = dict(html.live.query("GET %sgroups\nCache: reload\nColumns: name alias\n" % what))
    return [ (name, groups[name] or name) for name in groups.keys() ]

class FilterMultigroup(Filter):
    def __init__(self, what, title):
        htmlvars = [ what + "groups" ]
        Filter.__init__(self, htmlvars[0], # name
                              title,
                              what,        # info, e.g. "service"
                              htmlvars,
                              [])          # no link info needed
        self.what = what
        self.htmlvar = htmlvars[0]

    def double_height(self):
        return True

    def valuespec(self):
        return DualListChoice(choices = all_groups(self.what), autoheight=False, enlarge_active=True)

    def selection(self):
        current = html.var(self.htmlvar, "").strip().split("|")
        if current == ['']:
            return []
        else:
            return current

    def display(self):
        html.write('<div class=multigroup>')
        self.valuespec().render_input(self.htmlvar, self.selection())
        html.write('</div>')

    def filter(self, infoname):
        current = self.selection()
        if len(current) == 0:
            return "" # No group selected = all groups selected, filter unused
        filters = ""
        for group in current:
            filters += "Filter: %s_groups >= %s\n" % (self.what, lqencode(group))
        filters += "Or: %d\n" % len(current)
        return filters


# Selection of a host/service(-contact) group as an attribute of a host or service
class FilterGroupCombo(Filter):
    def __init__(self, what, title, enforce):
        self.enforce = enforce
        self.prefix = not self.enforce and "opt" or ""
        htmlvars = [ self.prefix + what + "_group" ]
        if not enforce:
            htmlvars.append("neg_" + htmlvars[0])
        Filter.__init__(self, self.prefix + what + "group", # name,     e.g. "hostgroup"
                title,                                      # title,    e.g. "Hostgroup"
                what.split("_")[0],                         # info,     e.g. "host"
                htmlvars,                                   # htmlvars, e.g. "host_group"
                [ what + "group_name" ])                    # rows needed to fetch for link information
        self.what = what

    def double_height(self):
        return True

    def display(self):
        choices = all_groups(self.what.split("_")[-1])
        if not self.enforce:
            choices = [("", "")] + choices
        html.sorted_select(self.htmlvars[0], choices)
        if not self.enforce:
            html.write(" <nobr>")
            html.checkbox(self.htmlvars[1], label=_("negate"))
            html.write("</nobr>")

    def current_value(self):
        htmlvar = self.htmlvars[0]
        return html.var(htmlvar)

    def filter(self, infoname):
        if not html.has_var(self.htmlvars[0]):
            return "" # Skip if filter is not being set at all

        current_value = self.current_value()
        if not current_value:
            if not self.enforce:
                return ""
            # Take first group with the name we search
            table = self.what.replace("host_contact", "contact").replace("service_contact", "contact")
            current_value = html.live.query_value("GET %sgroups\nCache: reload\nColumns: name\nLimit: 1\n" % table, None)

        if current_value == None:
            return "" # no {what}group exists!

        col = self.what + "_groups"
        if not self.enforce and html.var(self.htmlvars[1]):
            negate = "!"
        else:
            negate = ""
        return "Filter: %s %s>= %s\n" % (col, negate, lqencode(current_value))

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

    def heading_info(self):
        current_value = self.current_value()
        if current_value:
            table = self.what.replace("host_contact", "contact").replace("service_contact", "contact")
            alias = html.live.query_value("GET %sgroups\nCache: reload\nColumns: alias\nFilter: name = %s\n" %
                (table, lqencode(current_value)), current_value)
            return alias

declare_filter(104, FilterGroupCombo("host",            _("Host is in Group"),     False), _("Optional selection of host group"))
declare_filter(105, FilterMultigroup("host",            _("Several Host Groups")), _("Selection of multiple host groups"))
declare_filter(204, FilterGroupCombo("service",         _("Service is in Group"),     False), _("Optional selection of service group"))
declare_filter(205, FilterGroupCombo("service",         _("Servicegroup (enforced)"), True),  _("Dropdown list, selection of service group is <b>enforced</b>"))
declare_filter(205, FilterMultigroup("service",         _("Several Service Groups")), _("Selection of multiple service groups"))

declare_filter(106, FilterGroupCombo("host_contact",    _("Host Contact Group"),    False), _("Optional selection of host contact group"))
declare_filter(206, FilterGroupCombo("service_contact", _("Service Contact Group"), False), _("Optional selection of service contact group"))

declare_filter(107, FilterText("host_ctc", _("Host Contact"), "host", "host_contacts", "host_ctc", ">="))
declare_filter(207, FilterText("service_ctc", _("Service Contact"), "service", "service_contacts", "service_ctc", ">="))


# Selection of one group to be used in the info "hostgroup" or "servicegroup".
class FilterGroupSelection(Filter):
    def __init__(self, infoname, title):
        Filter.__init__(self, name=infoname, title=title, info=infoname, htmlvars=[infoname], link_columns=[])
        self.what = infoname

    def display(self):
        choices = all_groups(self.what[:-5]) # chop off "group", leaves host or service
        html.sorted_select(self.htmlvars[0], choices)

    def current_value(self):
        return html.var(self.htmlvars[0])

    def filter(self, infoname):
        current_value = self.current_value()
        if current_value:
            return "Filter: %s_name = %s\n" % (self.what, lqencode(current_value))
        else:
            return ""

    def variable_settings(self, row):
        group_name = row[self.what + "_name"]
        return [ (self.htmlvars[0], group_name) ]

# Filter for selecting one specific host group in the hostgroup views
declare_filter(104, FilterGroupSelection("hostgroup",    _("Host Group")),       _("Selection of the host group"))
declare_filter(104, FilterGroupSelection("servicegroup", _("Service Group")), _("Selection of the service group"))

class FilterHostgroupVisibility(Filter):
    def __init__(self, name, title):
        Filter.__init__(self, name=name, title=title, info="hostgroup", htmlvars=[ "hostgroupshowempty" ], link_columns=[])

    def display(self):
        html.checkbox("hostgroupshowempty", False, label="Show empty groups")

    def filter(self, infoname):
        if html.var("hostgroupshowempty"):
            return ""
        else:
            return "Filter: hostgroup_num_hosts > 0\n"

declare_filter(101, FilterText("hostgroupnameregex",    _("Hostgroup (Regex)"),        "hostgroup",    "hostgroup_name",      "hostgroup_regex",    "~~"),
                               _("Search field allowing regular expressions and partial matches on the names of hostgroups"))

declare_filter(102, FilterHostgroupVisibility("hostgroupvisibility", _("Empty Hostgroup Visibilitiy")),
                               _("You can enable this checkbox to show empty hostgroups"))

declare_filter(101, FilterText("servicegroupnameregex", _("Servicegroup (Regex)"),   "servicegroup", "servicegroup_name",   "servicegroup_regex", "~~"),
                          _("Search field allowing regular expression and partial matches"))

declare_filter(101, FilterText("servicegroupname", _("Servicegroup (enforced)"),   "servicegroup", "servicegroup_name",   "servicegroup_name", "="),
                          _("Exact match, used for linking"))

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
            return self.filterline % lqencode(current)
        else:
            return ""

declare_filter(110, FilterQueryDropdown("host_check_command", _("Host check command"), "host", \
        "GET commands\nCache: reload\nColumns: name\n", "Filter: host_check_command = %s\n"))
declare_filter(210, FilterQueryDropdown("check_command", _("Service check command"), "service", \
        "GET commands\nCache: reload\nColumns: name\n", "Filter: service_check_command = %s\n"))

class FilterServiceState(Filter):
    def __init__(self, name, title, prefix):
        Filter.__init__(self, name, title,
                "service", [ prefix + "st0", prefix + "st1", prefix + "st2", prefix + "st3", prefix + "stp" ], [])
        self.prefix = prefix

    def display(self):
        html.begin_checkbox_group()
        for var, text in [(self.prefix + "st0", _("OK")), (self.prefix + "st1", _("WARN")), \
                          (self.prefix + "st2", _("CRIT")), (self.prefix + "st3", _("UNKNOWN")),
                          (self.prefix + "stp", _("PEND"))]:
            html.checkbox(var, True, label=text)
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


class FilterStateType(FilterTristate):
    def __init__(self, info, column, title, deflt = -1):
        FilterTristate.__init__(self, column, title, info, None, deflt)

    def display(self):
        current = html.var(self.varname)
        html.begin_radio_group(horizontal = True)
        for value, text in [("0", _("SOFT")), ("1", _("HARD")), ("-1", _("(ignore)"))]:
            checked = current == value or (current in [ None, ""] and int(value) == self.deflt)
            html.radiobutton(self.varname, value, checked, text + " &nbsp; ")
        html.end_radio_group()

    def filter_code(self, infoname, positive):
        return "Filter: state_type = %d\n" % int(positive)

declare_filter(116, FilterStateType("host", "host_state_type",       _("Host state type")))
declare_filter(217, FilterStateType("service", "service_state_type", _("Service state type")))

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
declare_filter(233, FilterNagiosFlag("service", "service_active_checks_enabled",    _("Active checks enabled")))
declare_filter(234, FilterNagiosFlag("service", "service_notifications_enabled",    _("Notifications enabled")))
declare_filter(236, FilterNagiosFlag("service", "service_is_flapping",              _("Flapping")))
declare_filter(231, FilterNagiosFlag("service", "service_scheduled_downtime_depth", _("Service in downtime")))
declare_filter(132, FilterNagiosFlag("host",    "host_scheduled_downtime_depth",    _("Host in downtime")))
declare_filter(232, FilterNagiosExpression("service", "in_downtime",                _("Host/service in downtime"),
            "Filter: service_scheduled_downtime_depth > 0\nFilter: host_scheduled_downtime_depth > 0\nOr: 2\n",
            "Filter: service_scheduled_downtime_depth = 0\nFilter: host_scheduled_downtime_depth = 0\nAnd: 2\n"))

declare_filter(232, FilterNagiosExpression("host", "host_staleness",                _("Host is stale"),
            "Filter: host_staleness >= %0.2f\n" % config.staleness_threshold,
            "Filter: host_staleness < %0.2f\n" % config.staleness_threshold))
declare_filter(232, FilterNagiosExpression("service", "service_staleness",          _("Service is stale"),
            "Filter: service_staleness >= %0.2f\n" % config.staleness_threshold,
            "Filter: service_staleness < %0.2f\n" % config.staleness_threshold))

class FilterSite(Filter):
    def __init__(self, name, enforce):
        Filter.__init__(self, name, _("Site") + (enforce and _( " (enforced)") or ""), 'host', ["site"], [])
        self.enforce = enforce

    def visible(self):
        return config.is_multisite()

    def display(self):
        if not config.is_multisite():
            choices = [("", _("(local)"))]
        else:
            if self.enforce:
                choices = []
            else:
                choices = [("","")]
            for sitename, state in html.site_status.items():
                if state["state"] == "online":
                    choices.append((sitename, config.site(sitename)["alias"]))
        html.sorted_select("site", choices)

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

    def heading_info(self):
        current_value = html.var("site")
        if current_value:
            alias = config.site(current_value)["alias"]
            return alias

    def variable_settings(self, row):
        return [("site", row["site"])]

declare_filter(500, FilterSite("siteopt", False), _("Optional selection of a site"))
declare_filter(501, FilterSite("site",    True),  _("Selection of site is enforced, use this filter for joining"))

# name: internal id of filter
# title: user displayed title of the filter
# info: usually either "host" or "service"
# column: a livestatus column of type int or float
class FilterNumberRange(Filter): # type is int
    def __init__(self, name, title, info, column):
        self.column = column
        varnames = [ name + "_from", name + "_until" ]
        Filter.__init__(self, name, title, info, varnames, [])

    def display(self):
        html.write(_("From:") + "&nbsp;")
        html.text_input(self.htmlvars[0], style="width: 80px;")
        html.write(" &nbsp; " + _("To:") + "&nbsp;")
        html.text_input(self.htmlvars[1], style="width: 80px;")

    def filter(self, tablename):
        lql = ""
        for i, op in [ (0, ">="), (1, "<=") ]:
            try:
                txt = html.var(self.htmlvars[i])
                int(txt.strip())
                lql += "Filter: %s %s %s\n" % (self.column, op, txt.strip())
            except:
                pass
        return lql


declare_filter(232, FilterNumberRange("host_notif_number", _("Current Host Notification Number"), "host", "current_notification_number"))
declare_filter(232, FilterNumberRange("svc_notif_number", _("Current Service Notification Number"), "service", "current_notification_number"))

declare_filter(234, FilterNumberRange("host_num_services", _("Number of Services of the Host"), "host", "num_services"))



# Filter for setting time ranges, e.g. on last_state_change and last_check
class FilterTime(Filter):
    def __init__(self, info, name, title, column):
        self.column = column
        self.name = name
        self.ranges = [
           (86400,  _("days")),
           (3600,   _("hours")),
           (60,     _("min")),
           (1,      _("sec")),
        ]
        varnames = [ name + "_from", name + "_from_range",
                     name + "_until", name + "_until_range" ]

        Filter.__init__(self, name, title, info, varnames, [column])

    def double_height(self):
        return True

    def display(self):
        choices = [ (str(sec), title + " " + _("ago")) for sec, title in self.ranges ] + \
                  [ ("abs", _("Date (YYYY-MM-DD)")),
                    ("unix", _("UNIX timestamp")) ]

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
                elif rangename == "unix":
                    range.append(int(count))
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

    # def heading_info(self):
    #     return _("since the last couple of seconds")

declare_filter(250, FilterTime("service", "svc_last_state_change", _("Last service state change"), "service_last_state_change"))
declare_filter(251, FilterTime("service", "svc_last_check", _("Last service check"), "service_last_check"))

declare_filter(250, FilterTime("host", "host_last_state_change", _("Last host state change"), "host_last_state_change"))
declare_filter(251, FilterTime("host", "host_last_check", _("Last host check"), "host_last_check"))
declare_filter(253, FilterTime("comment", "comment_entry_time", _("Time of comment"), "comment_entry_time" ))
declare_filter(253, FilterTime("downtime", "downtime_entry_time", _("Time of Downtime"), "downtime_entry_time" ))
declare_filter(254, FilterText("downtime_comment", _("Downtime comment"), "downtime", "downtime_comment", "downtime_comment", "~"))
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
#                               filter          title              info       column           htmlvar
declare_filter(202, FilterUnicode("log_plugin_output",  _("Log: plugin output"), "log", "log_plugin_output", "log_plugin_output", "~~"))
declare_filter(203, FilterText("log_type",           _("Log: message type"), "log", "log_type", "log_type", "~~"))
declare_filter(204, FilterText("log_state_type",     _("Log: state type"), "log", "log_state_type", "log_state_type", "~~"))
declare_filter(260, FilterText("log_contact_name",   _("Log: contact name (exact match)"),  "log", "log_contact_name",  "log_contact_name",  "="),
                                                                                                  _("Exact match, used for linking"))
declare_filter(261, FilterText("log_contact_name_regex",   _("Log: contact name"),  "log", "log_contact_name",  "log_contact_name_regex",  "~~", negateable=True))

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

declare_filter(301, FilterText("downtime_id", _("Downtime ID"), "downtime", "downtime_id", "downtime_id", "="))

class FilterHostTags(Filter):
    def __init__(self):
        self.count = 3
        htmlvars = []
        for num in range(self.count):
            htmlvars += [ 'host_tag_%d_grp' % num, 'host_tag_%d_op' % num, 'host_tag_%d_val' % num ]

        Filter.__init__(self,
            name = 'host_tags',
            title = _('Host Tags'),
            info = 'host',
            htmlvars = htmlvars,
            link_columns = []
        )

    def display(self):
        groups = [ (e[0], e[1].lstrip("/") ) for e in config.wato_host_tags ]
        operators = [
            ("is", _("=")),
            ("isnot", _("&ne;")),
        ]

        # replace unicode strings, before writing out as "json"
        grouped = {}
        for entry in config.wato_host_tags:
            grouped.setdefault(entry[0], [["", ""]])

            for tag_entry in entry[2]:
                tag   = tag_entry[0]
                title = tag_entry[1]
                if tag is None:
                    tag = ''

                if type(title) == unicode:
                    title = title.encode("utf-8")
                grouped[entry[0]].append([tag, title])

        html.javascript('g_hosttag_groups = %r;' % grouped)
        html.write('<table>')
        for num in range(self.count):
            prefix = 'host_tag_%d' % num
            html.write('<tr><td>')
            html.sorted_select(prefix + '_grp',
                [("", "")] + groups,
                onchange = 'host_tag_update_value(\'%s\', this.value)' % prefix,
                attrs = {'style': 'width:129px'}
            )
            html.write('</td><td>')
            html.sorted_select(prefix + '_op', [("", "")] + operators,
                attrs = {'style': 'width:36px'})
            html.write('</td><td>')
            html.sorted_select(prefix + '_val',
                html.var(prefix + '_grp') and grouped[html.var(prefix + '_grp')] or [("", "")],
                attrs = {'style': 'width:129px'})
            html.write('</td></tr>')
        html.write('</table>')

    def hosttag_filter(self, negate, tag):
        return  'Filter: host_custom_variables %s TAGS (^|[ ])%s($|[ ])' % (negate and '!~' or '~', lqencode(tag))

    def filter(self, infoname):
        headers = []

        # Do not restrict to a certain number, because we'd like to link to this
        # via an URL, e.g. from the virtual host tree snapin
        num = 0
        while html.has_var('host_tag_%d_op' % num):
            prefix = 'host_tag_%d' % num
            op  = html.var(prefix + '_op')
            tag = html.var(prefix + '_val')

            if op:
                if tag:  # positive host tag
                    headers.append(self.hosttag_filter(op != "is", tag))
                else:
                    # empty host tag. Darn. We need to create a filter that excludes all other host tags
                    # of the group
                    group = html.var(prefix + '_grp')
                    grouptags = None
                    for entry in config.wato_host_tags:
                        if entry[0] == group:  # found our group
                            grouptags = [ x[0] for x in entry[2] if x[0] ]
                            break
                    if grouptags: # should never be empty, but maybe faked URL
                        for tag in grouptags:
                            headers.append(self.hosttag_filter(False, tag))
                        if len(grouptags) > 1:
                            headers.append("Or: %d" % len(grouptags))
                        if op == "is":
                            headers.append("Negate:")

            num += 1

        if headers:
            return '\n'.join(headers) + '\n'
        else:
            return ''

    def double_height(self):
        return True

declare_filter(302, FilterHostTags())


class FilterStarred(FilterTristate):
    def __init__(self, what):
        self.what = what
        icon = '<img class="icon inline" src="images/icon_starred.png"> '
        FilterTristate.__init__(self,
            name   = what + "_favorites",
            title  = icon  + (what == "host" and _("Favorite Hosts") or _("Favorite Services")),
            info   = what,
            column = what + "_favorite", # Column, not used
            deflt  = -1,
        )

    def filter(self, infoname):
        current = self.tristate_value()
        if current == -1:
            return ""
        elif current:
            aand, oor, eq = "And", "Or", "="
        else:
            aand, oor, eq = "Or", "And", "!="

        stars = config.load_stars()
        filters = ""
        count = 0
        if self.what == "host":
            for star in stars:
                if ";" in star:
                    continue
                filters += "Filter: host_name %s %s\n" % (eq, lqencode(star))
                count += 1
        else:
            for star in stars:
                if ";" not in star:
                    continue
                h, s = star.split(";")
                filters += "Filter: host_name %s %s\n" % (eq, lqencode(h))
                filters += "Filter: service_description %s %s\n" % (eq, lqencode(s))
                filters += "%s: 2\n" % aand
                count += 1

        # No starred object and show only starred -> show nothing
        if count == 0 and current:
            return "Filter: host_state = -4612\n"

        # no starred object and show unstarred -> show everything
        elif count == 0:
            return ""

        filters += "%s: %d\n" % (oor, count)
        return filters

declare_filter(501, FilterStarred("host"))
declare_filter(501, FilterStarred("service"))
