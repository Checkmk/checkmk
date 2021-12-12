#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
import time
from typing import List, Optional, Tuple, Union

import cmk.utils.defines as defines

import cmk.gui.inventory as inventory
import cmk.gui.legacy_filters as legacy_filters
import cmk.gui.utils as utils
from cmk.gui.exceptions import MKUserError
from cmk.gui.globals import html
from cmk.gui.i18n import _, _l
from cmk.gui.plugins.visuals.utils import (
    display_filter_radiobuttons,
    Filter,
    filter_registry,
    FilterOption,
    visual_info_registry,
    VisualInfo,
)
from cmk.gui.type_defs import FilterHeader, FilterHTTPVariables, Rows, VisualContext
from cmk.gui.valuespec import Age, DualListChoice, ValueSpec


class FilterInvtableText(Filter):
    def __init__(self, *, inv_info: str, ident: str, title: str) -> None:
        super().__init__(
            ident=ident,
            title=title,
            sort_index=800,
            info=inv_info,
            htmlvars=[ident],
            link_columns=[],
        )

    def display(self, value: FilterHTTPVariables) -> None:
        htmlvar = self.htmlvars[0]
        html.text_input(htmlvar, value.get(htmlvar, ""))

    def filter_table(self, context: VisualContext, rows: Rows) -> Rows:
        value = context.get(self.ident, {})
        assert not isinstance(value, str)
        htmlvar = self.htmlvars[0]
        filtertext = value.get(htmlvar, "").strip().lower()
        if not filtertext:
            return rows

        try:
            regex = re.compile(filtertext, re.IGNORECASE)
        except re.error:
            raise MKUserError(
                htmlvar,
                _(
                    "Your search statement is not valid. You need to provide a regular "
                    "expression (regex). For example you need to use <tt>\\\\</tt> instead of <tt>\\</tt> "
                    "if you like to search for a single backslash."
                ),
            )

        return [row for row in rows if regex.search(row.get(htmlvar, ""))]


class FilterInvtableTimestampAsAge(Filter):
    def __init__(self, *, inv_info: str, ident: str, title: str) -> None:
        self._from_varprefix = ident + "_from"
        self._to_varprefix = ident + "_to"
        super().__init__(
            ident=ident,
            title=title,
            sort_index=800,
            info=inv_info,
            htmlvars=[self._from_varprefix + "_days", self._to_varprefix + "_days"],
            link_columns=[],
        )

    def display(self, value: FilterHTTPVariables) -> None:
        html.open_table()

        from_value, to_value = (self._days_to_seconds(value.get(v, "")) for v in self.htmlvars)
        html.open_tr()
        html.td("%s:" % _("from"), style="vertical-align: middle;")
        html.open_td()
        self._valuespec().render_input(self._from_varprefix, from_value)
        html.close_td()
        html.close_tr()

        html.open_tr()
        html.td("%s:" % _("to"), style="vertical-align: middle;")
        html.open_td()
        self._valuespec().render_input(self._to_varprefix, to_value)
        html.close_td()
        html.close_tr()

        html.close_table()

    def _valuespec(self) -> ValueSpec:
        return Age(display=["days"])

    @staticmethod
    def _days_to_seconds(value: str) -> int:
        try:
            return int(value) * 3600 * 24
        except ValueError:
            return 0

    def filter_table(self, context: VisualContext, rows: Rows) -> Rows:

        values = context.get(self.ident, {})
        assert not isinstance(values, str)
        from_value, to_value = (self._days_to_seconds(values.get(v, "")) for v in self.htmlvars)

        if not from_value and not to_value:
            return rows

        now = time.time()
        newrows = []
        for row in rows:
            value = row.get(self.ident, None)
            if value is not None:
                age = now - value
                if from_value and age < from_value:
                    continue

                if to_value and age > to_value:
                    continue
                newrows.append(row)
        return newrows


class FilterInvtableIDRange(Filter):
    """Filter for choosing a range in which a certain integer lies"""

    def __init__(self, *, inv_info: str, ident: str, title: str) -> None:
        super().__init__(
            ident=ident,
            title=title,
            sort_index=800,
            info=inv_info,
            htmlvars=[ident + "_from", ident + "_to"],
            link_columns=[],
        )

    def display(self, value: FilterHTTPVariables) -> None:
        html.write_text(_("from:") + " ")
        html.text_input(
            self.ident + "_from",
            default_value=value.get(self.ident + "_from", ""),
            size=8,
            cssclass="number",
        )
        html.write_text("&nbsp; %s: " % _("to"))
        html.text_input(
            self.ident + "_to",
            default_value=value.get(self.ident + "_to", ""),
            size=8,
            cssclass="number",
        )

    def filter_table(self, context: VisualContext, rows: Rows) -> Rows:
        values = context.get(self.ident, {})
        assert not isinstance(values, str)
        from_value, to_value = (utils.saveint(values.get(v, 0)) for v in self.htmlvars)

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
    def __init__(self, *, inv_info: str, ident: str, title: str) -> None:
        super().__init__(
            ident=ident,
            title=title,
            sort_index=800,
            info=inv_info,
            htmlvars=[ident + "_" + str(x) for x in defines.interface_oper_states()],
            link_columns=[],
        )

    def display(self, value: FilterHTTPVariables) -> None:
        html.begin_checkbox_group()
        for state, state_name in sorted(defines.interface_oper_states().items()):
            if not isinstance(state, int):  # needed because of silly types
                continue
            if state >= 8:
                continue  # skip artificial state 8 (degraded) and 9 (admin down)
            varname = self.ident + "_" + str(state)
            html.checkbox(varname, bool(value.get(varname, True)), label=state_name)
            if state in (4, 7):
                html.br()
        html.end_checkbox_group()

    def filter_table(self, context: VisualContext, rows: Rows) -> Rows:
        # We consider the filter active if not all checkboxes
        # are either on (default) or off (unset)
        values = context.get(self.ident, {})
        assert not isinstance(values, str)
        settings = {values.get(v, "") for v in self.htmlvars}
        if len(settings) == 1:
            return rows

        return [
            row
            for row in rows
            if values.get("%s_%d" % (self.ident, row["invinterface_oper_status"]), "")
        ]


class FilterInvtableAdminStatus(Filter):
    def __init__(self, *, inv_info: str, ident: str, title: str) -> None:
        super().__init__(
            ident=ident,
            title=title,
            sort_index=800,
            info=inv_info,
            htmlvars=[ident],
            link_columns=[],
        )

    def display(self, value: FilterHTTPVariables) -> None:
        display_filter_radiobuttons(
            varname=self.ident,
            options=[
                ("1", _("up")),
                ("2", _("down")),
                ("-1", _("(ignore)")),
            ],
            default="-1",
            value=value,
        )

    def filter_table(self, context: VisualContext, rows: Rows) -> Rows:
        values = context.get(self.ident, {})
        assert not isinstance(values, str)
        current = values.get(self.ident, "-1")
        if current == "-1":
            return rows

        return [row for row in rows if str(row["invinterface_admin_status"]) == current]


class FilterInvtableAvailable(Filter):
    def __init__(self, *, inv_info: str, ident: str, title: str) -> None:
        super().__init__(
            ident=ident,
            title=title,
            sort_index=800,
            info=inv_info,
            htmlvars=[ident],
            link_columns=[],
        )

    def display(self, value: FilterHTTPVariables) -> None:
        display_filter_radiobuttons(
            varname=self.ident,
            options=[
                ("no", _("used")),
                ("yes", _("free")),
                ("", _("(ignore)")),
            ],
            default="",
            value=value,
        )

    def filter_table(self, context: VisualContext, rows: Rows) -> Rows:
        value = context.get(self.ident, {})
        current = value if isinstance(value, str) else value.get(self.ident, "")

        if current not in ("no", "yes"):
            return rows

        return [row for row in rows if (current == "yes") == row.get("invinterface_available")]


class FilterInvtableInterfaceType(Filter):
    def __init__(self, *, inv_info: str, ident: str, title: str) -> None:
        super().__init__(
            ident=ident,
            title=title,
            sort_index=800,
            info=inv_info,
            htmlvars=[ident],
            link_columns=[],
        )

    def valuespec(self) -> ValueSpec:
        sorted_choices = [
            (str(k), str(v))
            for k, v in sorted(defines.interface_port_types().items(), key=lambda t: t[0])
        ]
        return DualListChoice(
            choices=sorted_choices,
            rows=4,
            enlarge_active=True,
            custom_order=True,
        )

    def selection(self, value: FilterHTTPVariables) -> List[str]:
        current = value.get(self.ident, "").strip().split("|")
        if current == [""]:
            return []
        return current

    def display(self, value: FilterHTTPVariables) -> None:
        html.open_div(class_="multigroup")
        self.valuespec().render_input(self.ident, self.selection(value))
        html.close_div()

    def filter_table(self, context: VisualContext, rows: Rows) -> Rows:
        value = context.get(self.ident, {})
        assert not isinstance(value, str)
        current = self.selection(value)
        if len(current) == 0:
            return rows  # No types selected, filter is unused
        return [row for row in rows if str(row[self.ident]) in current]


class FilterInvtableVersion(Filter):
    def __init__(self, *, inv_info: str, ident: str, title: str) -> None:
        super().__init__(
            ident=ident,
            title=title,
            sort_index=800,
            info=inv_info,
            htmlvars=[ident + "_from", ident + "_to"],
            link_columns=[],
        )

    def display(self, value: FilterHTTPVariables) -> None:
        html.write_text(_("Min.&nbsp;Version:"))
        html.text_input(self.htmlvars[0], default_value=value.get(self.htmlvars[0], ""), size=7)
        html.write_text(" &nbsp; ")
        html.write_text(_("Max.&nbsp;Version:"))
        html.text_input(self.htmlvars[1], default_value=value.get(self.htmlvars[1], ""), size=7)

    def filter_table(self, context: VisualContext, rows: Rows) -> Rows:
        values = context.get(self.ident, {})
        assert not isinstance(values, str)
        from_version, to_version = (values.get(v) for v in self.htmlvars)
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
    def __init__(self, *, ident: str, title: str, inv_path: str, is_show_more: bool = True) -> None:
        super().__init__(
            ident=ident,
            title=title,
            sort_index=800,
            info="host",
            htmlvars=[ident],
            link_columns=[],
            is_show_more=is_show_more,
        )
        self._invpath = inv_path

    def filtertext(self, value: FilterHTTPVariables) -> FilterHeader:
        "Returns the string to filter"
        return value.get(self.htmlvars[0], "").strip().lower()

    def need_inventory(self, value) -> bool:
        return bool(self.filtertext(value))

    def display(self, value: FilterHTTPVariables) -> None:
        htmlvar = self.htmlvars[0]
        html.text_input(htmlvar, value[htmlvar] if value else "")

    def filter_table(self, context: VisualContext, rows: Rows) -> Rows:
        values = context.get(self.ident, {})
        assert not isinstance(values, str)
        filtertext = self.filtertext(values)
        if not filtertext:
            return rows

        try:
            regex = re.compile(filtertext, re.IGNORECASE)
        except re.error:
            raise MKUserError(
                self.htmlvars[0],
                _(
                    "Your search statement is not valid. You need to provide a regular "
                    "expression (regex). For example you need to use <tt>\\\\</tt> instead of <tt>\\</tt> "
                    "if you like to search for a single backslash."
                ),
            )

        newrows = []
        for row in rows:
            invdata = inventory.get_inventory_attribute(row["host_inventory"], self._invpath)
            if not isinstance(invdata, str):
                invdata = ""
            if regex.search(invdata):
                newrows.append(row)
        return newrows


class FilterInvFloat(Filter):
    def __init__(
        self,
        *,
        ident: str,
        title: str,
        inv_path: str,
        unit: Optional[str],
        scale: Optional[float],
        is_show_more: bool = True,
    ) -> None:
        super().__init__(
            ident=ident,
            title=title,
            sort_index=800,
            info="host",
            htmlvars=[ident + "_from", ident + "_to"],
            link_columns=[],
            is_show_more=is_show_more,
        )
        self._invpath = inv_path
        self._unit = unit
        self._scale = scale if scale is not None else 1.0

    def display(self, value: FilterHTTPVariables) -> None:
        html.write_text(_("From: "))
        htmlvar = self.htmlvars[0]
        current_value = value.get(htmlvar, "")
        html.text_input(htmlvar, default_value=current_value, size=8, cssclass="number")
        if self._unit:
            html.write_text(" %s" % self._unit)

        html.write_text("&nbsp;&nbsp;" + _("To: "))
        htmlvar = self.htmlvars[1]
        current_value = value.get(htmlvar, "")
        html.text_input(htmlvar, default_value=current_value, size=8, cssclass="number")
        if self._unit:
            html.write_text(" %s" % self._unit)

    def filter_configs(self, values: FilterHTTPVariables) -> List[Optional[float]]:
        "Returns scaled lower and upper bounds"

        def _scaled_bound(name) -> Optional[float]:
            try:
                return float(values.get(name, "")) * self._scale
            except ValueError:
                return None

        return [_scaled_bound(name) for name in self.htmlvars[:2]]

    def need_inventory(self, value) -> bool:
        return any(self.filter_configs(value))

    def filter_table(self, context: VisualContext, rows: Rows) -> Rows:
        values = context.get(self.ident, {})
        assert not isinstance(values, str)
        lower, upper = self.filter_configs(values)
        if not any((lower, upper)):
            return rows

        newrows = []
        for row in rows:
            invdata = inventory.get_inventory_attribute(row["host_inventory"], self._invpath)
            if not isinstance(invdata, (int, float)):
                continue
            if lower is not None and invdata < lower:
                continue
            if upper is not None and invdata > upper:
                continue
            newrows.append(row)
        return newrows


class FilterInvBool(FilterOption):
    def __init__(self, *, ident: str, title: str, inv_path: str, is_show_more: bool = True) -> None:
        super().__init__(
            ident=ident,
            title=title,
            sort_index=800,
            info="host",
            legacy_filter=legacy_filters.FilterTristate(
                ident=ident,
                filter_code=lambda x: "",  # No Livestatus filtering right now
                filter_rows=legacy_filters.inside_inventory(inv_path),
            ),
            is_show_more=is_show_more,
        )

    def need_inventory(self, value) -> bool:
        return self.legacy_filter.selection_value(value) != self.legacy_filter.ignore


@filter_registry.register_instance
class FilterHasInv(FilterOption):
    def __init__(self) -> None:
        super().__init__(
            ident="has_inv",
            title=_l("Has Inventory Data"),
            sort_index=801,
            info="host",
            legacy_filter=legacy_filters.FilterTristate(
                ident="has_inv",
                filter_code=lambda x: "",  # No Livestatus filtering right now
                filter_rows=legacy_filters.has_inventory,
            ),
            is_show_more=True,
        )

    def need_inventory(self, value) -> bool:
        return self.legacy_filter.selection_value(value) != self.legacy_filter.ignore


@filter_registry.register_instance
class FilterInvHasSoftwarePackage(Filter):
    def __init__(self) -> None:
        self._varprefix = "invswpac_host_"
        super().__init__(
            ident="invswpac",
            title=_l("Host has software package"),
            sort_index=801,
            info="host",
            htmlvars=[
                self._varprefix + "name",
                self._varprefix + "version_from",
                self._varprefix + "version_to",
                self._varprefix + "negate",
                self._varprefix + "match",
            ],
            link_columns=[],
            is_show_more=True,
        )

    def need_inventory(self, value: FilterHTTPVariables) -> bool:
        return bool(value.get(self._varprefix + "name"))

    def display(self, value: FilterHTTPVariables) -> None:
        html.text_input(self._varprefix + "name")
        html.br()
        display_filter_radiobuttons(
            varname=self._varprefix + "match",
            options=[
                ("exact", _("exact match")),
                ("regex", _("regular expression, substring match")),
            ],
            default="exact",
            value=value,
        )
        html.br()
        html.open_span(class_="min_max_row")
        html.write_text(_("Min.&nbsp;Version: "))
        html.text_input(
            self._varprefix + "version_from",
            default_value=value.get(self._varprefix + "version_from", ""),
            size=9,
        )
        html.write_text(" &nbsp; ")
        html.write_text(_("Max.&nbsp;Vers.: "))
        html.text_input(
            self._varprefix + "version_to",
            default_value=value.get(self._varprefix + "version_from", ""),
            size=9,
        )
        html.close_span()
        html.br()
        html.checkbox(
            self._varprefix + "negate",
            False,
            label=_("Negate: find hosts <b>not</b> having this package"),
        )

    def filter_table(self, context: VisualContext, rows: Rows) -> Rows:
        value = context.get(self.ident, {})
        assert not isinstance(value, str)
        name: Union[str, re.Pattern] = value.get(self._varprefix + "name", "")
        if not name:
            return rows

        from_version = value[self._varprefix + "from_version"]
        to_version = value[self._varprefix + "to_version"]
        negate = bool(value[self._varprefix + "negate"])
        match = value[self._varprefix + "match"]
        if match == "regex":
            try:
                name = re.compile(name)
            except re.error:
                raise MKUserError(
                    self._varprefix + "name",
                    _(
                        "Your search statement is not valid. You need to provide a regular "
                        "expression (regex). For example you need to use <tt>\\\\</tt> instead of <tt>\\</tt> "
                        "if you like to search for a single backslash."
                    ),
                )

        new_rows = []
        for row in rows:
            packages_table = row["host_inventory"].get_table(["software", "packages"])
            if packages_table is None:
                continue
            packages = packages_table.data
            is_in = self.find_package(packages, name, from_version, to_version)
            if is_in != negate:
                new_rows.append(row)
        return new_rows

    def find_package(self, packages, name, from_version, to_version):
        for package in packages:
            if isinstance(name, str):
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

    def version_is_lower(self, a: Optional[str], b: Optional[str]) -> bool:
        return a != b and not self.version_is_higher(a, b)

    def version_is_higher(self, a: Optional[str], b: Optional[str]) -> bool:
        return utils.cmp_version(a, b) == 1


@visual_info_registry.register
class VisualInfoHost(VisualInfo):
    @property
    def ident(self) -> str:
        return "invhist"

    @property
    def title(self) -> str:
        return _("Inventory History")

    @property
    def title_plural(self) -> str:
        return _("Inventory Historys")

    @property
    def single_spec(self) -> List[Tuple[str, ValueSpec]]:
        return []
