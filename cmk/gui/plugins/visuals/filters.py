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

import abc
import re
import json

import livestatus

import cmk

import cmk.gui.utils
import cmk.gui.config as config
import cmk.gui.sites as sites
import cmk.gui.bi as bi
import cmk.gui.mkeventd as mkeventd
from cmk.gui.i18n import _
from cmk.gui.exceptions import MKUserError
from cmk.gui.globals import html
from cmk.gui.valuespec import (
    DualListChoice,
    Labels,
)

if cmk.is_managed_edition():
    import cmk.gui.cme.plugins.visuals.managed

from cmk.gui.plugins.visuals import (
    filter_registry,
    Filter,
    FilterUnicodeFilter,
    FilterTristate,
    FilterTime,
    FilterCRESite,
)


# Filters for substring search, displaying a text input field
class FilterText(Filter):
    def __init__(self, info, column, htmlvar, op, negateable=False, show_heading=True):
        htmlvars = [htmlvar]
        if negateable:
            htmlvars.append("neg_" + htmlvar)
        link_columns = column if isinstance(column, list) else [column]
        super(FilterText, self).__init__(info, htmlvars, link_columns)
        self.op = op
        self.column = column
        self.negateable = negateable
        self._show_heading = show_heading

    def _current_value(self):
        htmlvar = self.htmlvars[0]
        return html.request.var(htmlvar, "")

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
            return "Filter: %s %s%s %s\n" % (
                self.column,
                negate,
                self.op,
                livestatus.lqencode(current_value),
            )
        return ""

    def variable_settings(self, row):
        return [(self.htmlvars[0], row[self.column])]

    def heading_info(self):
        if self._show_heading:
            return self._current_value()


class FilterUnicode(FilterText):
    def _current_value(self):
        htmlvar = self.htmlvars[0]
        return html.get_unicode_input(htmlvar, "")


class FilterUnicodeRegExp(FilterUnicode):
    def validate_value(self, value):
        htmlvar = self.htmlvars[0]
        try:
            cmk.gui.utils.validate_regex(value[htmlvar])
        except Exception as e:
            raise MKUserError(htmlvar, "%s" % e)


class FilterRegExp(FilterText):
    def validate_value(self, value):
        htmlvar = self.htmlvars[0]
        try:
            cmk.gui.utils.validate_regex(value[htmlvar])
        except Exception as e:
            raise MKUserError(htmlvar, "%s" % e)


@filter_registry.register
class FilterHostregex(FilterRegExp):
    @property
    def ident(self):
        return "hostregex"

    @property
    def title(self):
        return _("Hostname")

    @property
    def sort_index(self):
        return 100

    @property
    def description(self):
        return _("Search field allowing regular expressions and partial matches")

    def __init__(self):
        FilterRegExp.__init__(self, "host", "host_name", "host_regex", "~~", True)


@filter_registry.register
class FilterHost(FilterText):
    @property
    def ident(self):
        return "host"

    @property
    def title(self):
        return _("Hostname (exact match)")

    @property
    def sort_index(self):
        return 101

    @property
    def description(self):
        return _("Exact match, used for linking")

    def __init__(self):
        FilterText.__init__(self, "host", "host_name", "host", "=", True)


@filter_registry.register
class FilterHostalias(FilterUnicode):
    @property
    def ident(self):
        return "hostalias"

    @property
    def title(self):
        return _("Hostalias")

    @property
    def sort_index(self):
        return 102

    @property
    def description(self):
        return _("Search field allowing regular expressions and partial matches")

    def __init__(self):
        FilterUnicode.__init__(self, "host", "host_alias", "hostalias", "~~", True)


@filter_registry.register
class FilterServiceregex(FilterUnicodeRegExp):
    @property
    def ident(self):
        return "serviceregex"

    @property
    def title(self):
        return _("Service")

    @property
    def sort_index(self):
        return 200

    @property
    def description(self):
        return _("Search field allowing regular expressions and partial matches")

    def __init__(self):
        FilterUnicodeRegExp.__init__(self, "service", "service_description", "service_regex", "~~",
                                     True)


@filter_registry.register
class FilterService(FilterUnicode):
    @property
    def ident(self):
        return "service"

    @property
    def title(self):
        return _("Service (exact match)")

    @property
    def sort_index(self):
        return 201

    @property
    def description(self):
        return _("Exact match, used for linking")

    def __init__(self):
        FilterUnicode.__init__(self, "service", "service_description", "service", "=")


@filter_registry.register
class FilterServiceDisplayName(FilterUnicodeRegExp):
    @property
    def ident(self):
        return "service_display_name"

    @property
    def title(self):
        return _("Service alternative display name")

    @property
    def sort_index(self):
        return 202

    @property
    def description(self):
        return _("Alternative display name of the service, regex match")

    def __init__(self):
        FilterUnicodeRegExp.__init__(self, "service", "service_display_name",
                                     "service_display_name", "~~")


@filter_registry.register
class FilterOutput(FilterUnicode):
    @property
    def ident(self):
        return "output"

    @property
    def title(self):
        return _("Status detail")

    @property
    def sort_index(self):
        return 202

    def __init__(self):
        FilterUnicode.__init__(self, "service", "service_plugin_output", "service_output", "~~",
                               True)


@filter_registry.register
class FilterHostnameOrAlias(FilterUnicode):
    @property
    def ident(self):
        return "hostnameoralias"

    @property
    def title(self):
        return _("Hostname or Alias")

    @property
    def sort_index(self):
        return 102

    @property
    def description(self):
        return _("Search field allowing regular expressions and partial matches")

    def __init__(self):
        FilterUnicode.__init__(self, "host", ["host_alias", "host_name"], "hostnameoralias", "~~",
                               False)

    def filter(self, infoname):
        current_value = self._current_value()

        if self.negateable and html.get_checkbox(self.htmlvars[1]):
            negate = "!"
        else:
            negate = ""

        if current_value:
            return "Filter: host_name %s%s %s\nFilter: alias %s%s %s\nOr: 2\n" % ((
                negate,
                self.op,
                livestatus.lqencode(current_value),
            ) * 2)
        return ""


class FilterIPAddress(Filter):
    _what = None

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
        address = html.request.var(self.htmlvars[0])
        if address:
            op = "="
            if html.request.var(self.htmlvars[1]) == "yes":
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
        return [(self.htmlvars[0], row["host_address"])]

    def heading_info(self):
        return html.request.var(self.htmlvars[0])


@filter_registry.register
class FilterHostAddress(FilterIPAddress):
    _what = "primary"

    @property
    def ident(self):
        return "host_address"

    @property
    def title(self):
        return _("Host address (Primary)")

    @property
    def sort_index(self):
        return 102

    def __init__(self):
        FilterIPAddress.__init__(self,
                                 "host", ["host_address", "host_address_prefix"],
                                 link_columns=["host_address"])


@filter_registry.register
class FilterHostIpv4Address(FilterIPAddress):
    _what = "ipv4"

    @property
    def ident(self):
        return "host_ipv4_address"

    @property
    def title(self):
        return _("Host address (IPv4)")

    @property
    def sort_index(self):
        return 102

    def __init__(self):
        FilterIPAddress.__init__(self,
                                 "host", ["host_ipv4_address", "host_ipv4_address_prefix"],
                                 link_columns=[])


@filter_registry.register
class FilterHostIpv6Address(FilterIPAddress):
    _what = "ipv6"

    @property
    def ident(self):
        return "host_ipv6_address"

    @property
    def title(self):
        return _("Host address (IPv6)")

    @property
    def sort_index(self):
        return 102

    def __init__(self):
        FilterIPAddress.__init__(self,
                                 "host", ["host_ipv6_address", "host_ipv6_address_prefix"],
                                 link_columns=[])


@filter_registry.register
class FilterAddressFamily(Filter):
    @property
    def ident(self):
        return "address_family"

    @property
    def title(self):
        return _("Host address family (Primary)")

    @property
    def sort_index(self):
        return 103

    def __init__(self):
        Filter.__init__(self, info="host", htmlvars=["address_family"], link_columns=[])

    def display(self):
        html.begin_radio_group()
        html.radiobutton("address_family", "4", False, _("IPv4"))
        html.radiobutton("address_family", "6", False, _("IPv6"))
        html.radiobutton("address_family", "both", True, _("Both"))
        html.end_radio_group()

    def filter(self, infoname):
        family = html.request.var("address_family", "both")
        if family == "both":
            return ""
        return "Filter: tags = address_family ip-v%s-only\n" % livestatus.lqencode(family)


@filter_registry.register
class FilterAddressFamilies(Filter):
    @property
    def ident(self):
        return "address_families"

    @property
    def title(self):
        return _("Host address families")

    @property
    def sort_index(self):
        return 103

    def __init__(self):
        Filter.__init__(self, info="host", htmlvars=[
            "address_families",
        ], link_columns=[])

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
        family = html.request.var("address_families")
        if not family:
            return ""

        elif family == "both":
            return "Filter: tags = ip-v4 ip-v4\n" \
                   "Filter: tags = ip-v6 ip-v6\n" \
                   "Or: 2\n"
        else:
            if family[0] == "4":
                tag = "ip-v4"
            elif family[0] == "6":
                tag = "ip-v6"
            filt = "Filter: tags = %s %s\n" % (livestatus.lqencode(tag), livestatus.lqencode(tag))

            if family.endswith("_only"):
                if family[0] == "4":
                    tag = "ip-v6"
                elif family[0] == "6":
                    tag = "ip-v4"
                filt += "Filter: tags != %s %s\n" % (livestatus.lqencode(tag),
                                                     livestatus.lqencode(tag))

            return filt


class FilterMultigroup(Filter):
    def __init__(self, what):
        self.htmlvar = what + "groups"
        htmlvars = [self.htmlvar]
        # TODO: Is always negateable. Cleanup the class.
        self.negateable = True
        if self.negateable:
            htmlvars.append("neg_" + self.htmlvar)
        Filter.__init__(self, info=what, htmlvars=htmlvars, link_columns=[])
        self.what = what

    def double_height(self):
        return True

    def valuespec(self):
        return DualListChoice(choices=self._get_choices(),
                              rows=3 if self.negateable else 4,
                              enlarge_active=True)

    def _get_choices(self):
        return sites.all_groups(self.what)

    def selection(self):
        current = html.request.var(self.htmlvar, "").strip().split("|")
        if current == ['']:
            return []
        return current

    def display(self):
        html.open_div(class_="multigroup")
        self.valuespec().render_input(self.htmlvar, self.selection())
        if self._get_choices() and self.negateable:
            html.open_nobr()
            html.checkbox(self.htmlvars[1], False, label=_("negate"))
            html.close_nobr()
        html.close_div()

    def filter(self, infoname):
        current = self.selection()
        if len(current) == 0:
            return ""  # No group selected = all groups selected, filter unused
        # not (A or B) => (not A) and (not B)
        if self.negateable and html.get_checkbox(self.htmlvars[1]):
            negate = "!"
            op = "And"
        else:
            negate = ""
            op = "Or"
        filters = ""
        for group in current:
            filters += "Filter: %s_groups %s>= %s\n" % (self.what, negate,
                                                        livestatus.lqencode(group))
        if len(current) > 1:
            filters += "%s: %d\n" % (op, len(current))
        return filters


@filter_registry.register
class FilterHostgroups(FilterMultigroup):
    @property
    def ident(self):
        return "hostgroups"

    @property
    def title(self):
        return _("Several Host Groups")

    @property
    def sort_index(self):
        return 105

    @property
    def description(self):
        return _("Selection of multiple host groups")

    def __init__(self):
        FilterMultigroup.__init__(self, "host")


@filter_registry.register
class FilterServicegroups(FilterMultigroup):
    @property
    def ident(self):
        return "servicegroups"

    @property
    def title(self):
        return _("Several Service Groups")

    @property
    def sort_index(self):
        return 205

    @property
    def description(self):
        return _("Selection of multiple service groups")

    def __init__(self):
        FilterMultigroup.__init__(self, "service")


# Selection of a host/service(-contact) group as an attribute of a host or service
class FilterGroupCombo(Filter):
    def __init__(self, what, enforce):
        self.enforce = enforce
        self.prefix = "opt" if not self.enforce else ""
        htmlvars = [self.prefix + what + "_group"]
        if not enforce:
            htmlvars.append("neg_" + htmlvars[0])
        Filter.__init__(self,
                        info=what.split("_")[0],
                        htmlvars=htmlvars,
                        link_columns=[what + "group_name"])
        self.what = what

    def double_height(self):
        return True

    def display(self):
        choices = sites.all_groups(self.what.split("_")[-1])
        if not self.enforce:
            choices = [("", "")] + choices
        html.dropdown(self.htmlvars[0], choices, ordered=True)
        if not self.enforce:
            html.open_nobr()
            html.checkbox(self.htmlvars[1], False, label=_("negate"))
            html.close_nobr()

    def current_value(self):
        htmlvar = self.htmlvars[0]
        return html.request.var(htmlvar)

    def filter(self, infoname):
        if not html.request.has_var(self.htmlvars[0]):
            return ""  # Skip if filter is not being set at all

        current_value = self.current_value()
        if not current_value:
            if not self.enforce:
                return ""
            # Take first group with the name we search
            table = self.what.replace("host_contact",
                                      "contact").replace("service_contact", "contact")
            current_value = sites.live().query_value(
                "GET %sgroups\nCache: reload\nColumns: name\nLimit: 1\n" % table, None)

        if current_value is None:
            return ""  # no {what}group exists!

        col = self.what + "_groups"
        if not self.enforce and html.request.var(self.htmlvars[1]):
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
                if html.request.var(negvar):
                    s.append((negvar, html.request.var(negvar)))
            return s
        else:
            return []

    def heading_info(self):
        current_value = self.current_value()
        if current_value:
            table = self.what.replace("host_contact",
                                      "contact").replace("service_contact", "contact")
            alias = sites.live().query_value(
                "GET %sgroups\nCache: reload\nColumns: alias\nFilter: name = %s\n" %
                (table, livestatus.lqencode(current_value)), current_value)
            return alias


@filter_registry.register
class FilterOpthostgroup(FilterGroupCombo):
    @property
    def ident(self):
        return "opthostgroup"

    @property
    def title(self):
        return _("Host is in Group")

    @property
    def sort_index(self):
        return 104

    @property
    def description(self):
        return _("Optional selection of host group")

    def __init__(self):
        FilterGroupCombo.__init__(self, "host", False)


@filter_registry.register
class FilterOptservicegroup(FilterGroupCombo):
    @property
    def ident(self):
        return "optservicegroup"

    @property
    def title(self):
        return _("Service is in Group")

    @property
    def sort_index(self):
        return 204

    @property
    def description(self):
        return _("Optional selection of service group")

    def __init__(self):
        FilterGroupCombo.__init__(self, "service", False)


# TODO: Had a name conflict with servicegroup filter for servicegroup info.
# The other one was registered -> Investigate.
#@filter_registry.register
#class FilterServicegroup(FilterGroupCombo):
#    @property
#    def ident(self):
#        return "servicegroup"
#
#    @property
#    def title(self):
#        return _("Servicegroup (enforced)")
#
#    @property
#    def sort_index(self):
#        return 205
#
#    @property
#    def description(self):
#        return _("Dropdown list, selection of service group is <b>enforced</b>")
#
#    def __init__(self):
#        FilterGroupCombo.__init__(self, "service", _("Servicegroup (enforced)"), True)


@filter_registry.register
class FilterOpthostContactgroup(FilterGroupCombo):
    @property
    def ident(self):
        return "opthost_contactgroup"

    @property
    def title(self):
        return _("Host Contact Group")

    @property
    def sort_index(self):
        return 106

    @property
    def description(self):
        return _("Optional selection of host contact group")

    def __init__(self):
        FilterGroupCombo.__init__(self, "host_contact", False)


@filter_registry.register
class FilterOptserviceContactgroup(FilterGroupCombo):
    @property
    def ident(self):
        return "optservice_contactgroup"

    @property
    def title(self):
        return _("Service Contact Group")

    @property
    def sort_index(self):
        return 206

    @property
    def description(self):
        return _("Optional selection of service contact group")

    def __init__(self):
        FilterGroupCombo.__init__(self, "service_contact", False)


@filter_registry.register
class FilterHostCtc(FilterText):
    @property
    def ident(self):
        return "host_ctc"

    @property
    def title(self):
        return _("Host Contact")

    @property
    def sort_index(self):
        return 107

    def __init__(self):
        FilterText.__init__(self, "host", "host_contacts", "host_ctc", ">=")


@filter_registry.register
class FilterHostCtcRegex(FilterRegExp):
    @property
    def ident(self):
        return "host_ctc_regex"

    @property
    def title(self):
        return _("Host Contact (Regex)")

    @property
    def sort_index(self):
        return 107

    def __init__(self):
        FilterRegExp.__init__(self, "host", "host_contacts", "host_ctc_regex", "~~")


@filter_registry.register
class FilterServiceCtc(FilterText):
    @property
    def ident(self):
        return "service_ctc"

    @property
    def title(self):
        return _("Service Contact")

    @property
    def sort_index(self):
        return 207

    def __init__(self):
        FilterText.__init__(self, "service", "service_contacts", "service_ctc", ">=")


@filter_registry.register
class FilterServiceCtcRegex(FilterRegExp):
    @property
    def ident(self):
        return "service_ctc_regex"

    @property
    def title(self):
        return _("Service Contact (Regex)")

    @property
    def sort_index(self):
        return 207

    def __init__(self):
        FilterRegExp.__init__(self, "service", "service_contacts", "service_ctc_regex", "~~")


# Selection of one group to be used in the info "hostgroup" or "servicegroup".
class FilterGroupSelection(Filter):
    def __init__(self, infoname):
        Filter.__init__(self, info=infoname, htmlvars=[infoname], link_columns=[])
        self.what = infoname

    def display(self):
        choices = sites.all_groups(self.what[:-5])  # chop off "group", leaves host or service
        html.dropdown(self.htmlvars[0], choices, ordered=True)

    def current_value(self):
        return html.request.var(self.htmlvars[0])

    def filter(self, infoname):
        current_value = self.current_value()
        if current_value:
            return "Filter: %s_name = %s\n" % (self.what, livestatus.lqencode(current_value))
        return ""

    def variable_settings(self, row):
        group_name = row[self.what + "_name"]
        return [(self.htmlvars[0], group_name)]


@filter_registry.register
class FilterHostgroup(FilterGroupSelection):
    @property
    def ident(self):
        return "hostgroup"

    @property
    def title(self):
        return _("Host Group")

    @property
    def sort_index(self):
        return 104

    @property
    def description(self):
        return _("Selection of the host group")

    def __init__(self):
        FilterGroupSelection.__init__(self, "hostgroup")


@filter_registry.register
class FilterServicegroup(FilterGroupSelection):
    @property
    def ident(self):
        return "servicegroup"

    @property
    def title(self):
        return _("Service Group")

    @property
    def sort_index(self):
        return 104

    @property
    def description(self):
        return _("Selection of the service group")

    def __init__(self):
        FilterGroupSelection.__init__(self, "servicegroup")


@filter_registry.register
class FilterHostgroupnameregex(FilterRegExp):
    @property
    def ident(self):
        return "hostgroupnameregex"

    @property
    def title(self):
        return _("Hostgroup (Regex)")

    @property
    def sort_index(self):
        return 101

    @property
    def description(self):
        return _(
            "Search field allowing regular expressions and partial matches on the names of hostgroups"
        )

    def __init__(self):
        FilterRegExp.__init__(self, "hostgroup", "hostgroup_name", "hostgroup_regex", "~~")


@filter_registry.register
class FilterHostgroupVisibility(Filter):
    @property
    def ident(self):
        return "hostgroupvisibility"

    @property
    def title(self):
        return _("Empty Hostgroup Visibilitiy")

    @property
    def sort_index(self):
        return 102

    @property
    def description(self):
        return _("You can enable this checkbox to show empty hostgroups")

    def __init__(self):
        Filter.__init__(self, info="hostgroup", htmlvars=["hostgroupshowempty"], link_columns=[])

    def display(self):
        html.checkbox("hostgroupshowempty", False, label="Show empty groups")

    def filter(self, infoname):
        if html.request.var("hostgroupshowempty"):
            return ""
        return "Filter: hostgroup_num_hosts > 0\n"


@filter_registry.register
class FilterServicegroupnameregex(FilterRegExp):
    @property
    def ident(self):
        return "servicegroupnameregex"

    @property
    def title(self):
        return _("Servicegroup (Regex)")

    @property
    def sort_index(self):
        return 101

    @property
    def description(self):
        return _("Search field allowing regular expression and partial matches")

    def __init__(self):
        FilterRegExp.__init__(self,
                              "servicegroup",
                              "servicegroup_name",
                              "servicegroup_regex",
                              "~~",
                              negateable=True)


@filter_registry.register
class FilterServicegroupname(FilterText):
    @property
    def ident(self):
        return "servicegroupname"

    @property
    def title(self):
        return _("Servicegroup (enforced)")

    @property
    def sort_index(self):
        return 101

    @property
    def description(self):
        return _("Exact match, used for linking")

    def __init__(self):
        FilterText.__init__(self, "servicegroup", "servicegroup_name", "servicegroup_name", "=")


class FilterQueryDropdown(Filter):
    def __init__(self, info, query, filterline):
        Filter.__init__(self, info, [self.ident], [])
        self.query = query
        self.filterline = filterline

    def display(self):
        selection = sites.live().query_column_unique(self.query)
        html.dropdown(self.ident, [("", "")] + [(x, x) for x in selection], ordered=True)

    def filter(self, infoname):
        current = html.request.var(self.ident)
        if current:
            return self.filterline % livestatus.lqencode(current)
        return ""


@filter_registry.register
class FilterHostCheckCommand(FilterQueryDropdown):
    @property
    def ident(self):
        return "host_check_command"

    @property
    def title(self):
        return _("Host check command")

    @property
    def sort_index(self):
        return 110

    def __init__(self):
        FilterQueryDropdown.__init__(self, "host", "GET commands\nCache: reload\nColumns: name\n",
                                     "Filter: host_check_command ~ ^%s(!.*)?\n")


@filter_registry.register
class FilterCheckCommand(FilterQueryDropdown):
    @property
    def ident(self):
        return "check_command"

    @property
    def title(self):
        return _("Service check command")

    @property
    def sort_index(self):
        return 210

    def __init__(self):
        FilterQueryDropdown.__init__(self, "service",
                                     "GET commands\nCache: reload\nColumns: name\n",
                                     "Filter: service_check_command ~ ^%s(!.*)?$\n")


class FilterServiceState(Filter):
    def __init__(self, prefix):
        Filter.__init__(self, "service", [
            prefix + "_filled",
            prefix + "st0",
            prefix + "st1",
            prefix + "st2",
            prefix + "st3",
            prefix + "stp",
        ], [])
        self.prefix = prefix

    def display(self):
        html.begin_checkbox_group()
        html.hidden_field(self.prefix + "_filled", "1", add_var=True)
        for var, text in [(self.prefix + "st0", _("OK")), (self.prefix + "st1", _("WARN")), \
                          (self.prefix + "st2", _("CRIT")), (self.prefix + "st3", _("UNKN")),
                          (self.prefix + "stp", _("PEND"))]:
            html.checkbox(var, True if not self._filter_used() else False, label=text)
        html.end_checkbox_group()

    def _filter_used(self):
        return any([html.request.has_var(v) for v in self.htmlvars])

    def filter(self, infoname):
        headers = []
        for i in [0, 1, 2, 3]:
            check_result = html.get_checkbox(self.prefix + "st%d" % i)

            # When a view is displayed e.g. as a dashlet the unchecked checkboxes are not set in
            # the HTML variables while the form was not interactively submitted. In this case the
            # check_result is None intead of False. Since any of the filter variables is set, we
            # do treat this as if the form was submitted and the checkbox was unchecked.
            if self._filter_used() and check_result is None:
                check_result = False

            if check_result is False:
                if self.prefix == "hd":
                    column = "service_last_hard_state"
                else:
                    column = "service_state"
                headers.append("Filter: %s = %d\n"
                               "Filter: service_has_been_checked = 1\n"
                               "And: 2\nNegate:\n" % (column, i))

        if html.get_checkbox(self.prefix + "stp") is False:
            headers.append("Filter: service_has_been_checked = 1\n")

        if len(headers) == 5:  # none allowed = all allowed (makes URL building easier)
            return ""
        return "".join(headers)


@filter_registry.register
class FilterSvcstate(FilterServiceState):
    @property
    def ident(self):
        return "svcstate"

    @property
    def title(self):
        return _("Service states")

    @property
    def sort_index(self):
        return 215

    def __init__(self):
        FilterServiceState.__init__(self, prefix="")


@filter_registry.register
class FilterSvchardstate(FilterServiceState):
    @property
    def ident(self):
        return "svchardstate"

    @property
    def title(self):
        return _("Service hard states")

    @property
    def sort_index(self):
        return 216

    def __init__(self):
        FilterServiceState.__init__(self, prefix="hd")


@filter_registry.register
class FilterHostState(Filter):
    @property
    def ident(self):
        return "hoststate"

    @property
    def title(self):
        return _("Host states")

    @property
    def sort_index(self):
        return 115

    def __init__(self):
        Filter.__init__(
            self,
            "host",
            ["hoststate_filled", "hst0", "hst1", "hst2", "hstp"],
            [],
        )

    def display(self):
        html.begin_checkbox_group()
        html.hidden_field("hoststate_filled", "1", add_var=True)
        for var, text in [
            ("hst0", _("UP")),
            ("hst1", _("DOWN")),
            ("hst2", _("UNREACH")),
            ("hstp", _("PEND")),
        ]:
            html.checkbox(var, True if not self._filter_used() else False, label=text)
        html.end_checkbox_group()

    def _filter_used(self):
        return any([html.request.has_var(v) for v in self.htmlvars])

    def filter(self, infoname):
        headers = []
        for i in [0, 1, 2]:
            check_result = html.get_checkbox("hst%d" % i)

            # When a view is displayed e.g. as a dashlet the unchecked checkboxes are not set in
            # the HTML variables while the form was not interactively submitted. In this case the
            # check_result is None intead of False. Since any of the filter variables is set, we
            # do treat this as if the form was submitted and the checkbox was unchecked.
            if self._filter_used() and check_result is None:
                check_result = False

            if check_result is False:
                headers.append("Filter: host_state = %d\n"
                               "Filter: host_has_been_checked = 1\n"
                               "And: 2\nNegate:\n" % i)

        if html.get_checkbox("hstp") is False:
            headers.append("Filter: host_has_been_checked = 1\n")

        if len(headers) == 4:  # none allowed = all allowed (makes URL building easier)
            return ""
        return "".join(headers)


@filter_registry.register
class FilterHostsHavingServiceProblems(Filter):
    @property
    def ident(self):
        return "hosts_having_service_problems"

    @property
    def title(self):
        return _("Hosts having certain service problems")

    @property
    def sort_index(self):
        return 120

    def __init__(self):
        Filter.__init__(self, "host", [
            "hosts_having_services_warn",
            "hosts_having_services_crit",
            "hosts_having_services_pending",
            "hosts_having_services_unknown",
        ], [])

    def display(self):
        html.begin_checkbox_group()
        for var, text in [
            ("warn", _("WARN")),
            ("crit", _("CRIT")),
            ("pending", _("PEND")),
            ("unknown", _("UNKNOWN")),
        ]:
            html.checkbox("hosts_having_services_%s" % var, True, label=text)
        html.end_checkbox_group()

    def filter(self, infoname):
        headers = []
        for var in ["warn", "crit", "pending", "unknown"]:
            if html.get_checkbox("hosts_having_services_%s" % var) is True:
                headers.append("Filter: host_num_services_%s > 0\n" % var)

        len_headers = len(headers)
        if len_headers > 0:
            headers.append("Or: %d\n" % len_headers)
            return "".join(headers)
        return ""


class FilterStateType(FilterTristate):
    def __init__(self, info):
        FilterTristate.__init__(self, info, None, deflt=-1)

    def display(self):
        current = html.request.var(self.varname)
        html.begin_radio_group(horizontal=True)
        for value, text in [("0", _("SOFT")), ("1", _("HARD")), ("-1", _("(ignore)"))]:
            checked = current == value or (current in [None, ""] and int(value) == self.deflt)
            html.radiobutton(self.varname, value, checked, text + " &nbsp; ")
        html.end_radio_group()

    def filter_code(self, infoname, positive):
        filter_value = "HARD" if positive else "SOFT"
        return "Filter: state_type = %s\n" % filter_value


@filter_registry.register
class FilterHostStateType(FilterStateType):
    @property
    def ident(self):
        return "host_state_type"

    @property
    def title(self):
        return _("Host state type")

    @property
    def sort_index(self):
        return 116

    def __init__(self):
        FilterStateType.__init__(self, "host")


@filter_registry.register
class FilterServiceStateType(FilterStateType):
    @property
    def ident(self):
        return "service_state_type"

    @property
    def title(self):
        return _("Service state type")

    @property
    def sort_index(self):
        return 217

    def __init__(self):
        FilterStateType.__init__(self, "service")


class FilterNagiosExpression(FilterTristate):
    def __init__(self, info, pos, neg, deflt=-1):
        FilterTristate.__init__(self, info, None, deflt)
        self.pos = pos
        self.neg = neg

    def filter_code(self, infoname, positive):
        return self.pos if positive else self.neg


@filter_registry.register
class FilterHasPerformanceData(FilterNagiosExpression):
    @property
    def ident(self):
        return "has_performance_data"

    @property
    def title(self):
        return _("Has performance data")

    @property
    def sort_index(self):
        return 251

    def __init__(self):
        FilterNagiosExpression.__init__(self, "service", "Filter: service_perf_data != \n",
                                        "Filter: service_perf_data = \n")


@filter_registry.register
class FilterInDowntime(FilterNagiosExpression):
    @property
    def ident(self):
        return "in_downtime"

    @property
    def title(self):
        return _("Host/service in downtime")

    @property
    def sort_index(self):
        return 232

    def __init__(self):
        FilterNagiosExpression.__init__(
            self, "service",
            "Filter: service_scheduled_downtime_depth > 0\nFilter: host_scheduled_downtime_depth > 0\nOr: 2\n",
            "Filter: service_scheduled_downtime_depth = 0\nFilter: host_scheduled_downtime_depth = 0\nAnd: 2\n"
        )


@filter_registry.register
class FilterHostStaleness(FilterNagiosExpression):
    @property
    def ident(self):
        return "host_staleness"

    @property
    def title(self):
        return _("Host is stale")

    @property
    def sort_index(self):
        return 232

    def __init__(self):
        FilterNagiosExpression.__init__(
            self, "host", "Filter: host_staleness >= %0.2f\n" % config.staleness_threshold,
            "Filter: host_staleness < %0.2f\n" % config.staleness_threshold)


@filter_registry.register
class FilterServiceStaleness(FilterNagiosExpression):
    @property
    def ident(self):
        return "service_staleness"

    @property
    def title(self):
        return _("Service is stale")

    @property
    def sort_index(self):
        return 232

    def __init__(self):
        FilterNagiosExpression.__init__(
            self, "service", "Filter: service_staleness >= %0.2f\n" % config.staleness_threshold,
            "Filter: service_staleness < %0.2f\n" % config.staleness_threshold)


class FilterNagiosFlag(FilterTristate):
    def __init__(self, info, deflt=-1):
        FilterTristate.__init__(self, info=info, column=self.ident, deflt=deflt)

    def filter_code(self, infoname, positive):
        if positive:
            return "Filter: %s != 0\n" % self.column
        return "Filter: %s = 0\n" % self.column


@filter_registry.register
class FilterServiceProcessPerformanceData(FilterNagiosFlag):
    @property
    def ident(self):
        return "service_process_performance_data"

    @property
    def title(self):
        return _("Processes performance data")

    @property
    def sort_index(self):
        return 250

    def __init__(self):
        FilterNagiosFlag.__init__(self, "service")


@filter_registry.register
class FilterHostInNotificationPeriod(FilterNagiosFlag):
    @property
    def ident(self):
        return "host_in_notification_period"

    @property
    def title(self):
        return _("Host in notification period")

    @property
    def sort_index(self):
        return 130

    def __init__(self):
        FilterNagiosFlag.__init__(self, "host")


@filter_registry.register
class FilterHostInServicePeriod(FilterNagiosFlag):
    @property
    def ident(self):
        return "host_in_service_period"

    @property
    def title(self):
        return _("Host in service period")

    @property
    def sort_index(self):
        return 130

    def __init__(self):
        FilterNagiosFlag.__init__(self, "host")


@filter_registry.register
class FilterHostAcknowledged(FilterNagiosFlag):
    @property
    def ident(self):
        return "host_acknowledged"

    @property
    def title(self):
        return _("Host problem has been acknowledged")

    @property
    def sort_index(self):
        return 131

    def __init__(self):
        FilterNagiosFlag.__init__(self, "host")


@filter_registry.register
class FilterHostActiveChecksEnabled(FilterNagiosFlag):
    @property
    def ident(self):
        return "host_active_checks_enabled"

    @property
    def title(self):
        return _("Host active checks enabled")

    @property
    def sort_index(self):
        return 132

    def __init__(self):
        FilterNagiosFlag.__init__(self, "host")


@filter_registry.register
class FilterHostNotificationsEnabled(FilterNagiosFlag):
    @property
    def ident(self):
        return "host_notifications_enabled"

    @property
    def title(self):
        return _("Host notifications enabled")

    @property
    def sort_index(self):
        return 133

    def __init__(self):
        FilterNagiosFlag.__init__(self, "host")


@filter_registry.register
class FilterServiceAcknowledged(FilterNagiosFlag):
    @property
    def ident(self):
        return "service_acknowledged"

    @property
    def title(self):
        return _("Problem acknowledged")

    @property
    def sort_index(self):
        return 230

    def __init__(self):
        FilterNagiosFlag.__init__(self, "service")


@filter_registry.register
class FilterServiceInNotificationPeriod(FilterNagiosFlag):
    @property
    def ident(self):
        return "service_in_notification_period"

    @property
    def title(self):
        return _("Service in notification period")

    @property
    def sort_index(self):
        return 231

    def __init__(self):
        FilterNagiosFlag.__init__(self, "service")


@filter_registry.register
class FilterServiceInServicePeriod(FilterNagiosFlag):
    @property
    def ident(self):
        return "service_in_service_period"

    @property
    def title(self):
        return _("Service in service period")

    @property
    def sort_index(self):
        return 231

    def __init__(self):
        FilterNagiosFlag.__init__(self, "service")


@filter_registry.register
class FilterServiceActiveChecksEnabled(FilterNagiosFlag):
    @property
    def ident(self):
        return "service_active_checks_enabled"

    @property
    def title(self):
        return _("Active checks enabled")

    @property
    def sort_index(self):
        return 233

    def __init__(self):
        FilterNagiosFlag.__init__(self, "service")


@filter_registry.register
class FilterServiceNotificationsEnabled(FilterNagiosFlag):
    @property
    def ident(self):
        return "service_notifications_enabled"

    @property
    def title(self):
        return _("Notifications enabled")

    @property
    def sort_index(self):
        return 234

    def __init__(self):
        FilterNagiosFlag.__init__(self, "service")


@filter_registry.register
class FilterServiceIsFlapping(FilterNagiosFlag):
    @property
    def ident(self):
        return "service_is_flapping"

    @property
    def title(self):
        return _("Flapping")

    @property
    def sort_index(self):
        return 236

    def __init__(self):
        FilterNagiosFlag.__init__(self, "service")


@filter_registry.register
class FilterServiceScheduledDowntimeDepth(FilterNagiosFlag):
    @property
    def ident(self):
        return "service_scheduled_downtime_depth"

    @property
    def title(self):
        return _("Service in downtime")

    @property
    def sort_index(self):
        return 231

    def __init__(self):
        FilterNagiosFlag.__init__(self, "service")


@filter_registry.register
class FilterHostScheduledDowntimeDepth(FilterNagiosFlag):
    @property
    def ident(self):
        return "host_scheduled_downtime_depth"

    @property
    def title(self):
        return _("Host in downtime")

    @property
    def sort_index(self):
        return 132

    def __init__(self):
        FilterNagiosFlag.__init__(self, "host")


if cmk.is_managed_edition():
    SiteFilter = cmk.gui.cme.plugins.visuals.managed.FilterCMESite
else:
    SiteFilter = FilterCRESite


@filter_registry.register
class FilterSiteOpt(SiteFilter):
    @property
    def ident(self):
        return "siteopt"

    @property
    def title(self):
        return _("Site")

    @property
    def sort_index(self):
        return 500

    @property
    def description(self):
        return _("Optional selection of a site")

    def __init__(self):
        SiteFilter.__init__(self, enforce=False)


@filter_registry.register
class FilterSite(SiteFilter):
    @property
    def ident(self):
        return "site"

    @property
    def title(self):
        return _("Site (enforced)")

    @property
    def sort_index(self):
        return 501

    @property
    def description(self):
        return _("Selection of site is enforced, use this filter for joining")

    def __init__(self):
        SiteFilter.__init__(self, enforce=True)


# info: usually either "host" or "service"
# column: a livestatus column of type int or float
class FilterNumberRange(Filter):  # type is int
    def __init__(self, info, column):
        self.column = column
        varnames = [self.ident + "_from", self.ident + "_until"]
        Filter.__init__(self, info, varnames, [])

    def display(self):
        html.write_text(_("From:") + "&nbsp;")
        html.text_input(self.htmlvars[0], style="width: 80px;")
        html.write_text(" &nbsp; " + _("To:") + "&nbsp;")
        html.text_input(self.htmlvars[1], style="width: 80px;")

    def filter(self, infoname):
        lql = ""
        for i, op in [(0, ">="), (1, "<=")]:
            try:
                txt = html.request.var(self.htmlvars[i])
                int(txt.strip())
                lql += "Filter: %s %s %s\n" % (self.column, op, txt.strip())
            except:
                pass
        return lql


@filter_registry.register
class FilterHostNotifNumber(FilterNumberRange):
    @property
    def ident(self):
        return "host_notif_number"

    @property
    def title(self):
        return _("Current Host Notification Number")

    @property
    def sort_index(self):
        return 232

    def __init__(self):
        FilterNumberRange.__init__(self, "host", "current_notification_number")


@filter_registry.register
class FilterSvcNotifNumber(FilterNumberRange):
    @property
    def ident(self):
        return "svc_notif_number"

    @property
    def title(self):
        return _("Current Service Notification Number")

    @property
    def sort_index(self):
        return 232

    def __init__(self):
        FilterNumberRange.__init__(self, "service", "current_notification_number")


@filter_registry.register
class FilterHostNumServices(FilterNumberRange):
    @property
    def ident(self):
        return "host_num_services"

    @property
    def title(self):
        return _("Number of Services of the Host")

    @property
    def sort_index(self):
        return 234

    def __init__(self):
        FilterNumberRange.__init__(self, "host", "num_services")


@filter_registry.register
class FilterSvcLastStateChange(FilterTime):
    @property
    def ident(self):
        return "svc_last_state_change"

    @property
    def title(self):
        return _("Last service state change")

    @property
    def sort_index(self):
        return 250

    def __init__(self):
        FilterTime.__init__(self, "service", "service_last_state_change")


@filter_registry.register
class FilterSvcLastCheck(FilterTime):
    @property
    def ident(self):
        return "svc_last_check"

    @property
    def title(self):
        return _("Last service check")

    @property
    def sort_index(self):
        return 251

    def __init__(self):
        FilterTime.__init__(self, "service", "service_last_check")


@filter_registry.register
class FilterHostLastStateChange(FilterTime):
    @property
    def ident(self):
        return "host_last_state_change"

    @property
    def title(self):
        return _("Last host state change")

    @property
    def sort_index(self):
        return 250

    def __init__(self):
        FilterTime.__init__(self, "host", "host_last_state_change")


@filter_registry.register
class FilterHostLastCheck(FilterTime):
    @property
    def ident(self):
        return "host_last_check"

    @property
    def title(self):
        return _("Last host check")

    @property
    def sort_index(self):
        return 251

    def __init__(self):
        FilterTime.__init__(self, "host", "host_last_check")


@filter_registry.register
class FilterCommentEntryTime(FilterTime):
    @property
    def ident(self):
        return "comment_entry_time"

    @property
    def title(self):
        return _("Time of comment")

    @property
    def sort_index(self):
        return 253

    def __init__(self):
        FilterTime.__init__(self, "comment", "comment_entry_time")


@filter_registry.register
class FilterCommentComment(FilterText):
    @property
    def ident(self):
        return "comment_comment"

    @property
    def title(self):
        return _("Comment")

    @property
    def sort_index(self):
        return 258

    def __init__(self):
        FilterText.__init__(self, "comment", "comment_comment", "comment_comment", "~~", True)


@filter_registry.register
class FilterCommentAuthor(FilterText):
    @property
    def ident(self):
        return "comment_author"

    @property
    def title(self):
        return _("Author comment")

    @property
    def sort_index(self):
        return 259

    def __init__(self):
        FilterText.__init__(self, "comment", "comment_author", "comment_author", "~~", True)


@filter_registry.register
class FilterDowntimeEntryTime(FilterTime):
    @property
    def ident(self):
        return "downtime_entry_time"

    @property
    def title(self):
        return _("Time when downtime was created")

    @property
    def sort_index(self):
        return 253

    def __init__(self):
        FilterTime.__init__(self, "downtime", "downtime_entry_time")


@filter_registry.register
class FilterDowntimeComment(FilterText):
    @property
    def ident(self):
        return "downtime_comment"

    @property
    def title(self):
        return _("Downtime comment")

    @property
    def sort_index(self):
        return 254

    def __init__(self):
        FilterText.__init__(self, "downtime", "downtime_comment", "downtime_comment", "~")


@filter_registry.register
class FilterDowntimeStartTime(FilterTime):
    @property
    def ident(self):
        return "downtime_start_time"

    @property
    def title(self):
        return _("Start of downtime")

    @property
    def sort_index(self):
        return 255

    def __init__(self):
        FilterTime.__init__(self, "downtime", "downtime_start_time")


@filter_registry.register
class FilterDowntimeAuthor(FilterText):
    @property
    def ident(self):
        return "downtime_author"

    @property
    def title(self):
        return _("Downtime author")

    @property
    def sort_index(self):
        return 256

    def __init__(self):
        FilterText.__init__(self, "downtime", "downtime_author", "downtime_author", "~")


@filter_registry.register
class FilterLogtime(FilterTime):
    @property
    def ident(self):
        return "logtime"

    @property
    def title(self):
        return _("Time of log entry")

    @property
    def sort_index(self):
        return 252

    def __init__(self):
        FilterTime.__init__(self, "log", "log_time")


# INFO          0 // all messages not in any other class
# ALERT         1 // alerts: the change service/host state
# PROGRAM       2 // important programm events (restart, ...)
# NOTIFICATION  3 // host/service notifications
# PASSIVECHECK  4 // passive checks
# COMMAND       5 // external commands
# STATE         6 // initial or current states
# ALERT HANDLERS 8


@filter_registry.register
class FilterLogClass(Filter):
    @property
    def ident(self):
        return "log_class"

    @property
    def title(self):
        return _("Logentry class")

    @property
    def sort_index(self):
        return 255

    def __init__(self):
        self.log_classes = [
            (0, _("Informational")),
            (1, _("Alerts")),
            (2, _("Program")),
            (3, _("Notifications")),
            (4, _("Passive checks")),
            (5, _("Commands")),
            (6, _("States")),
            (8, _("Alert Handlers")),
        ]

        Filter.__init__(
            self,
            "log",
            ["logclass_filled"] + ["logclass%d" % l for l, _c in self.log_classes],
            [],
        )

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

    def _filter_used(self):
        return any([html.request.has_var(v) for v in self.htmlvars])

    def filter(self, infoname):
        if not self._filter_used():
            return ""  # Do not apply this filter

        headers = []
        for l, _c in self.log_classes:
            if html.get_checkbox("logclass%d" % l) != False:
                headers.append("Filter: class = %d\n" % l)

        if len(headers) == 0:
            return "Limit: 0\n"  # no class allowed
        return "".join(headers) + ("Or: %d\n" % len(headers))


@filter_registry.register
class FilterLogPluginOutput(FilterUnicode):
    @property
    def ident(self):
        return "log_plugin_output"

    @property
    def title(self):
        return _("Log: plugin output")

    @property
    def sort_index(self):
        return 202

    def __init__(self):
        FilterUnicode.__init__(self, "log", "log_plugin_output", "log_plugin_output", "~~")


@filter_registry.register
class FilterLogType(FilterText):
    @property
    def ident(self):
        return "log_type"

    @property
    def title(self):
        return _("Log: message type")

    @property
    def sort_index(self):
        return 203

    def __init__(self):
        FilterText.__init__(self, "log", "log_type", "log_type", "~~", show_heading=False)


@filter_registry.register
class FilterLogStateType(FilterText):
    @property
    def ident(self):
        return "log_state_type"

    @property
    def title(self):
        return _("Log: state type")

    @property
    def sort_index(self):
        return 204

    def __init__(self):
        FilterText.__init__(self, "log", "log_state_type", "log_state_type", "~~")


@filter_registry.register
class FilterLogContactName(FilterText):
    @property
    def ident(self):
        return "log_contact_name"

    @property
    def title(self):
        return _("Log: contact name (exact match)")

    @property
    def sort_index(self):
        return 260

    @property
    def description(self):
        return _("Exact match, used for linking")

    def __init__(self):
        FilterText.__init__(self, "log", "log_contact_name", "log_contact_name", "=")


@filter_registry.register
class FilterLogContactNameRegex(FilterRegExp):
    @property
    def ident(self):
        return "log_contact_name_regex"

    @property
    def title(self):
        return _("Log: contact name")

    @property
    def sort_index(self):
        return 261

    def __init__(self):
        FilterRegExp.__init__(self,
                              "log",
                              "log_contact_name",
                              "log_contact_name_regex",
                              "~~",
                              negateable=True)


@filter_registry.register
class FilterLogCommandNameRegex(FilterRegExp):
    @property
    def ident(self):
        return "log_command_name_regex"

    @property
    def title(self):
        return _("Log: command")

    @property
    def sort_index(self):
        return 262

    def __init__(self):
        FilterRegExp.__init__(self,
                              "log",
                              "log_command_name",
                              "log_command_name_regex",
                              "~~",
                              negateable=True)


@filter_registry.register
class FilterLogState(Filter):
    @property
    def ident(self):
        return "log_state"

    @property
    def title(self):
        return _("Type of alerts of hosts and services")

    @property
    def sort_index(self):
        return 270

    def __init__(self):
        self._items = [
            ("h0", "host", 0, _("Up")),
            ("h1", "host", 1, _("Down")),
            ("h2", "host", 2, _("Unreachable")),
            ("s0", "service", 0, _("OK")),
            ("s1", "service", 1, _("Warning")),
            ("s2", "service", 2, _("Critical")),
            ("s3", "service", 3, _("Unknown")),
        ]

        Filter.__init__(
            self,
            "log",
            ["logst_" + e[0] for e in self._items],
            [],
        )

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
            if html.get_checkbox("logst_" +
                                 varsuffix) != False:  # None = form not filled in = allow
                headers.append("Filter: log_type ~ %s .*\nFilter: log_state = %d\nAnd: 2\n" %
                               (what.upper(), state))
        if len(headers) == 0:
            return "Limit: 0\n"  # no allowed state
        elif len(headers) == len(self._items):
            return ""  # all allowed or form not filled in
        return "".join(headers) + ("Or: %d\n" % len(headers))


@filter_registry.register
class FilterLogNotificationPhase(FilterTristate):
    @property
    def ident(self):
        return "log_notification_phase"

    @property
    def title(self):
        return _("Notification phase")

    @property
    def sort_index(self):
        return 271

    def __init__(self):
        FilterTristate.__init__(
            self,
            "log",
            "log_command_name",
            -1,
        )

    def double_height(self):
        return True

    def display(self):
        current = html.request.var(self.varname)
        html.begin_radio_group(horizontal=False)
        for value, text in [
            ("-1", _("Show all phases of notifications")),
            ("1", _("Show just preliminary notifications")),
            ("0", _("Show just end-user-notifications")),
        ]:
            checked = current == value or (current in [None, ""] and int(value) == self.deflt)
            html.radiobutton(self.varname, value, checked, text + " &nbsp; ")
            html.br()
        html.end_radio_group()

    def filter_code(self, infoname, positive):
        # Note: this filter also has to work for entries that are no notification.
        # In that case the filter is passive and lets everything through
        if positive:
            return "Filter: %s = check-mk-notify\nFilter: %s =\nOr: 2\n" % (self.column,
                                                                            self.column)
        return "Filter: %s != check-mk-notify\n" % self.column


@filter_registry.register
class FilterAggrServiceUsed(FilterTristate):
    @property
    def ident(self):
        return "aggr_service_used"

    @property
    def title(self):
        return _("Used in BI aggregate")

    @property
    def sort_index(self):
        return 300

    def __init__(self):
        FilterTristate.__init__(
            self,
            "service",
            None,
        )

    def filter(self, infoname):
        return ""

    def filter_table(self, rows):
        current = self.tristate_value()
        if current == -1:
            return rows
        new_rows = []
        for row in rows:
            is_part = bi.is_part_of_aggregation("service", row["site"], row["host_name"],
                                                row["service_description"])
            if (is_part and current == 1) or \
               (not is_part and current == 0):
                new_rows.append(row)
        return new_rows

    def filter_code(self, infoname, positive):
        pass


@filter_registry.register
class FilterDowntimeId(FilterText):
    @property
    def ident(self):
        return "downtime_id"

    @property
    def title(self):
        return _("Downtime ID")

    @property
    def sort_index(self):
        return 301

    def __init__(self):
        FilterText.__init__(self, "downtime", "downtime_id", "downtime_id", "=")


class ABCTagFilter(Filter):
    __metaclass__ = abc.ABCMeta

    @abc.abstractproperty
    def object_type(self):
        raise NotImplementedError()

    @property
    def sort_index(self):
        return 302

    @property
    def _var_prefix(self):
        return "%s_tag_" % (self.object_type)

    def __init__(self):
        self.count = 3
        htmlvars = []
        for num in range(self.count):
            htmlvars += [
                '%s%d_grp' % (self._var_prefix, num),
                '%s%d_op' % (self._var_prefix, num),
                '%s%d_val' % (self._var_prefix, num),
            ]

        Filter.__init__(self, info=self.object_type, htmlvars=htmlvars, link_columns=[])

    def display(self):
        groups = config.tags.get_tag_group_choices()
        operators = [
            ("is", "="),
            ("isnot", u"≠"),
        ]

        grouped = {}
        for tag_group in config.tags.tag_groups:
            grouped.setdefault(tag_group.id, [["", ""]])

            for grouped_tag in tag_group.tags:
                tag_id = "" if grouped_tag.id is None else grouped_tag.id
                grouped[tag_group.id].append([tag_id, grouped_tag.title])

        html.javascript('cmk.utils.set_tag_groups(%s, %s);' %
                        (json.dumps(self.object_type), json.dumps(grouped)))
        html.open_table()
        for num in range(self.count):
            prefix = '%s%d' % (self._var_prefix, num)
            html.open_tr()
            html.open_td()
            html.dropdown(prefix + '_grp', [("", "")] + groups,
                          onchange='cmk.utils.tag_update_value(\'%s\', \'%s\', this.value)' %
                          (self.object_type, prefix),
                          style='width:129px',
                          ordered=True,
                          class_="grp")
            html.close_td()
            html.open_td()
            html.dropdown(prefix + '_op', [("", "")] + operators,
                          style="width:36px",
                          ordered=True,
                          class_="op")
            html.close_td()
            html.open_td()
            choices = grouped[html.request.var(prefix +
                                               '_grp')] if html.request.var(prefix +
                                                                            '_grp') else [("", "")]
            html.dropdown(prefix + '_val', choices, style="width:129px", ordered=True, class_="val")
            html.close_td()
            html.close_tr()
        html.close_table()

    def filter(self, infoname):
        headers = []

        # Do not restrict to a certain number, because we'd like to link to this
        # via an URL, e.g. from the virtual host tree snapin
        num = 0
        while html.request.has_var('%s%d_op' % (self._var_prefix, num)):
            prefix = '%s%d' % (self._var_prefix, num)
            num += 1

            op = html.request.var(prefix + '_op')
            tag_group = config.tags.get_tag_group(html.request.var(prefix + '_grp'))
            tag = html.request.var(prefix + '_val')

            if not tag_group or not op:
                continue

            headers.append(self._tag_filter(tag_group.id, tag, negate=op != "is"))

        if headers:
            return '\n'.join(headers) + '\n'
        return ''

    def _tag_filter(self, tag_group, tag, negate):
        return "Filter: %s_tags %s %s %s" % (
            livestatus.lqencode(self.object_type),
            '!=' if negate else '=',
            livestatus.lqencode(livestatus.quote_dict(tag_group)),
            livestatus.lqencode(livestatus.quote_dict(tag)),
        )

    def double_height(self):
        return True


@filter_registry.register
class FilterHostTags(ABCTagFilter):
    @property
    def object_type(self):
        return "host"

    @property
    def ident(self):
        return "host_tags"

    @property
    def title(self):
        return _("Host Tags")


@filter_registry.register
class FilterServiceTags(ABCTagFilter):
    @property
    def object_type(self):
        return "service"

    @property
    def ident(self):
        return "service_tags"

    @property
    def title(self):
        return _("Tags")


@filter_registry.register
class FilterHostAuxTags(Filter):
    @property
    def ident(self):
        return "host_auxtags"

    @property
    def title(self):
        return _("Host Auxiliary Tags")

    @property
    def sort_index(self):
        return 302

    def __init__(self):
        self.count = 3
        self.prefix = 'host_auxtags'
        htmlvars = []
        for num in range(self.count):
            htmlvars.append("%s_%d" % (self.prefix, num))
            htmlvars.append("%s_%d_neg" % (self.prefix, num))

        Filter.__init__(self, info='host', htmlvars=htmlvars, link_columns=[])

    def display(self):
        aux_tag_choices = [("", "")] + config.tags.aux_tag_list.get_choices()
        for num in range(self.count):
            html.dropdown('%s_%d' % (self.prefix, num), aux_tag_choices, ordered=True, class_='neg')
            html.open_nobr()
            html.checkbox('%s_%d_neg' % (self.prefix, num), False, label=_("negate"))
            html.close_nobr()

    def filter(self, infoname):
        headers = []

        # Do not restrict to a certain number, because we'd like to link to this
        # via an URL, e.g. from the virtual host tree snapin
        num = 0
        while html.request.has_var('%s_%d' % (self.prefix, num)):
            this_tag = html.request.var('%s_%d' % (self.prefix, num))
            if this_tag:
                negate = html.get_checkbox('%s_%d_neg' % (self.prefix, num))
                headers.append(self._host_auxtags_filter(this_tag, negate))
            num += 1

        if headers:
            return '\n'.join(headers) + '\n'
        return ''

    def _host_auxtags_filter(self, tag, negate):
        return "Filter: host_tags %s %s %s" % ("!=" if negate else "=",
                                               livestatus.lqencode(livestatus.quote_dict(tag)),
                                               livestatus.lqencode(livestatus.quote_dict(tag)))

    def double_height(self):
        return True


class ABCLabelFilter(Filter):
    __metaclass__ = abc.ABCMeta

    @abc.abstractproperty
    def object_type(self):
        raise NotImplementedError()

    @property
    def sort_index(self):
        return 301

    @property
    def _var_prefix(self):
        return "%s_label" % self.object_type

    @property
    def _column(self):
        return "%s_labels" % self.object_type

    def __init__(self):
        Filter.__init__(self, info=self.object_type, htmlvars=[self._var_prefix], link_columns=[])

    def _current_value(self):
        return self._valuespec().from_html_vars(self._var_prefix)

    def heading_info(self):
        return " ".join(":".join(e) for e in sorted(self._current_value().items()))

    def variable_settings(self, row):
        return [(self.htmlvars[0], row[self._column])]

    def _valuespec(self):
        return Labels(world=Labels.World.CORE)

    def display(self):
        self._valuespec().render_input(self._var_prefix, self._current_value())

    def filter(self, infoname):
        value = self._current_value()
        if not value:
            return ""

        return self._get_label_filters(value)

    def _get_label_filters(self, labels):
        filters = []
        for label_id, label_value in labels.items():
            filters.append(self._label_filter(label_id, label_value))
        return "".join(filters)

    def _label_filter(self, label_id, label_value):
        return "Filter: %s = %s %s\n" % (
            livestatus.lqencode(self._column),
            livestatus.lqencode(livestatus.quote_dict(label_id)),
            livestatus.lqencode(livestatus.quote_dict(label_value)),
        )


@filter_registry.register
class FilterHostLabels(ABCLabelFilter):
    @property
    def object_type(self):
        return "host"

    @property
    def ident(self):
        return "host_labels"

    @property
    def title(self):
        return _("Host labels")

    def double_height(self):
        return True


@filter_registry.register
class FilterServiceLabels(ABCLabelFilter):
    @property
    def object_type(self):
        return "service"

    @property
    def ident(self):
        return "service_labels"

    @property
    def title(self):
        return _("Service labels")

    def double_height(self):
        return True


class ABCFilterCustomAttribute(Filter):
    __metaclass__ = abc.ABCMeta

    @property
    def sort_index(self):
        return 103

    def __init__(self, info):
        Filter.__init__(self,
                        info=info,
                        htmlvars=[self.name_varname, self.value_varname],
                        link_columns=[])

    @property
    def name_varname(self):
        return "%s_name" % self.ident

    @property
    def value_varname(self):
        return "%s_value" % self.ident

    def display(self):
        html.dropdown(self.name_varname, [("", "")] + self._custom_attribute_choices())
        html.text_input(self.value_varname)

    @abc.abstractmethod
    def _custom_attribute_choices(self):
        raise NotImplementedError()

    def filter(self, infoname):
        if not html.get_ascii_input(self.name_varname):
            return ""

        attribute_id = html.get_item_input(self.name_varname,
                                           dict(self._custom_attribute_choices()))[1]
        value = html.get_unicode_input(self.value_varname)
        return "Filter: %s_custom_variables ~~ %s ^%s\n" % (
            self.info, livestatus.lqencode(attribute_id.upper()), livestatus.lqencode(value))


@filter_registry.register
class FilterCustomServiceAttribute(ABCFilterCustomAttribute):
    @property
    def ident(self):
        return "service_custom_variable"

    @property
    def title(self):
        return _("Service custom attribute")

    def __init__(self):
        ABCFilterCustomAttribute.__init__(self, info="service")

    def _custom_attribute_choices(self):
        choices = []
        for ident, attr_spec in config.custom_service_attributes.items():
            choices.append((ident, attr_spec["title"]))
        return sorted(choices, key=lambda x: x[1])


@filter_registry.register
class FilterCustomHostAttribute(ABCFilterCustomAttribute):
    @property
    def ident(self):
        return "host_custom_variable"

    @property
    def title(self):
        return _("Host custom attribute")

    def __init__(self):
        ABCFilterCustomAttribute.__init__(self, info="host")

    def _custom_attribute_choices(self):
        choices = []
        for attr_spec in config.wato_host_attrs:
            choices.append((attr_spec["name"], attr_spec["title"]))
        return sorted(choices, key=lambda x: x[1])


# choices = [ (value, "readable"), .. ]
class FilterECServiceLevelRange(Filter):
    def __init__(self, info):
        self.lower_bound_varname = "%s_lower" % self.ident
        self.upper_bound_varname = "%s_upper" % self.ident

        Filter.__init__(self, info, [
            self.lower_bound_varname,
            self.upper_bound_varname,
        ], [])

    def _prepare_choices(self):
        choices = config.mkeventd_service_levels[:]
        choices.sort()
        return [(str(x[0]), "%s - %s" % (x[0], x[1])) for x in choices]

    def display(self):
        selection = [("", "")] + self._prepare_choices()
        html.open_div(class_="service_level min")
        html.write_text("From")
        html.dropdown(self.lower_bound_varname, selection)
        html.close_div()
        html.open_div(class_="service_level max")
        html.write_text("To")
        html.select(self.upper_bound_varname, selection)
        html.close_div()

    def filter(self, infoname):
        lower_bound = html.request.var(self.lower_bound_varname)
        upper_bound = html.request.var(self.upper_bound_varname)

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

            filterline += "%s\n" % "\n".join(filterline_values)

            len_filterline_values = len(filterline_values)
            if len_filterline_values > 1:
                filterline += "Or: %d\n" % len_filterline_values

            return filterline

        else:
            return ""

    def double_height(self):
        return True


@filter_registry.register
class FilterSvcServiceLevel(FilterECServiceLevelRange):
    @property
    def ident(self):
        return "svc_service_level"

    @property
    def title(self):
        return _("Service service level")

    @property
    def sort_index(self):
        return 310

    def __init__(self):
        FilterECServiceLevelRange.__init__(self, "service")


@filter_registry.register
class FilterHstServiceLevel(FilterECServiceLevelRange):
    @property
    def ident(self):
        return "hst_service_level"

    @property
    def title(self):
        return _("Host service level")

    @property
    def sort_index(self):
        return 310

    def __init__(self):
        FilterECServiceLevelRange.__init__(self, "host")


class FilterStarred(FilterTristate):
    def __init__(self, what):
        self.what = what
        FilterTristate.__init__(
            self,
            info=what,
            column=what + "_favorite",  # Column, not used
            deflt=-1,
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


@filter_registry.register
class FilterHostFavorites(FilterStarred):
    @property
    def ident(self):
        return "host_favorites"

    @property
    def title(self):
        return _("Favorite Hosts")

    @property
    def sort_index(self):
        return 501

    def __init__(self):
        FilterStarred.__init__(self, "host")


@filter_registry.register
class FilterServiceFavorites(FilterStarred):
    @property
    def ident(self):
        return "service_favorites"

    @property
    def title(self):
        return _("Favorite Services")

    @property
    def sort_index(self):
        return 501

    def __init__(self):
        FilterStarred.__init__(self, "service")


@filter_registry.register
class FilterDiscoveryState(Filter):
    @property
    def ident(self):
        return "discovery_state"

    @property
    def title(self):
        return _("Discovery state")

    @property
    def sort_index(self):
        return 601

    def __init__(self):
        self.__options = [
            ("discovery_state_ignored", _("Hidden")),
            ("discovery_state_vanished", _("Vanished")),
            ("discovery_state_unmonitored", _("New")),
        ]
        Filter.__init__(
            self,
            "discovery",
            [o[0] for o in self.__options],
            [],
        )
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
            if value is None:
                value = True  # Default setting for filter: all checked!
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


@filter_registry.register
class FilterAggrGroup(FilterUnicodeFilter):
    @property
    def ident(self):
        return "aggr_group"

    @property
    def title(self):
        return _("Aggregation group")

    @property
    def sort_index(self):
        return 90

    def __init__(self):
        self.column = "aggr_group"
        FilterUnicodeFilter.__init__(self, self.column, [self.column], [self.column])

    def variable_settings(self, row):
        return [(self.htmlvars[0], row[self.column])]

    def display(self):
        htmlvar = self.htmlvars[0]
        html.dropdown(htmlvar,
                      [("", "")] + [(group, group) for group in bi.get_aggregation_group_trees()])

    def selected_group(self):
        return html.get_unicode_input(self.htmlvars[0])

    def filter_table(self, rows):
        group = self.selected_group()
        if not group:
            return rows
        return [row for row in rows if row[self.column] == group]

    def heading_info(self):
        return html.get_unicode_input(self.htmlvars[0])


@filter_registry.register
class FilterAggrGroupTree(FilterUnicodeFilter):
    @property
    def ident(self):
        return "aggr_group_tree"

    @property
    def title(self):
        return _("Aggregation group tree")

    @property
    def sort_index(self):
        return 91

    def __init__(self):
        self.column = "aggr_group_tree"
        FilterUnicodeFilter.__init__(self, "aggr_group", [self.column], [self.column])

    def variable_settings(self, row):
        return [(self.htmlvars[0], row[self.column])]

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
            _build_tree(group.split("/"), tree, tuple())

        selection = []
        index = 0
        for _, sub_tree in tree.iteritems():
            selection.append(_get_selection_entry(sub_tree, index))
            _build_selection(selection, sub_tree.get("__children__", {}), index)

        return selection


# how is either "regex" or "exact"
class BITextFilter(FilterUnicodeFilter):
    def __init__(self, what, how="regex", suffix=""):
        self.how = how
        self.column = "aggr_" + what
        FilterUnicodeFilter.__init__(self,
                                     info="aggr",
                                     htmlvars=[self.column + suffix],
                                     link_columns=[self.column])

    def variable_settings(self, row):
        return [(self.htmlvars[0], row[self.column])]

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
            except re.error as e:
                html.add_user_error(None, "Invalid regular expression: %s" % e)
                return rows

            return [row for row in rows if reg.search(row[self.column].lower())]
        return [row for row in rows if row[self.column] == val]


@filter_registry.register
class FilterAggrNameRegex(BITextFilter):
    @property
    def ident(self):
        return "aggr_name_regex"

    @property
    def title(self):
        return _("Aggregation name")

    @property
    def sort_index(self):
        return 120

    def __init__(self):
        BITextFilter.__init__(self, "name", suffix="_regex")


@filter_registry.register
class FilterAggrName(BITextFilter):
    @property
    def ident(self):
        return "aggr_name"

    @property
    def title(self):
        return _("Aggregation name (exact match)")

    @property
    def sort_index(self):
        return 120

    def __init__(self):
        BITextFilter.__init__(self, "name", how="exact")


@filter_registry.register
class FilterAggrOutput(BITextFilter):
    @property
    def ident(self):
        return "aggr_output"

    @property
    def title(self):
        return _("Aggregation output")

    @property
    def sort_index(self):
        return 121

    def __init__(self):
        BITextFilter.__init__(self, "output")


@filter_registry.register
class FilterAggrHosts(Filter):
    @property
    def ident(self):
        return "aggr_hosts"

    @property
    def title(self):
        return _("Affected hosts contain")

    @property
    def sort_index(self):
        return 130

    @property
    def description(self):
        return _(
            "Filter for all aggregations that base on status information of that host. Exact match (no regular expression)"
        )

    def __init__(self):
        Filter.__init__(
            self,
            "aggr",
            ["aggr_host_site", "aggr_host_host"],
            [],
        )

    def display(self):
        html.text_input(self.htmlvars[1])

    def heading_info(self):
        return html.request.var(self.htmlvars[1])

    def find_host(self, host, hostlist):
        for _s, h in hostlist:
            if h == host:
                return True
        return False

    # Used for linking
    def variable_settings(self, row):
        return [("aggr_host_host", row["host_name"]), ("aggr_host_site", row["site"])]

    def filter_table(self, rows):
        val = html.request.var(self.htmlvars[1])
        if not val:
            return rows
        return [row for row in rows if self.find_host(val, row["aggr_hosts"])]


@filter_registry.register
class FilterAggrService(Filter):
    @property
    def ident(self):
        return "aggr_service"

    @property
    def title(self):
        return _("Affected by service")

    @property
    def sort_index(self):
        return 131

    @property
    def description(self):
        return _(
            "Filter for all aggregations that are affected by one specific service on a specific host (no regular expression)"
        )

    def __init__(self):
        Filter.__init__(
            self,
            "aggr",
            ["aggr_service_site", "aggr_service_host", "aggr_service_service"],
            [],
        )

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
        if html.request.has_var(self.htmlvars[2]):
            return html.get_unicode_input(self.htmlvars[0]), html.get_unicode_input(
                self.htmlvars[1]), html.get_unicode_input(self.htmlvars[2])

    # Used for linking
    def variable_settings(self, row):
        return [("site", row["site"]), ("host", row["host_name"]),
                ("service", row["service_description"])]


class BIStatusFilter(Filter):
    def __init__(self, what):
        self.column = "aggr_" + what + "state"
        if what == "":
            self.code = 'r'
        else:
            self.code = what[0]
        self.prefix = "bi%ss" % self.code
        vars_ = ["%s%s" % (self.prefix, x) for x in [-1, 0, 1, 2, 3, "_filled"]]
        if self.code == 'a':
            vars_.append(self.prefix + "n")
        Filter.__init__(self, info="aggr", htmlvars=vars_, link_columns=[])

    def filter(self, infoname):
        return ""

    def double_height(self):
        return self.column == "aggr_assumed_state"

    def _filter_used(self):
        return html.request.has_var(self.prefix + "_filled")

    def display(self):
        html.hidden_field(self.prefix + "_filled", "1", add_var=True)

        for varend, text in [
            ('0', _('OK')),
            ('1', _('WARN')),
            ('2', _('CRIT')),
            ('3', _('UNKN')),
            ('-1', _('PEND')),
            ('n', _('no assumed state set')),
        ]:
            if self.code != 'a' and varend == 'n':
                continue  # no unset for read and effective state
            if varend == 'n':
                html.br()
            var = self.prefix + varend
            html.checkbox(var, defval=not self._filter_used(), label=text)

    def filter_table(self, rows):
        if not self._filter_used():
            return rows

        allowed_states = []
        for i in ['0', '1', '2', '3', '-1', 'n']:
            if html.get_checkbox(self.prefix + i):
                if i == 'n':
                    s = None
                else:
                    s = int(i)
                allowed_states.append(s)
        newrows = []
        for row in rows:
            if row[self.column] is not None:
                s = row[self.column]["state"]
            else:
                s = None
            if s in allowed_states:
                newrows.append(row)
        return newrows


@filter_registry.register
class FilterAggrState(BIStatusFilter):
    @property
    def ident(self):
        return "aggr_state"

    @property
    def title(self):
        return _(" State")

    @property
    def sort_index(self):
        return 150

    def __init__(self):
        BIStatusFilter.__init__(self, "")


@filter_registry.register
class FilterAggrEffectiveState(BIStatusFilter):
    @property
    def ident(self):
        return "aggr_effective_state"

    @property
    def title(self):
        return _("Effective  State")

    @property
    def sort_index(self):
        return 151

    def __init__(self):
        BIStatusFilter.__init__(self, "effective_")


@filter_registry.register
class FilterAggrAssumedState(BIStatusFilter):
    @property
    def ident(self):
        return "aggr_assumed_state"

    @property
    def title(self):
        return _("Assumed  State")

    @property
    def sort_index(self):
        return 152

    def __init__(self):
        BIStatusFilter.__init__(self, "assumed_")


@filter_registry.register
class FilterEventId(FilterText):
    @property
    def ident(self):
        return "event_id"

    @property
    def title(self):
        return _("Event ID")

    @property
    def sort_index(self):
        return 200

    def __init__(self):
        FilterText.__init__(self, "event", "event_id", "event_id", "=")


@filter_registry.register
class FilterEventRuleId(FilterText):
    @property
    def ident(self):
        return "event_rule_id"

    @property
    def title(self):
        return _("ID of rule")

    @property
    def sort_index(self):
        return 200

    def __init__(self):
        FilterText.__init__(self, "event", "event_rule_id", "event_rule_id", "=")


@filter_registry.register
class FilterEventText(FilterText):
    @property
    def ident(self):
        return "event_text"

    @property
    def title(self):
        return _("Message/Text of event")

    @property
    def sort_index(self):
        return 201

    def __init__(self):
        FilterText.__init__(self, "event", "event_text", "event_text", "~~")


@filter_registry.register
class FilterEventApplication(FilterText):
    @property
    def ident(self):
        return "event_application"

    @property
    def title(self):
        return _("Application / Syslog-Tag")

    @property
    def sort_index(self):
        return 201

    def __init__(self):
        FilterText.__init__(self, "event", "event_application", "event_application", "~~")


@filter_registry.register
class FilterEventContact(FilterText):
    @property
    def ident(self):
        return "event_contact"

    @property
    def title(self):
        return _("Contact Person")

    @property
    def sort_index(self):
        return 201

    def __init__(self):
        FilterText.__init__(self, "event", "event_contact", "event_contact", "~~")


@filter_registry.register
class FilterEventComment(FilterText):
    @property
    def ident(self):
        return "event_comment"

    @property
    def title(self):
        return _("Comment to the event")

    @property
    def sort_index(self):
        return 201

    def __init__(self):
        FilterText.__init__(self, "event", "event_comment", "event_comment", "~~")


@filter_registry.register
class FilterEventHostRegex(FilterRegExp):
    @property
    def ident(self):
        return "event_host_regex"

    @property
    def title(self):
        return _("Hostname of original event")

    @property
    def sort_index(self):
        return 201

    def __init__(self):
        FilterRegExp.__init__(self, "event", "event_host", "event_host", "~~")


@filter_registry.register
class FilterEventHost(FilterText):
    @property
    def ident(self):
        return "event_host"

    @property
    def title(self):
        return _("Hostname of event, exact match")

    @property
    def sort_index(self):
        return 201

    def __init__(self):
        FilterText.__init__(self, "event", "event_host", "event_host", "=")


@filter_registry.register
class FilterEventIpaddress(FilterText):
    @property
    def ident(self):
        return "event_ipaddress"

    @property
    def title(self):
        return _("Original IP Address of event")

    @property
    def sort_index(self):
        return 201

    def __init__(self):
        FilterText.__init__(self, "event", "event_ipaddress", "event_ipaddress", "~~")


@filter_registry.register
class FilterEventOwner(FilterText):
    @property
    def ident(self):
        return "event_owner"

    @property
    def title(self):
        return _("Owner of event")

    @property
    def sort_index(self):
        return 201

    def __init__(self):
        FilterText.__init__(self, "event", "event_owner", "event_owner", "~~")


@filter_registry.register
class FilterHistoryWho(FilterText):
    @property
    def ident(self):
        return "history_who"

    @property
    def title(self):
        return _("User that performed action")

    @property
    def sort_index(self):
        return 221

    def __init__(self):
        FilterText.__init__(self, "history", "history_who", "history_who", "~~")


@filter_registry.register
class FilterHistoryLine(FilterText):
    @property
    def ident(self):
        return "history_line"

    @property
    def title(self):
        return _("Line number in history logfile")

    @property
    def sort_index(self):
        return 222

    def __init__(self):
        FilterText.__init__(self, "history", "history_line", "history_line", "=")


@filter_registry.register
class FilterEventHostInDowntime(FilterNagiosFlag):
    @property
    def ident(self):
        return "event_host_in_downtime"

    @property
    def title(self):
        return _("Host in downtime during event creation")

    @property
    def sort_index(self):
        return 223

    def __init__(self):
        FilterNagiosFlag.__init__(self, "event")


@filter_registry.register
class FilterEventCount(Filter):
    @property
    def ident(self):
        return "event_count"

    @property
    def title(self):
        return _("Message count")

    @property
    def sort_index(self):
        return 205

    def __init__(self):
        name = "event_count"
        Filter.__init__(self, "event", [name + "_from", name + "_to"], [name])
        self._name = name

    def display(self):
        html.write_text("from: ")
        html.number_input(self._name + "_from", "")
        html.write_text(" to: ")
        html.number_input(self._name + "_to", "")

    def filter(self, infoname):
        f = ""
        if html.request.var(self._name + "_from"):
            f += "Filter: event_count >= %d\n" % int(html.request.var(self._name + "_from"))
        if html.request.var(self._name + "_to"):
            f += "Filter: event_count <= %d\n" % int(html.request.var(self._name + "_to"))
        return f


class EventFilterState(Filter):
    def __init__(self, table, choices):
        varnames = [self.ident + "_" + str(c[0]) for c in choices]
        super(EventFilterState, self).__init__(table, varnames, [self.ident])
        self._choices = choices

    def double_height(self):
        return len(self._choices) >= 5

    def display(self):
        html.begin_checkbox_group()
        for name, title in self._choices:
            html.checkbox(self.ident + "_" + str(name), True, label=title)
        html.end_checkbox_group()

    def filter(self, infoname):
        selected = []
        for name, _title in self._choices:
            if html.get_checkbox(self.ident + "_" + str(name)):
                selected.append(str(name))

        if not selected:
            return ""

        filters = []
        for sel in selected:
            filters.append("Filter: %s = %s" % (self.ident, sel))

        f = "\n".join(filters)
        if len(filters) > 1:
            f += "\nOr: %d" % len(filters)

        return f + "\n"


@filter_registry.register
class FilterEventState(EventFilterState):
    @property
    def ident(self):
        return "event_state"

    @property
    def title(self):
        return _("State classification")

    @property
    def sort_index(self):
        return 206

    def __init__(self):
        EventFilterState.__init__(self, "event", [(0, _("OK")), (1, _("WARN")), (2, _("CRIT")),
                                                  (3, _("UNKNOWN"))])


@filter_registry.register
class FilterEventPhase(EventFilterState):
    @property
    def ident(self):
        return "event_phase"

    @property
    def title(self):
        return _("Phase")

    @property
    def sort_index(self):
        return 207

    def __init__(self):
        EventFilterState.__init__(self, "event", mkeventd.phase_names.items())


@filter_registry.register
class FilterEventPriority(EventFilterState):
    @property
    def ident(self):
        return "event_priority"

    @property
    def title(self):
        return _("Syslog Priority")

    @property
    def sort_index(self):
        return 209

    def __init__(self):
        EventFilterState.__init__(self, "event", mkeventd.syslog_priorities)


@filter_registry.register
class FilterHistoryWhat(EventFilterState):
    @property
    def ident(self):
        return "history_what"

    @property
    def title(self):
        return _("History action type")

    @property
    def sort_index(self):
        return 225

    def __init__(self):
        EventFilterState.__init__(self, "history", [(k, k) for k in mkeventd.action_whats])


@filter_registry.register
class FilterEventFirst(FilterTime):
    @property
    def ident(self):
        return "event_first"

    @property
    def title(self):
        return _("First occurrence of event")

    @property
    def sort_index(self):
        return 220

    def __init__(self):
        FilterTime.__init__(self, "event", "event_first")


@filter_registry.register
class FilterEventLast(FilterTime):
    @property
    def ident(self):
        return "event_last"

    @property
    def title(self):
        return _("Last occurrance of event")

    @property
    def sort_index(self):
        return 221

    def __init__(self):
        FilterTime.__init__(self, "event", "event_last")


@filter_registry.register
class FilterHistoryTime(FilterTime):
    @property
    def ident(self):
        return "history_time"

    @property
    def title(self):
        return _("Time of entry in event history")

    @property
    def sort_index(self):
        return 222

    def __init__(self):
        FilterTime.__init__(self, "history", "history_time")


class EventFilterDropdown(Filter):
    def __init__(self, choices, operator='=', column=None):
        Filter.__init__(self, "event", [self.ident], ["event_" + column])
        self._choices = choices
        self._column = column
        self._operator = operator

    def display(self):
        if isinstance(self._choices, list):
            choices = self._choices
        else:
            choices = self._choices()
        html.dropdown(self.ident, [("", "")] + [(str(n), t) for (n, t) in choices])

    def filter(self, infoname):
        val = html.request.var(self.ident)
        if val:
            return "Filter: event_%s %s %s\n" % (self._column, self._operator, val)
        return ""


@filter_registry.register
class FilterEventFacility(EventFilterDropdown):
    @property
    def ident(self):
        return "event_facility"

    @property
    def title(self):
        return _("Syslog Facility")

    @property
    def sort_index(self):
        return 210

    def __init__(self):
        EventFilterDropdown.__init__(self, mkeventd.syslog_facilities, column="facility")


@filter_registry.register
class FilterEventSl(EventFilterDropdown):
    @property
    def ident(self):
        return "event_sl"

    @property
    def title(self):
        return _("Service Level at least")

    @property
    def sort_index(self):
        return 211

    def __init__(self):
        EventFilterDropdown.__init__(self, mkeventd.service_levels, operator='>=', column="sl")


@filter_registry.register
class FilterEventSlMax(EventFilterDropdown):
    @property
    def ident(self):
        return "event_sl_max"

    @property
    def title(self):
        return _("Service Level at most")

    @property
    def sort_index(self):
        return 211

    def __init__(self):
        EventFilterDropdown.__init__(self, mkeventd.service_levels, operator='<=', column="sl")


@filter_registry.register
class FilterOptEventEffectiveContactgroup(FilterGroupCombo):
    @property
    def ident(self):
        return "optevent_effective_contactgroup"

    @property
    def title(self):
        return _("Contact group (effective)")

    @property
    def sort_index(self):
        return 212

    def __init__(self):
        # TODO: Cleanup hierarchy here. The FilterGroupCombo constructor needs to be refactored
        FilterGroupCombo.__init__(
            self,
            what="event_effective_contact",
            enforce=False,
        )
        self.what = "contact"
        self.info = "event"
        self.link_columns = [
            "event_contact_groups", "event_contact_groups_precedence", "host_contact_groups"
        ]

    def filter(self, infoname):
        if not html.request.has_var(self.htmlvars[0]):
            return ""  # Skip if filter is not being set at all

        current_value = self.current_value()
        if not current_value:
            if not self.enforce:
                return ""
            current_value = sites.live().query_value(
                "GET contactgroups\nCache: reload\nColumns: name\nLimit: 1\n", None)

        if current_value is None:
            return ""  # no {what}group exists!

        if not self.enforce and html.request.var(self.htmlvars[1]):
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
