#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import re
import time
from typing import (  # pylint: disable=unused-import
    Text, List, Optional, Tuple, Callable,
)
import six

import cmk.gui.utils as utils
import cmk.gui.inventory as inventory
import cmk.utils.defines as defines
from cmk.gui.valuespec import (  # pylint: disable=unused-import
    Age, DualListChoice, ValueSpec,
)
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
from cmk.gui.type_defs import (  # pylint: disable=unused-import
    Rows,)


class FilterInvtableText(six.with_metaclass(abc.ABCMeta, Filter)):
    @abc.abstractproperty
    def _invinfo(self):
        # type: () -> str
        raise NotImplementedError()

    def __init__(self):
        # type: () -> None
        super(FilterInvtableText, self).__init__(self._invinfo, [self.ident], [])

    def display(self):
        # type: () -> None
        htmlvar = self.htmlvars[0]
        value = html.request.get_unicode_input(htmlvar)
        if value is not None:
            html.text_input(htmlvar, value)

    def filter_table(self, rows):
        # type: (Rows) -> Rows
        htmlvar = self.htmlvars[0]
        request_var = html.request.var(htmlvar)
        if request_var is None:
            return rows

        filtertext = request_var.strip().lower()
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


class FilterInvtableTimestampAsAge(six.with_metaclass(abc.ABCMeta, Filter)):
    @abc.abstractproperty
    def _invinfo(self):
        # type: () -> str
        raise NotImplementedError()

    def __init__(self):
        # type: () -> None
        self._from_varprefix = self.ident + "_from"
        self._to_varprefix = self.ident + "_to"
        super(FilterInvtableTimestampAsAge,
              self).__init__(self._invinfo,
                             [self._from_varprefix + "_days", self._to_varprefix + "_days"], [])

    def display(self):
        # type: () -> None
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
        # type: () -> ValueSpec
        return Age(display=["days"])

    def double_height(self):
        # type: () -> bool
        return True

    def filter_table_with_conversion(self, rows, conv):
        # type: (Rows, Callable[[float], float]) -> Rows
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
        # type: (Rows) -> Rows
        now = time.time()
        return self.filter_table_with_conversion(rows, lambda timestamp: now - timestamp)


# Filter for choosing a range in which a certain integer lies
class FilterInvtableIDRange(six.with_metaclass(abc.ABCMeta, Filter)):
    @abc.abstractproperty
    def _invinfo(self):
        # type: () -> str
        raise NotImplementedError()

    def __init__(self):
        # type: () -> None
        super(FilterInvtableIDRange, self).__init__(self._invinfo,
                                                    [self.ident + "_from", self.ident + "_to"], [])

    def display(self):
        # type: () -> None
        html.write_text(_("from:") + " ")
        html.text_input(self.ident + "_from", size=8, cssclass="number")
        html.write_text("&nbsp; %s: " % _("to"))
        html.text_input(self.ident + "_to", size=8, cssclass="number")

    def filter_table(self, rows):
        # type: (Rows) -> Rows
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


class FilterInvtableOperStatus(six.with_metaclass(abc.ABCMeta, Filter)):
    @abc.abstractproperty
    def _invinfo(self):
        # type: () -> str
        raise NotImplementedError()

    def __init__(self):
        # type: () -> None
        varnames = [self.ident + "_" + str(x) for x in defines.interface_oper_states()]
        super(FilterInvtableOperStatus, self).__init__(self._invinfo, varnames, [])

    def display(self):
        # type: () -> None
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
        # type: () -> bool
        return True

    def filter_table(self, rows):
        # type: (Rows) -> Rows
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


class FilterInvtableAdminStatus(six.with_metaclass(abc.ABCMeta, Filter)):
    @abc.abstractproperty
    def _invinfo(self):
        # type: () -> str
        raise NotImplementedError()

    def __init__(self):
        # type: () -> None
        super(FilterInvtableAdminStatus, self).__init__(self._invinfo, [self.ident], [])

    def display(self):
        # type: () -> None
        html.begin_radio_group(horizontal=True)
        for value, text in [("1", _("up")), ("2", _("down")), ("-1", _("(ignore)"))]:
            html.radiobutton(self.ident, value, value == "-1", text + " &nbsp; ")
        html.end_radio_group()

    def filter_table(self, rows):
        # type: (Rows) -> Rows
        current = html.request.var(self.ident)
        if current not in ("1", "2"):
            return rows

        new_rows = []
        for row in rows:
            admin_status = str(row["invinterface_admin_status"])
            if admin_status == current:
                new_rows.append(row)
        return new_rows


class FilterInvtableAvailable(six.with_metaclass(abc.ABCMeta, Filter)):
    @abc.abstractproperty
    def _invinfo(self):
        # type: () -> str
        raise NotImplementedError()

    def __init__(self):
        # type: () -> None
        super(FilterInvtableAvailable, self).__init__(self._invinfo, [self.ident], [])

    def display(self):
        # type: () -> None
        html.begin_radio_group(horizontal=True)
        for value, text in [("no", _("used")), ("yes", _("free")), ("", _("(ignore)"))]:
            html.radiobutton(self.ident, value, value == "", text + " &nbsp; ")
        html.end_radio_group()

    def filter_table(self, rows):
        # type: (Rows) -> Rows
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


class FilterInvtableInterfaceType(six.with_metaclass(abc.ABCMeta, Filter)):
    @abc.abstractproperty
    def _invinfo(self):
        # type: () -> str
        raise NotImplementedError()

    def __init__(self):
        # type: () -> None
        super(FilterInvtableInterfaceType, self).__init__(self._invinfo, [self.ident], [])

    def double_height(self):
        # type: () -> bool
        return True

    def valuespec(self):
        # type: () -> ValueSpec
        sorted_choices = [
            (six.text_type(k), six.text_type(v))
            for k, v in sorted(defines.interface_port_types().items(), key=lambda t: t[0])
        ]
        return DualListChoice(
            choices=sorted_choices,
            rows=4,
            enlarge_active=True,
            custom_order=True,
        )

    def selection(self):
        # type: () -> List[str]
        request_var = html.request.var(self.ident)
        if request_var is None:
            return []
        current = request_var.strip().split("|")
        if current == ['']:
            return []
        return current

    def display(self):
        # type: () -> None
        html.open_div(class_="multigroup")
        self.valuespec().render_input(self.ident, self.selection())
        html.close_div()

    def filter_table(self, rows):
        # type: (Rows) -> Rows
        current = self.selection()
        if len(current) == 0:
            return rows  # No types selected, filter is unused
        new_rows = []
        for row in rows:
            if str(row[self.ident]) in current:
                new_rows.append(row)
        return new_rows


class FilterInvtableVersion(six.with_metaclass(abc.ABCMeta, Filter)):
    @abc.abstractproperty
    def _invinfo(self):
        # type: () -> str
        raise NotImplementedError()

    def __init__(self):
        # type: () -> None
        super(FilterInvtableVersion, self).__init__(self._invinfo,
                                                    [self.ident + "_from", self.ident + "_to"], [])

    def display(self):
        # type: () -> None
        html.write_text(_("Min.&nbsp;Version:"))
        html.text_input(self.htmlvars[0], size=7)
        html.write_text(" &nbsp; ")
        html.write_text(_("Max.&nbsp;Version:"))
        html.text_input(self.htmlvars[1], size=7)

    def filter_table(self, rows):
        # type: (Rows) -> Rows
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


class FilterInvText(six.with_metaclass(abc.ABCMeta, Filter)):
    @abc.abstractproperty
    def _invpath(self):
        raise NotImplementedError()

    def __init__(self):
        # type: () -> None
        super(FilterInvText, self).__init__("host", [self.ident], [])

    @property
    def filtertext(self):
        "Returns the string to filter"
        return html.request.get_str_input_mandatory(self.htmlvars[0], "").strip().lower()

    def need_inventory(self):
        # type: () -> bool
        return bool(self.filtertext)

    def display(self):
        # type: () -> None
        htmlvar = self.htmlvars[0]
        value = html.request.var(htmlvar)
        if value is not None:
            html.text_input(htmlvar, value)

    def filter_table(self, rows):
        # type: (Rows) -> Rows
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


class FilterInvFloat(six.with_metaclass(abc.ABCMeta, Filter)):
    @abc.abstractproperty
    def _invpath(self):
        raise NotImplementedError()

    @abc.abstractproperty
    def _unit(self):
        raise NotImplementedError()

    @abc.abstractproperty
    def _scale(self):
        raise NotImplementedError()

    def __init__(self):
        # type: () -> None
        super(FilterInvFloat, self).__init__("host", [self.ident + "_from", self.ident + "_to"], [])

    def display(self):
        # type: () -> None
        html.write_text(_("From: "))
        htmlvar = self.htmlvars[0]
        current_value = html.request.var(htmlvar, "")
        html.text_input(htmlvar, default_value=str(current_value), size=8, cssclass="number")
        if self._unit:
            html.write(self._unit)

        html.write_text("&nbsp;&nbsp;" + _("To: "))
        htmlvar = self.htmlvars[1]
        current_value = html.request.var(htmlvar, "")
        html.text_input(htmlvar, default_value=str(current_value), size=8, cssclass="number")
        if self._unit:
            html.write(self._unit)

    def filter_configs(self):
        "Returns scaled lower and upper bounds"

        def _scaled_bound(value):
            try:
                return html.request.get_float_input_mandatory(value) * self._scale
            except (TypeError, ValueError):
                return None

        return [_scaled_bound(val) for val in self.htmlvars[:2]]

    def need_inventory(self):
        # type: () -> bool
        return any(self.filter_configs())

    def filter_table(self, rows):
        # type: (Rows) -> Rows
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


class FilterInvBool(six.with_metaclass(abc.ABCMeta, FilterTristate)):
    @abc.abstractproperty
    def _invpath(self):
        raise NotImplementedError()

    def __init__(self):
        # type: () -> None
        super(FilterInvBool, self).__init__("host", self.ident)

    def need_inventory(self):
        # type: () -> bool
        return self.tristate_value() != -1

    def filter(self, infoname):
        return ""  # No Livestatus filtering right now

    def filter_table(self, rows):
        # type: (Rows) -> Rows
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
        # type: () -> str
        return "has_inv"

    @property
    def title(self):
        # type: () -> Text
        return _("Has Inventory Data")

    @property
    def sort_index(self):
        # type: () -> int
        return 801

    def __init__(self):
        # type: () -> None
        FilterTristate.__init__(self, "host", "host_inventory")

    def need_inventory(self):
        # type: () -> bool
        return self.tristate_value() != -1

    def filter(self, infoname):
        return ""  # No Livestatus filtering right now

    def filter_table(self, rows):
        # type: (Rows) -> Rows
        tri = self.tristate_value()
        if tri == -1:
            return rows
        if tri == 1:
            return [row for row in rows if row["host_inventory"]]
        # not
        return [row for row in rows if not row["host_inventory"]]


@filter_registry.register
class FilterInvHasSoftwarePackage(Filter):
    @property
    def ident(self):
        # type: () -> str
        return "invswpac"

    @property
    def title(self):
        # type: () -> Text
        return _("Host has software package")

    @property
    def sort_index(self):
        # type: () -> int
        return 801

    def __init__(self):
        # type: () -> None
        self._varprefix = "invswpac_host_"
        Filter.__init__(self, "host", [
            self._varprefix + "name",
            self._varprefix + "version_from",
            self._varprefix + "version_to",
            self._varprefix + "negate",
        ], [])

    def double_height(self):
        # type: () -> bool
        return True

    @property
    def filtername(self):
        return html.request.get_unicode_input(self._varprefix + "name")

    def need_inventory(self):
        # type: () -> bool
        return bool(self.filtername)

    def display(self):
        # type: () -> None
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
        # type: (Rows) -> Rows
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
            if isinstance(name, six.text_type):
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
        # type: (Optional[str], Optional[str]) -> bool
        return a != b and not self.version_is_higher(a, b)

    def version_is_higher(self, a, b):
        # type: (Optional[str], Optional[str]) -> bool
        return utils.cmp_version(a, b) == 1


@visual_info_registry.register
class VisualInfoHost(VisualInfo):
    @property
    def ident(self):
        # type: () -> str
        return "invhist"

    @property
    def title(self):
        # type: () -> Text
        return _("Inventory History")

    @property
    def title_plural(self):
        # type: () -> Text
        return _("Inventory Historys")

    @property
    def single_spec(self):
        # type: () -> Optional[Tuple[str, ValueSpec]]
        return None
