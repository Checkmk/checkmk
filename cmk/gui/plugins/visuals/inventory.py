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
import time

import cmk.gui.utils as utils
import cmk.gui.inventory as inventory
import cmk.utils.defines as defines
from cmk.gui.valuespec import (Age, DualListChoice)
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.exceptions import MKUserError

from cmk.gui.plugins.visuals import (
    filter_registry,
    Filter,
    FilterTristate,
    VisualInfo,
    visual_info_registry,
)


class FilterInvtableText(Filter):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def _invinfo(self):
        raise NotImplementedError()

    def __init__(self):
        super(FilterInvtableText, self).__init__(self._invinfo, [self.ident], [])

    def display(self):
        htmlvar = self.htmlvars[0]
        current_value = html.request.var(htmlvar, "")
        html.text_input(htmlvar, current_value)

    def filter_table(self, rows):
        htmlvar = self.htmlvars[0]
        filtertext = html.request.var(htmlvar, "").strip().lower()
        if not filtertext:
            return rows

        try:
            regex = re.compile(filtertext, re.IGNORECASE)
        except re.error:
            raise MKUserError(
                htmlvar,
                _('You search statement is not valid. You need to provide a regular '
                  'expression (regex). For example you need to use <tt>\\\\</tt> instead of <tt>\\</tt> '
                  'if you like to search for a single backslash.'))

        newrows = []
        for row in rows:
            if regex.search(row.get(htmlvar, "")):
                newrows.append(row)
        return newrows


class FilterInvtableTimestampAsAge(Filter):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def _invinfo(self):
        raise NotImplementedError()

    def __init__(self):
        self._from_varprefix = self.ident + "_from"
        self._to_varprefix = self.ident + "_to"
        Filter.__init__(self, self._invinfo,
                        [self._from_varprefix + "_days", self._to_varprefix + "_days"], [])

    def display(self):
        html.open_table()

        html.open_tr()
        html.td("%s:" % _("from"), style="vertical-align: middle;")
        html.open_td()
        self._valuespec().render_input(self._from_varprefix, 0)
        html.close_td()
        html.close_tr()

        html.open_tr()
        html.td("%s:" % _("to"), style="vertical-align: middle;")
        html.open_td()
        self._valuespec().render_input(self._to_varprefix, 0)
        html.close_td()
        html.close_tr()

        html.close_table()

    def _valuespec(self):
        return Age(display=["days"])

    def double_height(self):
        return True

    def filter_table_with_conversion(self, rows, conv):
        from_value = self._valuespec().from_html_vars(self._from_varprefix)
        to_value = self._valuespec().from_html_vars(self._to_varprefix)
        if not from_value and not to_value:
            return rows

        newrows = []
        for row in rows:
            value = row.get(self.ident, None)
            if value is not None:
                age = conv(value)
                if from_value and age < from_value:
                    continue

                if to_value and age > to_value:
                    continue
                newrows.append(row)
        return newrows

    def filter_table(self, rows):
        now = time.time()
        return self.filter_table_with_conversion(rows, lambda timestamp: now - timestamp)


# Filter for choosing a range in which a certain integer lies
class FilterInvtableIDRange(Filter):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def _invinfo(self):
        raise NotImplementedError()

    def __init__(self):
        Filter.__init__(self, self._invinfo, [self.ident + "_from", self.ident + "_to"], [])

    def display(self):
        html.write_text(_("from:") + " ")
        html.number_input(self.ident + "_from")
        html.write_text("&nbsp; %s: " % _("to"))
        html.number_input(self.ident + "_to")

    def filter_table(self, rows):
        from_value = utils.saveint(html.request.var(self.ident + "_from"))
        to_value = utils.saveint(html.request.var(self.ident + "_to"))

        if not from_value and not to_value:
            return rows

        newrows = []
        for row in rows:
            value = row.get(self.ident, None)
            if value is not None:
                if from_value and value < from_value:
                    continue

                if to_value and value > to_value:
                    continue
                newrows.append(row)
        return newrows


class FilterInvtableOperStatus(Filter):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def _invinfo(self):
        raise NotImplementedError()

    def __init__(self):
        varnames = [self.ident + "_" + str(x) for x in defines.interface_oper_states()]
        Filter.__init__(self, self._invinfo, varnames, [])

    def display(self):
        html.begin_checkbox_group()
        for state, state_name in sorted(defines.interface_oper_states().items()):
            if state >= 8:
                continue  # skip artificial state 8 (degraded) and 9 (admin down)
            varname = self.ident + "_" + str(state)
            html.checkbox(varname, True, label=state_name)
            if state in (4, 7):
                html.br()
        html.end_checkbox_group()

    def double_height(self):
        return True

    def filter_table(self, rows):
        # We consider the filter active if not all checkboxes
        # are either on (default) or off (unset)
        settings = set([])
        for varname in self.htmlvars:
            settings.add(html.request.var(varname))
        if len(settings) == 1:
            return rows

        new_rows = []
        for row in rows:
            oper_status = row["invinterface_oper_status"]
            varname = "%s_%d" % (self.ident, oper_status)
            if html.get_checkbox(varname):
                new_rows.append(row)
        return new_rows


class FilterInvtableAdminStatus(Filter):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def _invinfo(self):
        raise NotImplementedError()

    def __init__(self):
        Filter.__init__(self, self._invinfo, [self.ident], [])

    def display(self):
        html.begin_radio_group(horizontal=True)
        for value, text in [("1", _("up")), ("2", _("down")), ("-1", _("(ignore)"))]:
            html.radiobutton(self.ident, value, value == "-1", text + " &nbsp; ")
        html.end_radio_group()

    def filter_table(self, rows):
        current = html.request.var(self.ident)
        if current not in ("1", "2"):
            return rows

        new_rows = []
        for row in rows:
            admin_status = str(row["invinterface_admin_status"])
            if admin_status == current:
                new_rows.append(row)
        return new_rows


class FilterInvtableAvailable(Filter):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def _invinfo(self):
        raise NotImplementedError()

    def __init__(self):
        Filter.__init__(self, self._invinfo, [self.ident], [])

    def display(self):
        html.begin_radio_group(horizontal=True)
        for value, text in [("no", _("used")), ("yes", _("free")), ("", _("(ignore)"))]:
            html.radiobutton(self.ident, value, value == "", text + " &nbsp; ")
        html.end_radio_group()

    def filter_table(self, rows):
        current = html.request.var(self.ident)
        if current not in ("no", "yes"):
            return rows

        f = current == "yes"

        new_rows = []
        for row in rows:
            available = row.get("invinterface_available")
            if available == f:
                new_rows.append(row)
        return new_rows


class FilterInvtableInterfaceType(Filter):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def _invinfo(self):
        raise NotImplementedError()

    def __init__(self):
        Filter.__init__(self, self._invinfo, [self.ident], [])

    def double_height(self):
        return True

    def valuespec(self):
        return DualListChoice(
            choices=defines.interface_port_types(),
            rows=4,
            enlarge_active=True,
            custom_order=True,
        )

    def selection(self):
        current = html.request.var(self.ident, "").strip().split("|")
        if current == ['']:
            return []
        return current

    def display(self):
        html.open_div(class_="multigroup")
        self.valuespec().render_input(self.ident, self.selection())
        html.close_div()

    def filter_table(self, rows):
        current = self.selection()
        if len(current) == 0:
            return rows  # No types selected, filter is unused
        new_rows = []
        for row in rows:
            if str(row[self.ident]) in current:
                new_rows.append(row)
        return new_rows


class FilterInvtableVersion(Filter):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def _invinfo(self):
        raise NotImplementedError()

    def __init__(self):
        Filter.__init__(self, self._invinfo, [self.ident + "_from", self.ident + "_to"], [])

    def display(self):
        html.write_text(_("Min.&nbsp;Version:"))
        html.text_input(self.htmlvars[0], size=9)
        html.write_text(" &nbsp; ")
        html.write_text(_("Max.&nbsp;Version:"))
        html.text_input(self.htmlvars[1], size=9)

    def filter_table(self, rows):
        from_version = html.request.var(self.htmlvars[0])
        to_version = html.request.var(self.htmlvars[1])
        if not from_version and not to_version:
            return rows  # Filter not used

        new_rows = []
        for row in rows:
            version = row.get(self.ident, "")
            if from_version and utils.cmp_version(version, from_version) == -1:
                continue
            if to_version and utils.cmp_version(version, to_version) == 1:
                continue
            new_rows.append(row)

        return new_rows


class FilterInvText(Filter):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def _invpath(self):
        raise NotImplementedError()

    def __init__(self):
        Filter.__init__(self, "host", [self.ident], [])

    @property
    def filtertext(self):
        "Returns the string to filter"
        return html.request.var(self.htmlvars[0], "").strip().lower()

    def need_inventory(self):
        return bool(self.filtertext)

    def display(self):
        htmlvar = self.htmlvars[0]
        current_value = html.request.var(htmlvar, "")
        html.text_input(htmlvar, current_value)

    def filter_table(self, rows):
        filtertext = self.filtertext
        if not filtertext:
            return rows

        try:
            regex = re.compile(filtertext, re.IGNORECASE)
        except re.error:
            raise MKUserError(
                self.htmlvars[0],
                _('You search statement is not valid. You need to provide a regular '
                  'expression (regex). For example you need to use <tt>\\\\</tt> instead of <tt>\\</tt> '
                  'if you like to search for a single backslash.'))

        newrows = []
        for row in rows:
            invdata = inventory.get_inventory_data(row["host_inventory"], self._invpath)
            if invdata is None:
                invdata = ""
            if regex.search(invdata):
                newrows.append(row)
        return newrows


class FilterInvFloat(Filter):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def _invpath(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def _unit(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def _scale(self):
        raise NotImplementedError()

    def __init__(self):
        Filter.__init__(self, "host", [self.ident + "_from", self.ident + "_to"], [])

    def display(self):
        html.write_text(_("From: "))
        htmlvar = self.htmlvars[0]
        current_value = html.request.var(htmlvar, "")
        html.number_input(htmlvar, current_value)
        if self._unit:
            html.write(self._unit)

        html.write_text("&nbsp;&nbsp;" + _("To: "))
        htmlvar = self.htmlvars[1]
        current_value = html.request.var(htmlvar, "")
        html.number_input(htmlvar, current_value)
        if self._unit:
            html.write(self._unit)

    def filter_configs(self):
        "Returns scaled lower and upper bounds"

        def _scaled_bound(value):
            try:
                return float(html.request.var(value)) * self._scale
            except (TypeError, ValueError):
                return None

        return [_scaled_bound(val) for val in self.htmlvars[:2]]

    def need_inventory(self):
        return any(self.filter_configs())

    def filter_table(self, rows):
        lower, upper = self.filter_configs()
        if not any((lower, upper)):
            return rows

        newrows = []
        for row in rows:
            invdata = inventory.get_inventory_data(row["host_inventory"], self._invpath)
            if lower is not None and invdata < lower:
                continue
            if upper is not None and invdata > upper:
                continue
            newrows.append(row)
        return newrows


class FilterInvBool(FilterTristate):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def _invpath(self):
        raise NotImplementedError()

    def __init__(self):
        FilterTristate.__init__(self, "host", self.ident)

    def need_inventory(self):
        return self.tristate_value() != -1

    def filter(self, infoname):
        return ""  # No Livestatus filtering right now

    def filter_table(self, rows):
        tri = self.tristate_value()
        if tri == -1:
            return rows

        wanted_value = tri == 1
        newrows = []
        for row in rows:
            invdata = inventory.get_inventory_data(row["host_inventory"], self._invpath)
            if wanted_value == invdata:
                newrows.append(row)
        return newrows


@filter_registry.register
class FilterHasInv(FilterTristate):
    @property
    def ident(self):
        return "has_inv"

    @property
    def title(self):
        return _("Has Inventory Data")

    @property
    def sort_index(self):
        return 801

    def __init__(self):
        FilterTristate.__init__(self, "host", "host_inventory")

    def need_inventory(self):
        return self.tristate_value() != -1

    def filter(self, infoname):
        return ""  # No Livestatus filtering right now

    def filter_table(self, rows):
        tri = self.tristate_value()
        if tri == -1:
            return rows
        elif tri == 1:
            return [row for row in rows if row["host_inventory"]]

        # not
        return [row for row in rows if not row["host_inventory"]]


@filter_registry.register
class FilterInvHasSoftwarePackage(Filter):
    @property
    def ident(self):
        return "invswpac"

    @property
    def title(self):
        return _("Host has software package")

    @property
    def sort_index(self):
        return 801

    def __init__(self):
        self._varprefix = "invswpac_host_"
        Filter.__init__(self, "host", [
            self._varprefix + "name",
            self._varprefix + "version_from",
            self._varprefix + "version_to",
            self._varprefix + "negate",
        ], [])

    def double_height(self):
        return True

    @property
    def filtername(self):
        return html.get_unicode_input(self._varprefix + "name")

    def need_inventory(self):
        return bool(self.filtername)

    def display(self):
        html.text_input(self._varprefix + "name")
        html.br()
        html.begin_radio_group(horizontal=True)
        html.radiobutton(self._varprefix + "match", "exact", True, label=_("exact match"))
        html.radiobutton(self._varprefix + "match",
                         "regex",
                         False,
                         label=_("regular expression, substring match"))
        html.end_radio_group()
        html.br()
        html.write_text(_("Min.&nbsp;Version:"))
        html.text_input(self._varprefix + "version_from", size=9)
        html.write_text(" &nbsp; ")
        html.write_text(_("Max.&nbsp;Vers.:"))
        html.text_input(self._varprefix + "version_to", size=9)
        html.br()
        html.checkbox(self._varprefix + "negate",
                      False,
                      label=_("Negate: find hosts <b>not</b> having this package"))

    def filter_table(self, rows):
        name = self.filtername
        if not name:
            return rows

        from_version = html.request.var(self._varprefix + "from_version")
        to_version = html.request.var(self._varprefix + "to_version")
        negate = html.get_checkbox(self._varprefix + "negate")
        match = html.request.var(self._varprefix + "match")
        if match == "regex":
            try:
                name = re.compile(name)
            except re.error:
                raise MKUserError(
                    self._varprefix + "name",
                    _('You search statement is not valid. You need to provide a regular '
                      'expression (regex). For example you need to use <tt>\\\\</tt> instead of <tt>\\</tt> '
                      'if you like to search for a single backslash.'))

        new_rows = []
        for row in rows:
            packages_numeration = row["host_inventory"].get_sub_numeration(["software", "packages"])
            if packages_numeration is None:
                continue
            packages = packages_numeration.get_child_data()
            is_in = self.find_package(packages, name, from_version, to_version)
            if is_in != negate:
                new_rows.append(row)
        return new_rows

    def find_package(self, packages, name, from_version, to_version):
        for package in packages:
            if isinstance(name, unicode):
                if package["name"] != name:
                    continue
            else:
                if not name.search(package["name"]):
                    continue
            if not from_version and not to_version:
                return True  # version not relevant
            version = package["version"]
            if from_version == to_version and from_version != version:
                continue
            if from_version and self.version_is_lower(version, from_version):
                continue
            if to_version and self.version_is_higher(version, to_version):
                continue
        return False

    def version_is_lower(self, a, b):
        return a != b and not self.version_is_higher(a, b)

    def version_is_higher(self, a, b):
        return utils.cmp_version(a, b) == 1


@visual_info_registry.register
class VisualInfoHost(VisualInfo):
    @property
    def ident(self):
        return "invhist"

    @property
    def title(self):
        return _("Inventory History")

    @property
    def title_plural(self):
        return _("Inventory Historys")

    @property
    def single_spec(self):
        return None
