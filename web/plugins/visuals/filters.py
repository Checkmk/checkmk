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

import sites


# Filters for substring search, displaying a text input field
class FilterText(Filter):
    def __init__(self, name, title, info, column, htmlvar, op, negateable=False, show_heading=True):
        htmlvars = [htmlvar]
        if negateable:
            htmlvars.append("neg_" + htmlvar)
        link_columns = column if isinstance(column, list) else [column]
        Filter.__init__(self, name, title, info, htmlvars, link_columns)
        self.op = op
        self.column = column
        self.negateable = negateable
        self._show_heading = show_heading

    def _current_value(self):
        htmlvar = self.htmlvars[0]
        return html.var(htmlvar, "")

    def display(self):
        current_value = self._current_value()
        html.text_input(self.htmlvars[0], current_value, self.negateable and 'neg' or '')
        if self.negateable:
            html.open_nobr()
            html.checkbox(self.htmlvars[1], False, label=_("negate"))
            html.close_nobr()

    def filter(self, infoname):
        current_value = self._current_value()

        if self.negateable and html.get_checkbox(self.htmlvars[1]):
            negate = "!"
        else:
            negate = ""

        if current_value:
            if type(current_value) == unicode:
                current_value = current_value.encode("utf-8")
            return "Filter: %s %s%s %s\n" % (self.column, negate, self.op, lqencode(current_value))
        else:
            return ""

    def variable_settings(self, row):
        return [ (self.htmlvars[0], row[self.column]) ]

    def heading_info(self):
        if self._show_heading:
            return self._current_value()


class FilterUnicode(FilterText):
    def __init__(self, *args):
        FilterText.__init__(self, *args)

    def _current_value(self):
        htmlvar = self.htmlvars[0]
        return html.get_unicode_input(htmlvar, "")

class FilterHostnameOrAlias(FilterUnicode):
    def __init__(self, *args):
        FilterUnicode.__init__(self, *args)

    def filter(self, infoname):
        current_value = self._current_value()

        if self.negateable and html.get_checkbox(self.htmlvars[1]):
            negate = "!"
        else:
            negate = ""

        if current_value:
            if type(current_value) == unicode:
                current_value = current_value.encode("utf-8")
            return "Filter: host_name %s%s %s\nFilter: alias %s%s %s\nOr: 2\n" % ((negate, self.op, lqencode(current_value)) * 2)
        else:
            return ""

#                               filter          title              info       column           htmlvar
declare_filter(100, FilterText("hostregex",    _("Hostname"),        "host",    "host_name",      "host_regex",    "~~" , True),
                          _("Search field allowing regular expressions and partial matches"))

declare_filter(101, FilterText("host",    _("Hostname (exact match)"),             "host",    "host_name",          "host",    "=", True),
                          _("Exact match, used for linking"))

declare_filter(102, FilterUnicode("hostalias",   _("Hostalias"),      "host",     "host_alias",      "hostalias",    "~~", True),
                          _("Search field allowing regular expressions and partial matches"))

declare_filter(200, FilterUnicode("serviceregex", _("Service"),         "service", "service_description",   "service_regex", "~~", True),
                          _("Search field allowing regular expressions and partial matches"))

declare_filter(201, FilterUnicode("service", _("Service (exact match)"),              "service", "service_description",   "service", "="),
                          _("Exact match, used for linking"))

declare_filter(202, FilterUnicode("service_display_name", _("Service alternative display name"),   "service", "service_display_name",   "service_display_name", "~~"),
                          _("Alternative display name of the service, regex match"))

declare_filter(202, FilterUnicode("output",  _("Status detail"), "service", "service_plugin_output", "service_output", "~~", True))

declare_filter(102, FilterHostnameOrAlias("hostnameoralias",   _("Hostname or Alias"), "host", ["host_alias", "host_name"],  "hostnameoralias", "~~", False),
                          _("Search field allowing regular expressions and partial matches"))


class FilterIPAddress(Filter):
    def __init__(self, what):
        self._what = what

        if what == "primary":
            varname = "host_address"
            title = _("Host address (Primary)")
            link_columns = ["host_address"]
        elif what == "ipv4":
            varname = "host_ipv4_address"
            title = _("Host address (IPv4)")
            link_columns = []
        else:
            varname = "host_ipv6_address"
            title = _("Host address (IPv6)")
            link_columns = []

        # name, title, info, htmlvars, link_columns
        Filter.__init__(self, varname, title, "host", [varname, varname+"_prefix"], link_columns)

    def display(self):
        html.text_input(self.htmlvars[0])
        html.br()
        html.br()
        html.begin_radio_group()
        html.radiobutton(self.htmlvars[1], "yes", True, _("Prefix match"))
        html.radiobutton(self.htmlvars[1], "no", False, _("Exact match"))
        html.end_radio_group()

    def double_height(self):
        return True

    def filter(self, infoname):
        address = html.var(self.htmlvars[0])
        if address:
            op = "="
            if html.var(self.htmlvars[1]) == "yes":
                op = "~"
                address = "^" + lqencode(address)
            else:
                address = lqencode(address)

            if self._what == "primary":
                return "Filter: host_address %s %s\n" % (op, address)
            else:
                varname = "ADDRESS_4" if self._what == "ipv4" else "ADDRESS_6"
                return "Filter: host_custom_variables %s %s %s\n" % (op, varname, address)
        else:
            return ""

    def variable_settings(self, row):
        return [ (self.htmlvars[0], row["host_address"]) ]

    def heading_info(self):
        return html.var(self.htmlvars[0])


declare_filter(102, FilterIPAddress(what="primary"))
declare_filter(102, FilterIPAddress(what="ipv4"))
declare_filter(102, FilterIPAddress(what="ipv6"))


class FilterAddressFamily(Filter):
    def __init__(self):
        Filter.__init__(self, name="address_family", title=_("Host address family (Primary)"),
                        info="host", htmlvars=[ "address_family" ], link_columns=[])

    def display(self):
        html.begin_radio_group()
        html.radiobutton("address_family", "4", False, _("IPv4"))
        html.radiobutton("address_family", "6", False, _("IPv6"))
        html.radiobutton("address_family", "both", True, _("Both"))
        html.end_radio_group()

    def filter(self, infoname):
        family = html.var("address_family", "both")
        if family == "both":
            return ""
        else:
            return "Filter: host_custom_variables = ADDRESS_FAMILY %s\n" % lqencode(family)


declare_filter(103, FilterAddressFamily())

class FilterAddressFamilies(Filter):
    def __init__(self):
        Filter.__init__(self,
            name="address_families", title=_("Host address families"),
            info="host", htmlvars=[ "address_families", ], link_columns=[])

    def display(self):
        html.begin_radio_group()
        html.radiobutton("address_families", "4", False, label="v4")
        html.radiobutton("address_families", "6", False, label="v6")
        html.radiobutton("address_families", "both", False, label=_("both"))
        html.radiobutton("address_families", "4_only", False, label=_("only v4"))
        html.radiobutton("address_families", "6_only", False, label=_("only v6"))
        html.radiobutton("address_families", "", True, label=_("(ignore)"))
        html.end_radio_group()

    def filter(self, infoname):
        family = html.var("address_families")
        if not family:
            return ""

        elif family == "both":
            return "Filter: host_custom_variables ~ TAGS (^|[ ])ip-v4($|[ ])\n" \
                   "Filter: host_custom_variables ~ TAGS (^|[ ])ip-v6($|[ ])\n"
        else:
            if family[0] == "4":
                tag = "ip-v4"
            elif family[0] == "6":
                tag = "ip-v6"
            filt = "Filter: host_custom_variables ~ TAGS (^|[ ])%s($|[ ])\n" % lqencode(tag)

            if family.endswith("_only"):
                if family[0] == "4":
                    tag = "ip-v6"
                elif family[0] == "6":
                    tag = "ip-v4"
                filt += "Filter: host_custom_variables !~ TAGS (^|[ ])%s($|[ ])\n" % lqencode(tag)

            return filt


declare_filter(103, FilterAddressFamilies())

# Helper that retrieves the list of host/service/contactgroups via Livestatus
# use alias by default but fallback to name if no alias defined
def all_groups(what):
    groups = dict(sites.live().query("GET %sgroups\nCache: reload\nColumns: name alias\n" % what))
    return [ (name, groups[name] or name) for name in groups.keys() ]

class FilterMultigroup(Filter):
    def __init__(self, what, title, negateable=False):
        self.htmlvar = what + "groups"
        htmlvars = [ self.htmlvar ]
        self.negateable = negateable
        if self.negateable:
            htmlvars.append("neg_" + self.htmlvar)
        Filter.__init__(self, self.htmlvar, # name
                              title,
                              what,        # info, e.g. "service"
                              htmlvars,
                              [])          # no link info needed
        self.what = what

    def double_height(self):
        return True

    def valuespec(self):
        return DualListChoice(
            choices = all_groups(self.what),
            rows=3 if self.negateable else 4,
            enlarge_active=True
        )

    def selection(self):
        current = html.var(self.htmlvar, "").strip().split("|")
        if current == ['']:
            return []
        else:
            return current

    def display(self):
        html.open_div(class_="multigroup")
        self.valuespec().render_input(self.htmlvar, self.selection())
        if self.negateable:
            html.open_nobr()
            html.checkbox(self.htmlvars[1], False, label=_("negate"))
            html.close_nobr()
        html.close_div()

    def filter(self, infoname):
        current = self.selection()
        if len(current) == 0:
            return "" # No group selected = all groups selected, filter unused
        # not (A or B) => (not A) and (not B)
        if self.negateable and html.get_checkbox(self.htmlvars[1]):
            negate = "!"
            op = "And"
        else:
            negate  = ""
            op = "Or"
        filters = ""
        for group in current:
            filters += "Filter: %s_groups %s>= %s\n" % (self.what, negate, lqencode(group))
        if len(current) > 1:
            filters += "%s: %d\n" % (op, len(current))
        return filters


# Selection of a host/service(-contact) group as an attribute of a host or service
class FilterGroupCombo(Filter):
    def __init__(self, what, title, enforce):
        self.enforce = enforce
        self.prefix = "opt" if not self.enforce else ""
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
        html.dropdown(self.htmlvars[0], choices, sorted=True)
        if not self.enforce:
            html.open_nobr()
            html.checkbox(self.htmlvars[1], False, label=_("negate"))
            html.close_nobr()

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
            current_value = sites.live().query_value("GET %sgroups\nCache: reload\nColumns: name\nLimit: 1\n" % table, None)

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
            alias = sites.live().query_value("GET %sgroups\nCache: reload\nColumns: alias\nFilter: name = %s\n" %
                (table, lqencode(current_value)), current_value)
            return alias

declare_filter(104, FilterGroupCombo("host",            _("Host is in Group"),        False), _("Optional selection of host group"))
declare_filter(105, FilterMultigroup("host",            _("Several Host Groups"),     True),  _("Selection of multiple host groups"))
declare_filter(204, FilterGroupCombo("service",         _("Service is in Group"),     False), _("Optional selection of service group"))
declare_filter(205, FilterGroupCombo("service",         _("Servicegroup (enforced)"), True),  _("Dropdown list, selection of service group is <b>enforced</b>"))
declare_filter(205, FilterMultigroup("service",         _("Several Service Groups"),  True),  _("Selection of multiple service groups"))

declare_filter(106, FilterGroupCombo("host_contact",    _("Host Contact Group"),    False), _("Optional selection of host contact group"))
declare_filter(206, FilterGroupCombo("service_contact", _("Service Contact Group"), False), _("Optional selection of service contact group"))

declare_filter(107, FilterText("host_ctc",    _("Host Contact"),    "host",    "host_contacts",    "host_ctc",    ">="))
declare_filter(207, FilterText("service_ctc", _("Service Contact"), "service", "service_contacts", "service_ctc", ">="))


# Selection of one group to be used in the info "hostgroup" or "servicegroup".
class FilterGroupSelection(Filter):
    def __init__(self, infoname, title):
        Filter.__init__(self, name=infoname, title=title, info=infoname, htmlvars=[infoname], link_columns=[])
        self.what = infoname

    def display(self):
        choices = all_groups(self.what[:-5]) # chop off "group", leaves host or service
        html.dropdown(self.htmlvars[0], choices, sorted=True)

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

declare_filter(101, FilterText("servicegroupnameregex", _("Servicegroup (Regex)"),   "servicegroup", "servicegroup_name",   "servicegroup_regex", "~~", negateable=True),
                          _("Search field allowing regular expression and partial matches"))

declare_filter(101, FilterText("servicegroupname", _("Servicegroup (enforced)"),   "servicegroup", "servicegroup_name",   "servicegroup_name", "="),
                          _("Exact match, used for linking"))

class FilterQueryDropdown(Filter):
    def __init__(self, name, title, info, query, filterline):
        Filter.__init__(self, name, title, info, [ name ], [])
        self.query = query
        self.filterline = filterline

    def display(self):
        selection = sites.live().query_column_unique(self.query)
        html.dropdown(self.name, [("", "")] + [(x,x) for x in selection], sorted=True)

    def filter(self, infoname):
        current = html.var(self.name)
        if current:
            return self.filterline % lqencode(current)
        else:
            return ""

declare_filter(110, FilterQueryDropdown("host_check_command", _("Host check command"), "host", \
        "GET commands\nCache: reload\nColumns: name\n", "Filter: host_check_command ~ ^%s(!.*)?\n"))
declare_filter(210, FilterQueryDropdown("check_command", _("Service check command"), "service", \
        "GET commands\nCache: reload\nColumns: name\n", "Filter: service_check_command ~ ^%s(!.*)?$\n"))

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

class FilterHostsHavingServiceProblems(Filter):
    def __init__(self):
        Filter.__init__(self, "hosts_having_service_problems",
            _("Hosts having certain service problems"), "host",
            ["hosts_having_services_warn", "hosts_having_services_crit",
             "hosts_having_services_pending", "hosts_having_services_unknown"], [])

    def display(self):
        html.begin_checkbox_group()
        for var, text in [
            ("warn",    _("WARN")),
            ("crit",    _("CRIT")),
            ("pending", _("PEND")),
            ("unknown", _("UNKNOWN")), ]:
            html.checkbox("hosts_having_services_%s" % var, True, label=text)
        html.end_checkbox_group()

    def filter(self, infoname):
        headers = []
        for var in [ "warn", "crit", "pending", "unknown" ]:
            if html.get_checkbox("hosts_having_services_%s" % var) == True:
                headers.append("Filter: host_num_services_%s > 0\n" % var)

        len_headers = len(headers)
        if len_headers > 0:
            headers.append("Or: %d\n" % len_headers)
            return "".join(headers)
        else:
            return ""

declare_filter(120, FilterHostsHavingServiceProblems())

class FilterTristate(Filter):
    def __init__(self, name, title, info, column, deflt = -1):
        self.column = column
        self.varname = "is_" + name
        Filter.__init__(self, name, title, info, [ self.varname ], [])
        self.deflt = deflt

    def display(self):
        current = html.var(self.varname)
        html.begin_radio_group(horizontal=True)
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

    def filter_code(self, infoname, positive):
        raise NotImplementedError()


class FilterStateType(FilterTristate):
    def __init__(self, info, column, title, deflt = -1):
        FilterTristate.__init__(self, column, title, info, None, deflt)

    def display(self):
        current = html.var(self.varname)
        html.begin_radio_group(horizontal=True)
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

declare_filter(130, FilterNagiosFlag("host",    "host_in_notification_period",      _("Host in notification period")))
declare_filter(130, FilterNagiosFlag("host",    "host_in_service_period",           _("Host in service period")))
declare_filter(131, FilterNagiosFlag("host",    "host_acknowledged",                _("Host problem has been acknowledged")))
declare_filter(132, FilterNagiosFlag("host",    "host_active_checks_enabled",       _("Host active checks enabled")))
declare_filter(133, FilterNagiosFlag("host",    "host_notifications_enabled",       _("Host notifications enabled")))
declare_filter(230, FilterNagiosFlag("service", "service_acknowledged",             _("Problem acknowledged")))
declare_filter(231, FilterNagiosFlag("service", "service_in_notification_period",   _("Service in notification period")))
declare_filter(231, FilterNagiosFlag("service", "service_in_service_period",        _("Service in service period")))
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
        html.dropdown("site", self._choices())


    def _choices(self):
        if self.enforce:
            choices = []
        else:
            choices = [("","")]

        for sitename, state in sites.states().items():
            if state["state"] == "online":
                choices.append((sitename, config.site(sitename)["alias"]))

        return sorted(choices, key=lambda a: a[1].lower())


    def heading_info(self):
        current_value = html.var("site")
        if current_value:
            alias = config.site(current_value)["alias"]
            return alias


    def variable_settings(self, row):
        return [("site", row["site"])]



def declare_site_filters():
    if cmk.is_managed_edition():
        cls = FilterCMESite
    else:
        cls = FilterSite

    declare_filter(500, cls("siteopt", False),
                   _("Optional selection of a site"))
    declare_filter(501, cls("site",    True),
                   _("Selection of site is enforced, use this filter for joining"))

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
        html.write_text(_("From:") + "&nbsp;")
        html.text_input(self.htmlvars[0], style="width: 80px;")
        html.write_text(" &nbsp; " + _("To:") + "&nbsp;")
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

        html.open_table(class_="filtertime")
        for what, whatname in [
            ( "from", _("From") ),
            ( "until", _("Until") ) ]:
            varprefix = self.name + "_" + what
            html.open_tr()
            html.open_td()
            html.write("%s:" % whatname)
            html.close_td()
            html.open_td()
            html.text_input(varprefix, style="width: 116px;")
            html.close_td()
            html.open_td()
            html.dropdown(varprefix + "_range", choices, deflt="3600")
            html.close_td()
            html.close_tr()
        html.close_table()


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
        return self._get_time_range_of("from"), \
               self._get_time_range_of("until")


    def _get_time_range_of(self, what):
        varprefix = self.name + "_" + what
        count = html.var(varprefix)
        if count == "":
            return None

        rangename = html.var(varprefix + "_range")
        if rangename == "abs":
            try:
                return time.mktime(time.strptime(count, "%Y-%m-%d"))
            except:
                html.add_user_error(varprefix, _("Please enter the date in the format YYYY-MM-DD."))
                return None

        elif rangename == "unix":
            return int(count)

        try:
            count = int(count)
            secs = count * int(rangename)
            return int(time.time()) - secs
        except:
            html.set_var(varprefix, "")
            return None



declare_filter(250, FilterTime("service", "svc_last_state_change", _("Last service state change"), "service_last_state_change"))
declare_filter(251, FilterTime("service", "svc_last_check", _("Last service check"), "service_last_check"))

declare_filter(250, FilterTime("host", "host_last_state_change", _("Last host state change"), "host_last_state_change"))
declare_filter(251, FilterTime("host", "host_last_check", _("Last host check"), "host_last_check"))
declare_filter(253, FilterTime("comment", "comment_entry_time", _("Time of comment"), "comment_entry_time" ))

declare_filter(258, FilterText("comment_comment", _("Comment"), "comment", "comment_comment", "comment_comment", "~~" , True))
declare_filter(259, FilterText("comment_author", _("Author comment"), "comment", "comment_author", "comment_author", "~~" , True))

declare_filter(253, FilterTime("downtime", "downtime_entry_time", _("Time when downtime was created"), "downtime_entry_time" ))
declare_filter(254, FilterText("downtime_comment", _("Downtime comment"), "downtime", "downtime_comment", "downtime_comment", "~"))
declare_filter(255, FilterTime("downtime", "downtime_start_time", _("Start of downtime"), "downtime_start_time" ))
declare_filter(256, FilterText("downtime_author", _("Downtime author"), "downtime", "downtime_author", "downtime_author", "~"))

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
# ALERT HANDLERS 8

class FilterLogClass(Filter):
    def __init__(self):
        self.log_classes = [
            (0, _("Informational")),
            (1, _("Alerts")),
            (2, _("Program")),
            (3, _("Notifications")),
            (4, _("Passive checks")),
            (5, _("Commands")),
            (6, _("States")),
            (8, _("Alert Handlers")) ]

        Filter.__init__(self, "log_class", _("Logentry class"),
                "log", [ "logclass_filled" ] + [ "logclass%d" % l for l, c in self.log_classes ], [])

    def double_height(self):
        return True

    def display(self):
        html.hidden_field("logclass_filled", "1", add_var=True)
        html.open_table(cellspacing=0, cellpadding=0)
        if config.filter_columns == 1:
            num_cols = 4
        else:
            num_cols = 2
        col = 1
        for l, c in self.log_classes:
            if col == 1:
                html.open_tr()
            html.open_td()
            html.checkbox("logclass%d" % l, True)
            html.write(c)
            html.close_td()
            if col == num_cols:
                html.close_tr()
                col = 1
            else:
                col += 1
        if col < num_cols:
            html.open_td()
            html.close_td()
            html.close_tr()
        html.close_table()

    def filter(self, infoname):
        headers = []
        for l, c in self.log_classes:
            if html.get_checkbox("logclass%d" % l) != False:
                headers.append("Filter: class = %d\n" % l)

        if len(headers) == 0:
            return "Limit: 0\n" # no class allowed
        else:
            return "".join(headers) + ("Or: %d\n" % len(headers))

declare_filter(255, FilterLogClass())
#                               filter          title              info       column           htmlvar
declare_filter(202, FilterUnicode("log_plugin_output",  _("Log: plugin output"), "log", "log_plugin_output", "log_plugin_output", "~~"))
declare_filter(203, FilterText("log_type",           _("Log: message type"), "log", "log_type", "log_type", "~~", show_heading=False))
declare_filter(204, FilterText("log_state_type",     _("Log: state type"), "log", "log_state_type", "log_state_type", "~~"))
declare_filter(260, FilterText("log_contact_name",   _("Log: contact name (exact match)"),  "log", "log_contact_name",  "log_contact_name",  "="),
                                                                                                  _("Exact match, used for linking"))
declare_filter(261, FilterText("log_contact_name_regex",   _("Log: contact name"),  "log", "log_contact_name",  "log_contact_name_regex",  "~~", negateable=True))
declare_filter(262, FilterText("log_command_name_regex",  _("Log: command"),  "log", "log_command_name",  "log_command_name_regex",  "~~", negateable=True))

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
        html.open_table(class_="alertstatefilter")
        html.open_tr()
        html.open_td()
        html.begin_checkbox_group()
        for varsuffix, what, state, text in self._items:
            if state == 0:
                title = _("Host") if what == "host" else _("Service")
                html.u("%s:" % title)
                html.close_td()
                html.open_td()
            html.write_text("&nbsp; ")
            html.checkbox("logst_" + varsuffix, True, label=text)
            if not html.mobile:
                html.br()
            if varsuffix == "h2":
                html.close_td()
                html.open_td()
        html.end_checkbox_group()
        html.close_td()
        html.close_tr()
        html.close_table()

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

class NotificationPhaseFilter(FilterTristate):
    def __init__(self):
	FilterTristate.__init__(self, "log_notification_phase", _("Notification phase"), "log", "log_command_name", -1)

    def double_height(self):
        return True

    def display(self):
        current = html.var(self.varname)
        html.begin_radio_group(horizontal=False)
        for value, text in [
            ("-1", _("Show all phases of notifications")),
            ("1",  _("Show just preliminary notifications")),
            ("0",  _("Show just end-user-notifications")),
        ]:
            checked = current == value or (current in [ None, ""] and int(value) == self.deflt)
            html.radiobutton(self.varname, value, checked, text + " &nbsp; ")
            html.br()
        html.end_radio_group()

    def filter_code(self, infoname, positive):
        # Note: this filter also has to work for entries that are no notification.
        # In that case the filter is passive and lets everything through
        if positive:
            return "Filter: %s = check-mk-notify\nFilter: %s =\nOr: 2\n" % (self.column, self.column)
        else:
            return "Filter: %s != check-mk-notify\n" % self.column


declare_filter(271, NotificationPhaseFilter())

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

    def filter_code(self, infoname, positive):
        pass


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
            ("is", "="),
            ("isnot", u"≠"),
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

                # if type(title) == unicode:
                #     title = title.encode("utf-8")
                grouped[entry[0]].append([tag, title])

        html.javascript('g_hosttag_groups = %s;' % json.dumps(grouped))
        html.open_table()
        for num in range(self.count):
            prefix = 'host_tag_%d' % num
            html.open_tr()
            html.open_td()
            html.dropdown(prefix + '_grp', [("", "")] + groups,
                          onchange = 'host_tag_update_value(\'%s\', this.value)' % prefix,
                          style='width:129px', sorted=True)
            html.close_td()
            html.open_td()
            html.dropdown(prefix + '_op', [("", "")] + operators, style="width:36px", sorted=True)
            html.close_td()
            html.open_td()
            choices = grouped[html.var(prefix + '_grp')] if html.var(prefix + '_grp') else [("", "")]
            html.dropdown(prefix + '_val', choices, style="width:129px", sorted=True)
            html.close_td()
            html.close_tr()
        html.close_table()

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



class FilterHostAuxTags(Filter):
    def __init__(self):
        self.count  = 3
        self.prefix = 'host_auxtags'
        htmlvars    = [ "%s_%d" % (self.prefix, num)
                        for num in range(self.count) ]

        Filter.__init__(self,
            name     = 'host_auxtags',
            title    = _('Host Auxiliary Tags'),
            info     = 'host',
            htmlvars = htmlvars,
            link_columns = []
        )

        self.auxtags = config.wato_aux_tags


    def display(self):
        selection = []
        for num in range(self.count):
            html.dropdown('%s_%d' % (self.prefix, num), [("", "")] + self.auxtags, sorted=True)


    def host_auxtags_filter(self, tag):
        return "Filter: custom_variables ~ TAGS (^|[ ])%s($|[ ])" % lqencode(tag)


    def filter(self, infoname):
        headers = []

        # Do not restrict to a certain number, because we'd like to link to this
        # via an URL, e.g. from the virtual host tree snapin
        num = 0
        while html.has_var( '%s_%d' % (self.prefix, num) ):
            this_tag = html.var( '%s_%d' % (self.prefix, num) )
            if this_tag:
                headers.append( self.host_auxtags_filter( this_tag ) )
            num += 1

        if headers:
            return '\n'.join(headers) + '\n'
        else:
            return ''


    def double_height(self):
        return True



declare_filter(302, FilterHostAuxTags())



# choices = [ (value, "readable"), .. ]
class FilterECServiceLevelRange(Filter):
    def __init__(self, name, title, info):
        self.lower_bound_varname = "%s_lower" % name
        self.upper_bound_varname = "%s_upper" % name

        Filter.__init__( self, name, title, info,
                         [ self.lower_bound_varname,
                           self.upper_bound_varname, ], [] )


    def _prepare_choices(self):
        choices = config.mkeventd_service_levels[:]
        choices.sort()
        return map( lambda x: ( str(x[0]), "%s - %s" % (x[0], x[1]) ), choices )


    def display(self):
        selection = [ ("", "") ] + self._prepare_choices()
        html.write_text("From")
        html.dropdown(self.lower_bound_varname, selection)
        html.write_text("To")
        html.select(self.upper_bound_varname, selection)


    def filter(self, infoname):
        lower_bound = html.var(self.lower_bound_varname)
        upper_bound = html.var(self.upper_bound_varname)

        if lower_bound and upper_bound:
            match_func = lambda val: int(lower_bound) <= val <= int(upper_bound)
        elif lower_bound and not upper_bound:
            match_func = lambda val: int(lower_bound) <= val
        elif not lower_bound and upper_bound:
            match_func = lambda val: val <= int(upper_bound)
        else:
            match_func = None

        if match_func is not None:
            filterline = "Filter: %s_custom_variable_names >= EC_SL\n" % self.info

            filterline_values = []
            for value, readable in config.mkeventd_service_levels:
                if match_func(value):
                    filterline_values.append( "Filter: %s_custom_variable_values >= %s" % \
                                              (self.info, lqencode(str(value))) )

            filterline += "%s\n" % "\n".join( filterline_values )

            len_filterline_values = len(filterline_values)
            if len_filterline_values > 1:
                filterline += "Or: %d\n" % len_filterline_values

            return filterline

        else:
            return ""


    def double_height(self):
        return True



declare_filter(310, FilterECServiceLevelRange(
        "svc_service_level", _("Service service level"), "service"))


declare_filter(310, FilterECServiceLevelRange(
        "hst_service_level", _("Host service level"), "host"))



class FilterStarred(FilterTristate):
    def __init__(self, what):
        self.what = what

        title = html.render_icon("starred", cssclass="inline") \
                + (what == "host" and _("Favorite Hosts") or _("Favorite Services"))

        FilterTristate.__init__(self,
            name   = what + "_favorites",
            title  = HTML(title),
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

        stars = config.user.load_stars()
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

    def filter_code(self, infoname, positive):
        pass


declare_filter(501, FilterStarred("host"))
declare_filter(501, FilterStarred("service"))

class FilterDiscoveryState(Filter):
    def __init__(self):
        self.__options = [
            ("discovery_state_ignored",     _("Hidden")),
            ("discovery_state_vanished",    _("Vanished")),
            ("discovery_state_unmonitored", _("New")),
        ]
        Filter.__init__(self, "discovery_state", _("Discovery state"), "discovery_state",
                [ o[0] for o in self.__options ], [])
        self.__varname = "discovery_state"


    def display(self):
        html.begin_checkbox_group()
        for varname, title in self.__options:
            html.checkbox(varname, True, label=title)
        html.end_checkbox_group()


    def value(self):
        val = {}
        for varname in self.htmlvars:
            value = html.get_checkbox(varname)
            if value == None:
                value = True # Default setting for filter: all checked!
            val[varname] = value
        return val


    def filter(self, infoname):
        return ""


    def filter_table(self, rows):
        new_rows = []
        filter_options = self.value()
        for row in rows:
            if filter_options["discovery_state_" + row["discovery_state"]]:
                new_rows.append(row)
        return new_rows


declare_filter(601, FilterDiscoveryState())
