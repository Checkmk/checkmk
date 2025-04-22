#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from collections.abc import Callable
from functools import partial

from cmk.gui import query_filters
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _, _l
from cmk.gui.ifaceoper import interface_oper_states, interface_port_types
from cmk.gui.num_split import cmp_version
from cmk.gui.type_defs import FilterHeader, FilterHTTPVariables, Row, Rows, VisualContext
from cmk.gui.utils.speaklater import LazyString
from cmk.gui.visuals.filter import (
    CheckboxRowFilter,
    display_filter_radiobuttons,
    DualListFilter,
    Filter,
    FilterNumberRange,
    FilterOption,
    InputTextFilter,
)

from ._tree import InventoryPath


class FilterInvtableText(InputTextFilter):
    def __init__(self, *, inv_info: str, ident: str, title: str) -> None:
        super().__init__(
            title=title,
            sort_index=800,
            info=inv_info,
            query_filter=query_filters.TableTextQuery(
                ident=ident, row_filter=query_filters.filter_by_column_textregex
            ),
            show_heading=False,
        )


class FilterInvText(InputTextFilter):
    def __init__(
        self,
        *,
        ident: str,
        title: str,
        inventory_path: InventoryPath,
        is_show_more: bool = True,
    ) -> None:
        super().__init__(
            title=title,
            sort_index=800,
            info="host",
            query_filter=query_filters.TableTextQuery(
                ident=ident, row_filter=_filter_by_host_inventory(inventory_path)
            ),
            show_heading=False,
            is_show_more=is_show_more,
        )

    def need_inventory(self, value: FilterHTTPVariables) -> bool:
        return bool(value.get(self.htmlvars[0], "").strip().lower())


def _filter_by_host_inventory(
    inventory_path: InventoryPath,
) -> Callable[[str, str], Callable[[Row], bool]]:
    def row_filter(filtertext: str, column: str) -> Callable[[Row], bool]:
        regex = query_filters.re_ignorecase(filtertext, column)

        def filt(row: Row) -> bool:
            return bool(
                regex.search(
                    str(
                        row["host_inventory"].get_attribute(inventory_path.path, inventory_path.key)
                    )
                )
            )

        return filt

    return row_filter


class FilterInvtableTimestampAsAge(FilterNumberRange):
    def __init__(self, *, inv_info: str, ident: str, title: str) -> None:
        super().__init__(
            title=title,
            sort_index=800,
            info=inv_info,
            query_filter=query_filters.NumberRangeQuery(
                ident=ident,
                filter_livestatus=False,
                filter_row=query_filters.column_age_in_range,
                request_var_suffix="_days",
                bound_rescaling=3600 * 24,
            ),
            unit="days",
            is_show_more=False,
        )


class FilterInvtableIntegerRange(FilterNumberRange):
    """Filter for choosing a range in which a certain integer lies"""

    def __init__(self, *, inv_info: str, ident: str, title: str) -> None:
        super().__init__(
            title=title,
            sort_index=800,
            info=inv_info,
            query_filter=query_filters.NumberRangeQuery(
                ident=ident,
                filter_livestatus=False,
                filter_row=query_filters.column_value_in_range,
            ),
        )


class FilterInvFloat(FilterNumberRange):
    def __init__(
        self,
        *,
        ident: str,
        title: str,
        inventory_path: InventoryPath,
        unit: str | LazyString,
        scale: float | None,
        is_show_more: bool = True,
    ) -> None:
        super().__init__(
            title=title,
            sort_index=800,
            info="host",
            query_filter=query_filters.NumberRangeQuery(
                ident=ident,
                filter_livestatus=False,
                filter_row=_filter_in_host_inventory_range(inventory_path),
                request_var_suffix="",
                bound_rescaling=scale if scale is not None else 1.0,
            ),
            unit=unit,
            is_show_more=is_show_more,
        )

    def need_inventory(self, value: FilterHTTPVariables) -> bool:
        return any(self.query_filter.extractor(value))


def _filter_in_host_inventory_range(
    inventory_path: InventoryPath,
) -> Callable[[Row, str, query_filters.MaybeBounds], bool]:
    def row_filter(row: Row, column: str, bounds: query_filters.MaybeBounds) -> bool:
        if not isinstance(
            invdata := row["host_inventory"].get_attribute(inventory_path.path, inventory_path.key),
            int | float,
        ):
            return False
        return query_filters.value_in_range(invdata, bounds)

    return row_filter


class FilterInvtableVersion(Filter):
    def __init__(self, *, inv_info: str, ident: str, title: str) -> None:
        request_vars = [ident + "_from", ident + "_until"]
        self.query_filter = query_filters.Query(
            ident=ident,
            request_vars=request_vars,
            rows_filter=partial(query_filters.version_in_range, ident, request_vars),
        )
        super().__init__(
            ident=self.query_filter.ident,
            title=title,
            sort_index=800,
            info=inv_info,
            htmlvars=self.query_filter.request_vars,
            link_columns=[],
        )

    def display(self, value: FilterHTTPVariables) -> None:
        html.write_text_permissive(_("Min.&nbsp;Version:"))
        html.text_input(self.htmlvars[0], default_value=value.get(self.htmlvars[0], ""), size=7)
        html.write_text_permissive(" &nbsp; ")
        html.write_text_permissive(_("Max.&nbsp;Version:"))
        html.text_input(self.htmlvars[1], default_value=value.get(self.htmlvars[1], ""), size=7)

    def filter_table(self, context: VisualContext, rows: Rows) -> Rows:
        return self.query_filter.filter_table(context, rows)


class FilterInvtableOperStatus(CheckboxRowFilter):
    def __init__(self, *, inv_info: str, ident: str, title: str) -> None:
        super().__init__(
            title=title,
            sort_index=800,
            info=inv_info,
            query_filter=query_filters.MultipleOptionsQuery(
                ident=ident,
                options=[
                    (ident + "_" + str(state), title)
                    for state, title in interface_oper_states().items()
                    # needed because of silly types
                    # skip artificial state 8 (degraded) and 9 (admin down)
                    if isinstance(state, int) and state < 8
                ],
                rows_filter=partial(query_filters.if_oper_status_filter_table, ident),
            ),
        )


class FilterInvtableAdminStatus(FilterOption):
    def __init__(self, *, inv_info: str, ident: str, title: str) -> None:
        super().__init__(
            title=title,
            sort_index=800,
            info=inv_info,
            query_filter=query_filters.SingleOptionQuery(
                ident=ident,
                options=[
                    ("1", _("up")),
                    ("2", _("down")),
                    ("-1", _("(ignore)")),
                ],
                filter_code=lambda x: "",
                filter_row=lambda selection, row: str(row.get("invinterface_admin_status", ""))
                == selection,
            ),
        )


class FilterInvtableAvailable(FilterOption):
    def __init__(self, *, inv_info: str, ident: str, title: str) -> None:
        super().__init__(
            title=title,
            sort_index=800,
            info=inv_info,
            query_filter=query_filters.SingleOptionQuery(
                ident=ident,
                options=[
                    ("no", _("used")),
                    ("yes", _("free")),
                    ("", _("(ignore)")),
                ],
                filter_code=lambda x: "",
                filter_row=lambda selection, row: (selection == "yes")
                == row.get("invinterface_available"),
            ),
        )


def port_types(info: str) -> list[tuple[str, str]]:
    return [(str(k), str(v)) for k, v in sorted(interface_port_types().items(), key=lambda t: t[0])]


class FilterInvtableInterfaceType(DualListFilter):
    def __init__(self, *, inv_info: str, ident: str, title: str) -> None:
        super().__init__(
            title=title,
            sort_index=800,
            info=inv_info,
            query_filter=query_filters.MultipleQuery(ident=ident, op="="),
            options=port_types,
        )

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        return ""

    def filter_table(self, context: VisualContext, rows: Rows) -> Rows:
        value = context.get(self.query_filter.ident, {})
        selection = self.query_filter.selection(value)

        if not selection:
            return rows  # No types selected, filter is unused
        return [row for row in rows if str(row[self.query_filter.column]) in selection]


class FilterInvBool(FilterOption):
    def __init__(
        self,
        *,
        ident: str,
        title: str,
        inventory_path: InventoryPath,
        is_show_more: bool = True,
    ) -> None:
        super().__init__(
            title=title,
            sort_index=800,
            info="host",
            query_filter=query_filters.TristateQuery(
                ident=ident,
                filter_code=lambda x: "",  # No Livestatus filtering right now
                filter_row=inside_inventory(inventory_path),
            ),
            is_show_more=is_show_more,
        )

    def need_inventory(self, value: FilterHTTPVariables) -> bool:
        return self.query_filter.selection_value(value) != self.query_filter.ignore


# Filter tables
def inside_inventory(inventory_path: InventoryPath) -> Callable[[bool, Row], bool]:
    def keep_row(on: bool, row: Row) -> bool:
        return row["host_inventory"].get_attribute(inventory_path.path, inventory_path.key) is on

    return keep_row


class FilterHasInv(FilterOption):
    def __init__(self) -> None:
        super().__init__(
            title=_l("Has Inventory Data"),
            sort_index=801,
            info="host",
            query_filter=query_filters.TristateQuery(
                ident="has_inv",
                filter_code=lambda x: "",  # No Livestatus filtering right now
                filter_row=query_filters.has_inventory,
            ),
            is_show_more=True,
        )

    def need_inventory(self, value: FilterHTTPVariables) -> bool:
        return self.query_filter.selection_value(value) != self.query_filter.ignore


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
        html.text_input(
            varname=self._varprefix + "name",
            default_value=value.get(self._varprefix + "name", ""),
        )
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
        html.write_text_permissive(_("Min.&nbsp;Version: "))
        html.text_input(
            self._varprefix + "version_from",
            default_value=value.get(self._varprefix + "version_from", ""),
            size=9,
        )
        html.write_text_permissive(" &nbsp; ")
        html.write_text_permissive(_("Max.&nbsp;Vers.: "))
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
        name: str | re.Pattern = value.get(self._varprefix + "name", "")
        if not name:
            return rows

        from_version = value[self._varprefix + "version_from"]
        to_version = value[self._varprefix + "version_to"]
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
            packages = row["host_inventory"].get_rows(("software", "packages"))
            is_in = self.find_package(packages, name, from_version, to_version)
            if is_in != negate:
                new_rows.append(row)
        return new_rows

    def find_package(self, packages, name, from_version, to_version):
        for package in packages:
            if isinstance(name, str):
                if package["name"] != name:
                    continue
            elif not name.search(package["name"]):
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
            return True
        return False

    def version_is_lower(self, a: str | None, b: str | None) -> bool:
        return a != b and not self.version_is_higher(a, b)

    def version_is_higher(self, a: str | None, b: str | None) -> bool:
        return cmp_version(a, b) == 1
