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

import re
import time
import livestatus
import json

import cmk

import cmk.gui.config as config
import cmk.gui.sites as sites
import cmk.gui.bi as bi
import cmk.gui.mkeventd as mkeventd
from cmk.gui.htmllib import HTML
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.valuespec import (DualListChoice)

if cmk.is_managed_edition():
    import cmk.gui.cme.plugins.visuals.managed

from . import (
    declare_filter,
    Filter,
    FilterUnicodeFilter,
    FilterTristate,
    FilterTime,
    FilterSite,
)

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
            return "Filter: %s %s%s %s\n" % (self.column, negate, self.op, livestatus.lqencode(current_value))
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
            return "Filter: host_name %s%s %s\nFilter: alias %s%s %s\nOr: 2\n" % ((negate, self.op, livestatus.lqencode(current_value)) * 2)
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
                address = "^" + livestatus.lqencode(address)
            else:
                address = livestatus.lqencode(address)

            if self._what == "primary":
                return "Filter: host_address %s %s\n" % (op, address)

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
            return "Filter: host_custom_variables = ADDRESS_FAMILY %s\n" % livestatus.lqencode(family)


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
            filt = "Filter: host_custom_variables ~ TAGS (^|[ ])%s($|[ ])\n" % livestatus.lqencode(tag)

            if family.endswith("_only"):
                if family[0] == "4":
                    tag = "ip-v6"
                elif family[0] == "6":
                    tag = "ip-v4"
                filt += "Filter: host_custom_variables !~ TAGS (^|[ ])%s($|[ ])\n" % livestatus.lqencode(tag)

            return filt


declare_filter(103, FilterAddressFamilies())

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
            choices = sites.all_groups(self.what),
            rows=3 if self.negateable else 4,
            enlarge_active=True
        )

    def selection(self):
        current = html.var(self.htmlvar, "").strip().split("|")
        if current == ['']:
            return []
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
            filters += "Filter: %s_groups %s>= %s\n" % (self.what, negate, livestatus.lqencode(group))
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
        choices = sites.all_groups(self.what.split("_")[-1])
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
        return "Filter: %s %s>= %s\n" % (col, negate, livestatus.lqencode(current_value))

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
                (table, livestatus.lqencode(current_value)), current_value)
            return alias

declare_filter(104, FilterGroupCombo("host",            _("Host is in Group"),        False), _("Optional selection of host group"))
declare_filter(105, FilterMultigroup("host",            _("Several Host Groups"),     True),  _("Selection of multiple host groups"))
declare_filter(204, FilterGroupCombo("service",         _("Service is in Group"),     False), _("Optional selection of service group"))
declare_filter(205, FilterGroupCombo("service",         _("Servicegroup (enforced)"), True),  _("Dropdown list, selection of service group is <b>enforced</b>"))
declare_filter(205, FilterMultigroup("service",         _("Several Service Groups"),  True),  _("Selection of multiple service groups"))

declare_filter(106, FilterGroupCombo("host_contact",    _("Host Contact Group"),    False), _("Optional selection of host contact group"))
declare_filter(206, FilterGroupCombo("service_contact", _("Service Contact Group"), False), _("Optional selection of service contact group"))

declare_filter(107, FilterText("host_ctc",          _("Host Contact"),            "host",    "host_contacts",    "host_ctc",          ">="))
declare_filter(107, FilterText("host_ctc_regex",    _("Host Contact (Regex)"),    "host",    "host_contacts",    "host_ctc_regex",    "~~"))
declare_filter(207, FilterText("service_ctc",       _("Service Contact"),         "service", "service_contacts", "service_ctc",       ">="))
declare_filter(207, FilterText("service_ctc_regex", _("Service Contact (Regex)"), "service", "service_contacts", "service_ctc_regex", "~~"))


# Selection of one group to be used in the info "hostgroup" or "servicegroup".
class FilterGroupSelection(Filter):
    def __init__(self, infoname, title):
        Filter.__init__(self, name=infoname, title=title, info=infoname, htmlvars=[infoname], link_columns=[])
        self.what = infoname

    def display(self):
        choices = sites.all_groups(self.what[:-5]) # chop off "group", leaves host or service
        html.dropdown(self.htmlvars[0], choices, sorted=True)

    def current_value(self):
        return html.var(self.htmlvars[0])

    def filter(self, infoname):
        current_value = self.current_value()
        if current_value:
            return "Filter: %s_name = %s\n" % (self.what, livestatus.lqencode(current_value))
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
            return self.filterline % livestatus.lqencode(current)
        return ""

declare_filter(110, FilterQueryDropdown("host_check_command", _("Host check command"), "host", \
        "GET commands\nCache: reload\nColumns: name\n", "Filter: host_check_command ~ ^%s(!.*)?\n"))
declare_filter(210, FilterQueryDropdown("check_command", _("Service check command"), "service", \
        "GET commands\nCache: reload\nColumns: name\n", "Filter: service_check_command ~ ^%s(!.*)?$\n"))

class FilterServiceState(Filter):
    def __init__(self, name, title, prefix):
        Filter.__init__(self, name, title,
                "service", [ prefix + "_filled", prefix + "st0", prefix + "st1", prefix + "st2", prefix + "st3", prefix + "stp" ], [])
        self.prefix = prefix

    def display(self):
        html.begin_checkbox_group()
        html.hidden_field(self.prefix + "_filled", "1", add_var=True)
        for var, text in [(self.prefix + "st0", _("OK")), (self.prefix + "st1", _("WARN")), \
                          (self.prefix + "st2", _("CRIT")), (self.prefix + "st3", _("UNKNOWN")),
                          (self.prefix + "stp", _("PEND"))]:
            html.checkbox(var, True if not self._filter_used() else False, label=text)
        html.end_checkbox_group()

    def _filter_used(self):
        return any([ html.has_var(v) for v in self.htmlvars ])

    def filter(self, infoname):
        headers = []
        for i in [0,1,2,3]:
            check_result = html.get_checkbox(self.prefix + "st%d" % i)

            # When a view is displayed e.g. as a dashlet the unchecked checkboxes are not set in
            # the HTML variables while the form was not interactively submitted. In this case the
            # check_result is None intead of False. Since any of the filter variables is set, we
            # do treat this as if the form was submitted and the checkbox was unchecked.
            if self._filter_used() and check_result is None:
                check_result = False

            if check_result == False:
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
        return "".join(headers)

declare_filter(215, FilterServiceState("svcstate",     _("Service states"),      ""))
declare_filter(216, FilterServiceState("svchardstate", _("Service hard states"), "hd"))

class FilterHostState(Filter):
    def __init__(self):
        Filter.__init__(self, "hoststate", _("Host states"),
                "host", [ "hoststate_filled", "hst0", "hst1", "hst2", "hstp" ], [])

    def display(self):
        html.begin_checkbox_group()
        html.hidden_field("hoststate_filled", "1", add_var=True)
        for var, text in [("hst0", _("UP")), ("hst1", _("DOWN")),
                          ("hst2", _("UNREACH")), ("hstp", _("PENDING"))]:
            html.checkbox(var, True if not self._filter_used() else False, label=text)
        html.end_checkbox_group()

    def _filter_used(self):
        return any([ html.has_var(v) for v in self.htmlvars ])

    def filter(self, infoname):
        headers = []
        for i in [0,1,2]:
            check_result = html.get_checkbox("hst%d" % i)

            # When a view is displayed e.g. as a dashlet the unchecked checkboxes are not set in
            # the HTML variables while the form was not interactively submitted. In this case the
            # check_result is None intead of False. Since any of the filter variables is set, we
            # do treat this as if the form was submitted and the checkbox was unchecked.
            if self._filter_used() and check_result is None:
                check_result = False

            if check_result == False:
                headers.append("Filter: host_state = %d\n"
                               "Filter: host_has_been_checked = 1\n"
                               "And: 2\nNegate:\n" % i)

        if html.get_checkbox("hstp") == False:
            headers.append("Filter: host_has_been_checked = 1\n")

        if len(headers) == 4: # none allowed = all allowed (makes URL building easier)
            return ""
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
        return ""

declare_filter(120, FilterHostsHavingServiceProblems())


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
        return "Filter: %s = 0\n" % self.column


class FilterNagiosExpression(FilterTristate):
    def __init__(self, info, name, title, pos, neg, deflt = -1):
        FilterTristate.__init__(self, name, title, info, None, deflt)
        self.pos = pos
        self.neg = neg

    def filter_code(self, infoname, positive):
        return self.pos if positive else self.neg

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


def declare_site_filters():
    # TODO: Refactor to factory
    if cmk.is_managed_edition():
        cls = cmk.gui.cme.plugins.visuals.managed.FilterCMESite
    else:
        cls = FilterSite

    declare_filter(500, cls("siteopt", False),
                   _("Optional selection of a site"))
    declare_filter(501, cls("site",    True),
                   _("Selection of site is enforced, use this filter for joining"))

declare_site_filters()

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

    def filter(self, infoname):
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
                "log", [ "logclass_filled" ] + [ "logclass%d" % l for l, _c in self.log_classes ], [])

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
        for l, _c in self.log_classes:
            if html.get_checkbox("logclass%d" % l) != False:
                headers.append("Filter: class = %d\n" % l)

        if len(headers) == 0:
            return "Limit: 0\n" # no class allowed
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
        for varsuffix, what, state, _text in self._items:
            if html.get_checkbox("logst_" + varsuffix) != False: # None = form not filled in = allow
                headers.append("Filter: log_type ~ %s .*\nFilter: log_state = %d\nAnd: 2\n" %
                            (what.upper(), state))
        if len(headers) == 0:
            return "Limit: 0\n" # no allowed state
        elif len(headers) == len(self._items):
            return "" # all allowed or form not filled in
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
        groups = [ (e[0], e[1].lstrip("/") ) for e in config.host_tag_groups() ]
        operators = [
            ("is", "="),
            ("isnot", u"≠"),
        ]

        # replace unicode strings, before writing out as "json"
        grouped = {}
        for entry in config.host_tag_groups():
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
                          style='width:129px', sorted=True, class_="grp")
            html.close_td()
            html.open_td()
            html.dropdown(prefix + '_op', [("", "")] + operators, style="width:36px", sorted=True, class_="op")
            html.close_td()
            html.open_td()
            choices = grouped[html.var(prefix + '_grp')] if html.var(prefix + '_grp') else [("", "")]
            html.dropdown(prefix + '_val', choices, style="width:129px", sorted=True, class_="val")
            html.close_td()
            html.close_tr()
        html.close_table()

    def hosttag_filter(self, negate, tag):
        return  'Filter: host_custom_variables %s TAGS (^|[ ])%s($|[ ])' % (negate and '!~' or '~', livestatus.lqencode(tag))

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
                    for entry in config.host_tag_groups():
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
        return ''

    def double_height(self):
        return True

declare_filter(302, FilterHostTags())



class FilterHostAuxTags(Filter):
    def __init__(self):
        self.count  = 3
        self.prefix = 'host_auxtags'
        htmlvars = []
        for num in range(self.count):
            htmlvars.append("%s_%d" % (self.prefix, num))
            htmlvars.append("%s_%d_neg" % (self.prefix, num))

        Filter.__init__(self,
            name     = 'host_auxtags',
            title    = _('Host Auxiliary Tags'),
            info     = 'host',
            htmlvars = htmlvars,
            link_columns = []
        )

        self.auxtags = config.wato_aux_tags


    def display(self):
        for num in range(self.count):
            html.dropdown('%s_%d' % (self.prefix, num), [("", "")] + self.auxtags, sorted=True, class_='neg')
            html.open_nobr()
            html.checkbox('%s_%d_neg' % (self.prefix, num), False, label=_("negate"))
            html.close_nobr()


    def host_auxtags_filter(self, tag, negate):
        return "Filter: host_custom_variables %s~ TAGS (^|[ ])%s($|[ ])" % (negate, livestatus.lqencode(tag))


    def filter(self, infoname):
        headers = []

        # Do not restrict to a certain number, because we'd like to link to this
        # via an URL, e.g. from the virtual host tree snapin
        num = 0
        while html.has_var( '%s_%d' % (self.prefix, num) ):
            this_tag = html.var( '%s_%d' % (self.prefix, num) )
            if this_tag:
                negate = ("!" if html.get_checkbox('%s_%d_neg' % (self.prefix, num))
                        else "")
                headers.append(self.host_auxtags_filter(this_tag, negate))
            num += 1

        if headers:
            return '\n'.join(headers) + '\n'
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
        return [( str(x[0]), "%s - %s" % (x[0], x[1]) ) for x in choices]


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
            for value, _readable in config.mkeventd_service_levels:
                if match_func(value):
                    filterline_values.append( "Filter: %s_custom_variable_values >= %s" % \
                                              (self.info, livestatus.lqencode(str(value))) )

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

        title = _("Favorite Hosts") if what == "host" else _("Favorite Services")

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
                filters += "Filter: host_name %s %s\n" % (eq, livestatus.lqencode(star))
                count += 1
        else:
            for star in stars:
                if ";" not in star:
                    continue
                h, s = star.split(";")
                filters += "Filter: host_name %s %s\n" % (eq, livestatus.lqencode(h))
                filters += "Filter: service_description %s %s\n" % (eq, livestatus.lqencode(s))
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


class BIGroupFilter(FilterUnicodeFilter):
    def __init__(self):
        self.column = "aggr_group"
        FilterUnicodeFilter.__init__(self, self.column, _("Aggregation group"),
                                     self.column, [self.column], [self.column])


    def variable_settings(self, row):
        return [ (self.htmlvars[0], row[self.column]) ]


    def display(self):
        htmlvar = self.htmlvars[0]
        html.dropdown(htmlvar, [("", "")] + [(group, group) for group in
                      {sg for g in bi.get_aggregation_group_trees() for sg in g}])


    def selected_group(self):
        return html.get_unicode_input(self.htmlvars[0])


    def filter_table(self, rows):
        group = self.selected_group()
        if not group:
            return rows
        return [row for row in rows if row[self.column] == group]


    def heading_info(self):
        return html.get_unicode_input(self.htmlvars[0])


declare_filter(90, BIGroupFilter())


class BIGroupTreeFilter(FilterUnicodeFilter):
    def __init__(self):
        self.column = "aggr_group_tree"
        FilterUnicodeFilter.__init__(self, self.column, _("Aggregation group tree"),
                                     "aggr_group", [self.column], [self.column])


    def variable_settings(self, row):
        return [ (self.htmlvars[0], row[self.column]) ]


    def display(self):
        htmlvar = self.htmlvars[0]
        html.dropdown(htmlvar, [("", "")] + self._get_selection())


    def selected_group(self):
        return html.get_unicode_input(self.htmlvars[0])


    def heading_info(self):
        return html.get_unicode_input(self.htmlvars[0])


    def _get_selection(self):
        def _build_tree(group, parent, path):
            this_node = group[0]
            path = path + (this_node,)
            child = parent.setdefault(this_node, {"__path__": path})
            children = group[1:]
            if children:
                child = child.setdefault('__children__', {})
                _build_tree(children, child, path)

        def _build_selection(selection, tree, index):
            index += 1
            for _, sub_tree in tree.iteritems():
                selection.append(_get_selection_entry(sub_tree, index, True))
                _build_selection(selection, sub_tree.get("__children__", {}), index)

        def _get_selection_entry(tree, index, prefix=None):
            path = tree["__path__"]
            if prefix:
                title_prefix = (u"\u00a0" * 6 * index) + u"\u2514\u2500 "
            else:
                title_prefix = ""
            return ("/".join(path), title_prefix + path[index])

        tree = {}
        for group in bi.get_aggregation_group_trees():
            _build_tree(group, tree, tuple())

        selection = []
        index = 0
        for _, sub_tree in tree.iteritems():
            selection.append(_get_selection_entry(sub_tree, index))
            _build_selection(selection, sub_tree.get("__children__", {}), index)

        return selection


declare_filter(91, BIGroupTreeFilter())


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
        for _s, h in hostlist:
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
        vars_ = [ self.prefix + str(x) for x in [ -1, 0, 1, 2, 3 ] ]
        if self.code == 'a':
            vars_.append(self.prefix + "n")
        Filter.__init__(self, self.column, title, "aggr", vars_, [])


    def filter(self, infoname):
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


if config.mkeventd_enabled:
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
    declare_filter(223, FilterNagiosFlag("event", "event_host_in_downtime", _("Host in downtime during event creation")))


    class EventFilterCount(Filter):
        def __init__(self, name, title):
            super(EventFilterCount, self).__init__(name, title, "event", [name + "_from", name + "_to"], [name])
            self._name = name

        def display(self):
            html.write_text("from: ")
            html.number_input(self._name + "_from", "")
            html.write_text(" to: ")
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
            super(EventFilterState, self).__init__(name, title, table, varnames, [name])
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
            for name, _title in self._choices:
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
    declare_filter(225, EventFilterState("history", "history_what", _("History action type"), [(k,k) for k in mkeventd.action_whats]))

    declare_filter(220, FilterTime("event",   "event_first",  _("First occurrence of event"),      "event_first", ))
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
            html.dropdown(self._varname, [ ("", "") ] + [(str(n),t) for (n,t) in choices])

        def filter(self, infoname):
            val = html.var(self._varname)
            if val:
                return "Filter: event_%s %s %s\n" % (self._column, self._operator, val)
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
                   "Or: 2\n" % (negate, livestatus.lqencode(current_value),
                                negate, livestatus.lqencode(current_value))


        def variable_settings(self, row):
            return []

    declare_filter(212, EventFilterEffectiveContactGroupCombo())
