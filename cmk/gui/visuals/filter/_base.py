#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import re
from collections.abc import Callable, Iterable
from typing import Literal

from cmk.gui import query_filters
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.type_defs import (
    ColumnName,
    FilterHeader,
    FilterHTTPVariables,
    Row,
    Rows,
    VisualContext,
)
from cmk.gui.utils.regex import validate_regex
from cmk.gui.utils.speaklater import LazyString
from cmk.gui.valuespec import DualListChoice


class Filter(abc.ABC):
    """Base class for all filters"""

    def __init__(
        self,
        *,
        ident: str,
        title: str | LazyString,
        sort_index: int,
        info: str,
        htmlvars: list[str],
        link_columns: list[ColumnName],
        description: None | str | LazyString = None,
        is_show_more: bool = False,
    ) -> None:
        """
        info:          The datasource info this filter needs to work. If this
                       is "service", the filter will also be available in tables
                       showing service information. "host" is available in all
                       service and host views. The log datasource provides both
                       "host" and "service". Look into datasource.py for which
                       datasource provides which information
        htmlvars:      HTML variables this filter uses
        link_columns:  If this filter is used for linking (state "hidden"), then
                       these Livestatus columns are needed to fill the filter with
                       the proper information. In most cases, this is just []. Only
                       a few filters are useful for linking (such as the host_name and
                       service_description filters with exact match)
        """
        self.ident = ident
        self._title = title
        self.sort_index = sort_index
        self.info = info
        self.htmlvars = htmlvars
        self.link_columns = link_columns
        self._description = description
        self.is_show_more = is_show_more

    @property
    def title(self) -> str:
        return str(self._title)

    @property
    def description(self) -> str | None:
        return None if self._description is None else str(self._description)

    def available(self) -> bool:
        """Some filters can be unavailable due to the configuration
        (e.g. the Setup Folder filter is only available if Setup is enabled."""
        return True

    def visible(self) -> bool:
        """Some filters can be invisible. This is useful to hide filters which have always
        the same value but can not be removed using available() because the value needs
        to be set during runtime.
        A good example is the "site" filter which does not need to be available to the
        user in single site setups."""
        return True

    @abc.abstractmethod
    def display(self, value: FilterHTTPVariables) -> None:
        raise NotImplementedError()

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        return ""

    def need_inventory(self, value: FilterHTTPVariables) -> bool:
        """Whether this filter needs to load host inventory data"""
        return False

    def validate_value(self, value: FilterHTTPVariables) -> None:
        return

    def columns_for_filter_table(self, context: VisualContext) -> Iterable[str]:
        """Columns needed to perform post-Livestatus filtering"""
        return []

    def filter_table(self, context: VisualContext, rows: Rows) -> Rows:
        """post-Livestatus filtering (e.g. for BI aggregations)"""
        return rows

    def request_vars_from_row(self, row: Row) -> FilterHTTPVariables:
        """return filter request variables built from the given row"""
        return {}

    def infoprefix(self, infoname: str) -> str:
        if self.info == infoname:
            return ""
        return self.info[:-1] + "_"

    def heading_info(self, value: FilterHTTPVariables) -> str | None:
        """Hidden filters may contribute to the pages headers of the views"""
        return None

    def value(self) -> FilterHTTPVariables:
        """Returns the current representation of the filter settings from the HTML
        var context. This can be used to persist the filter settings."""
        return {varname: request.get_str_input_mandatory(varname, "") for varname in self.htmlvars}


class FilterOption(Filter):
    def __init__(
        self,
        *,
        title: str | LazyString,
        sort_index: int,
        info: str,
        query_filter: query_filters.SingleOptionQuery,
        is_show_more: bool = False,
    ):
        self.query_filter = query_filter
        super().__init__(
            ident=self.query_filter.ident,
            title=title,
            sort_index=sort_index,
            info=info,
            htmlvars=self.query_filter.request_vars,
            link_columns=[],
            is_show_more=is_show_more,
        )

    def display(self, value: FilterHTTPVariables) -> None:
        display_filter_radiobuttons(
            varname=self.query_filter.request_vars[0],
            options=self.query_filter.options,
            default=str(self.query_filter.ignore),
            value=value,
        )

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        return self.query_filter.filter(value)

    def filter_table(self, context: VisualContext, rows: Rows) -> Rows:
        """post-Livestatus filtering (e.g. for BI aggregations)"""
        return self.query_filter.filter_table(context, rows)


def display_filter_radiobuttons(
    *, varname: str, options: list[tuple[str, str]], default: str, value: FilterHTTPVariables
) -> None:
    pick = value.get(varname, default)
    html.begin_radio_group(horizontal=True)
    for state, text in options:
        html.radiobutton(varname, state, pick == state, text + " &nbsp; ")
    html.end_radio_group()


def recover_pre_2_1_range_filter_request_vars(
    query: query_filters.NumberRangeQuery,
) -> dict[str, str]:
    """Some range filters used the _to suffix instead of the standard _until.

    Do inverse translation to search for this request vars."""
    request_var_match = ((var, re.sub("_until(_|$)", "_to\\1", var)) for var in query.request_vars)
    return {
        current_var: (
            request.get_str_input_mandatory(current_var, "")
            or request.get_str_input_mandatory(old_var, "")
        )
        for current_var, old_var in request_var_match
    }


class FilterNumberRange(Filter):  # type is int
    def __init__(
        self,
        *,
        title: str | LazyString,
        sort_index: int,
        info: str,
        query_filter: query_filters.NumberRangeQuery,
        unit: str | LazyString = "",
        is_show_more: bool = True,
    ) -> None:
        self.query_filter = query_filter
        self.unit = unit
        super().__init__(
            ident=self.query_filter.ident,
            title=title,
            sort_index=sort_index,
            info=info,
            htmlvars=self.query_filter.request_vars,
            link_columns=[],
            is_show_more=is_show_more,
        )

    def display(self, value: FilterHTTPVariables) -> None:
        html.write_text_permissive(_("From:") + "&nbsp;")
        html.text_input(
            self.htmlvars[0], default_value=value.get(self.htmlvars[0], ""), style="width: 80px;"
        )
        if self.unit:
            html.write_text_permissive(" %s " % self.unit)

        html.write_text_permissive(" &nbsp; " + _("To:") + "&nbsp;")
        html.text_input(
            self.htmlvars[1], default_value=value.get(self.htmlvars[1], ""), style="width: 80px;"
        )
        if self.unit:
            html.write_text_permissive(" %s " % self.unit)

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        return self.query_filter.filter(value)

    def filter_table(self, context: VisualContext, rows: Rows) -> Rows:
        return self.query_filter.filter_table(context, rows)

    def value(self) -> FilterHTTPVariables:
        """Returns the current representation of the filter settings from the request context."""
        return recover_pre_2_1_range_filter_request_vars(self.query_filter)


class FilterTime(Filter):
    """Filter for setting time ranges, e.g. on last_state_change and last_check"""

    def __init__(
        self,
        *,
        title: str | LazyString,
        sort_index: int,
        info: Literal["comment", "downtime", "event", "history", "host", "log", "service"],
        query_filter: query_filters.TimeQuery,
        is_show_more: bool = False,
    ):
        self.query_filter = query_filter

        super().__init__(
            ident=self.query_filter.ident,
            title=title,
            sort_index=sort_index,
            info=info,
            htmlvars=self.query_filter.request_vars,
            link_columns=[self.query_filter.column],
            is_show_more=is_show_more,
        )

    def display(self, value: FilterHTTPVariables) -> None:
        html.open_table(class_="filtertime")
        for what, whatname in [("from", _("From")), ("until", _("Until"))]:
            varprefix = self.ident + "_" + what
            html.open_tr()
            html.td("%s:" % whatname)
            html.open_td()
            html.text_input(varprefix, default_value=value.get(varprefix, ""))
            html.close_td()
            html.open_td()
            html.dropdown(
                varprefix + "_range",
                query_filters.time_filter_options(),
                deflt=value.get(varprefix + "_range", "3600"),
            )
            html.close_td()
            html.close_tr()
        html.close_table()

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        return self.query_filter.filter(value)

    def filter_table(self, context: VisualContext, rows: Rows) -> Rows:
        return self.query_filter.filter_table(context, rows)

    def value(self) -> FilterHTTPVariables:
        """Returns the current representation of the filter settings from the request context."""
        return recover_pre_2_1_range_filter_request_vars(self.query_filter)


def checkbox_component(htmlvar: str, value: FilterHTTPVariables, label: str) -> None:
    html.open_nobr()
    html.checkbox(htmlvar, bool(value.get(htmlvar)), label=label)
    html.close_nobr()


class InputTextFilter(Filter):
    def __init__(
        self,
        *,
        title: str | LazyString,
        sort_index: int,
        info: str,
        query_filter: query_filters.TextQuery,
        show_heading: bool = True,
        description: None | str | LazyString = None,
        is_show_more: bool = False,
    ):
        self.query_filter = query_filter

        super().__init__(
            ident=self.query_filter.ident,
            title=title,
            sort_index=sort_index,
            info=info,
            htmlvars=self.query_filter.request_vars,
            link_columns=self.query_filter.link_columns,
            description=description,
            is_show_more=is_show_more,
        )
        self._show_heading = show_heading

    def display(self, value: FilterHTTPVariables) -> None:
        current_value = value.get(self.query_filter.request_vars[0], "")
        html.text_input(
            self.htmlvars[0], current_value, self.query_filter.negateable and "neg" or ""
        )

        if self.query_filter.negateable:
            checkbox_component(self.query_filter.request_vars[1], value, _("negate"))

    def request_vars_from_row(self, row: Row) -> dict[str, str]:
        return {self.htmlvars[0]: row[self.query_filter.column]}

    def heading_info(self, value: FilterHTTPVariables) -> str | None:
        if self._show_heading:
            return value.get(self.query_filter.request_vars[0])
        return None

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        return self.query_filter.filter(value)

    def filter_table(self, context: VisualContext, rows: Rows) -> Rows:
        return self.query_filter.filter_table(context, rows)


def checkbox_row(
    options: list[tuple[str, str]], value: FilterHTTPVariables, title: str | None = None
) -> None:
    html.begin_checkbox_group()
    if title:
        html.write_text_permissive(title)
    checkbox_default = not any(value.values())
    for var, text in options:
        html.checkbox(var, bool(value.get(var, checkbox_default)), label=text)
    html.end_checkbox_group()


class CheckboxRowFilter(Filter):
    def __init__(
        self,
        *,
        title: str | LazyString,
        sort_index: int,
        info: str,
        query_filter: query_filters.MultipleOptionsQuery,
        is_show_more: bool = False,
    ) -> None:
        super().__init__(
            ident=query_filter.ident,
            title=title,
            sort_index=sort_index,
            info=info,
            htmlvars=query_filter.request_vars,
            link_columns=[],
            is_show_more=is_show_more,
        )
        self.query_filter = query_filter

    def display(self, value: FilterHTTPVariables) -> None:
        checkbox_row(self.query_filter.options, value)

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        return self.query_filter.filter(value)

    def filter_table(self, context: VisualContext, rows: Rows) -> Rows:
        return self.query_filter.filter_table(context, rows)


class DualListFilter(Filter):
    def __init__(
        self,
        *,
        title: str | LazyString,
        sort_index: int,
        info: str,
        query_filter: query_filters.MultipleQuery,
        options: Callable[[str], query_filters.SitesOptions],
        description: None | str | LazyString = None,
        is_show_more: bool = True,
    ):
        self.query_filter = query_filter
        self._options = options
        super().__init__(
            ident=self.query_filter.ident,
            title=title,
            sort_index=sort_index,
            info=info,
            htmlvars=self.query_filter.request_vars,
            link_columns=[],
            description=description,
            is_show_more=is_show_more,
        )

    def display(self, value: FilterHTTPVariables) -> None:
        html.open_div(class_="multigroup")
        DualListChoice(choices=self._options(self.info), rows=4, enlarge_active=True).render_input(
            self.query_filter.request_vars[0], self.query_filter.selection(value)
        )

        if self.query_filter.negateable:
            checkbox_component(self.query_filter.request_vars[1], value, _("negate"))
        html.close_div()

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        return self.query_filter.filter(value)


class RegexFilter(InputTextFilter):
    def validate_value(self, value: FilterHTTPVariables) -> None:
        htmlvar = self.htmlvars[0]
        validate_regex(value.get(htmlvar, ""), htmlvar)
