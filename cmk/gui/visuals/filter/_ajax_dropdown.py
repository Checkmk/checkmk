#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Callable
from typing import Literal

import livestatus

from cmk.gui import query_filters, sites
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
from cmk.gui.utils.autocompleter_config import AutocompleterConfig
from cmk.gui.utils.speaklater import LazyString

from ._base import checkbox_component, Filter


class AjaxDropdownFilter(Filter):
    "Select from dropdown with dynamic option query"

    def __init__(
        self,
        *,
        title: str | LazyString,
        sort_index: int,
        info: str,
        autocompleter: AutocompleterConfig,
        query_filter: query_filters.TextQuery | query_filters.KubernetesQuery,
        link_columns: list[ColumnName] | None = None,
        description: None | str | LazyString = None,
        is_show_more: bool = False,
        validate_value: Callable[[str, str], None] | None = None,
    ) -> None:
        self.query_filter = query_filter
        self.autocompleter = autocompleter
        self._validate_value = validate_value

        super().__init__(
            ident=self.query_filter.ident,
            title=title,
            sort_index=sort_index,
            info=info,
            htmlvars=self.query_filter.request_vars,
            link_columns=link_columns or self.query_filter.link_columns,
            description=description,
            is_show_more=is_show_more,
        )

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        return self.query_filter.filter(value)

    def filter_table(self, context: VisualContext, rows: Rows) -> Rows:
        return self.query_filter.filter_table(context, rows)

    def request_vars_from_row(self, row: Row) -> dict[str, str]:
        return {self.query_filter.request_vars[0]: row[self.query_filter.column]}

    def display(self, value: FilterHTTPVariables) -> None:
        current_value = value.get(self.query_filter.request_vars[0], "")
        choices = [(current_value, current_value)] if current_value else []
        varname = self.query_filter.request_vars[0]

        html.dropdown(
            varname,
            choices,
            current_value,
            style="width: 250px;",
            class_=["ajax-vals"],
            data_autocompleter=json.dumps(self.autocompleter.config),
        )

        if self.query_filter.negateable:
            checkbox_component(self.query_filter.request_vars[1], value, _("negate"))

        if self._validate_value:
            html.javascript(
                f"cmk.valuespecs.init_on_change_validation('{varname}', '{self.ident}');"
            )

    def validate_value(self, value: FilterHTTPVariables) -> None:
        if self._validate_value:
            htmlvar = self.htmlvars[0]
            self._validate_value(value.get(htmlvar, ""), htmlvar)


GroupType = Literal[
    "host", "service", "contact", "host_contact", "service_contact", "event_effective_contact"
]


class FilterGroupCombo(AjaxDropdownFilter):
    """Selection of a host/service(-contact) group as an attribute of a host or service"""

    def __init__(
        self,
        *,
        title: str | LazyString,
        sort_index: int,
        group_type: GroupType,
        autocompleter: AutocompleterConfig,
        query_filter: query_filters.TextQuery,
        description: None | str | LazyString = None,
    ) -> None:
        self.query_filter = query_filter
        self.group_type = group_type

        super().__init__(
            title=title,
            sort_index=sort_index,
            info=group_type.split("_")[0],
            autocompleter=autocompleter,
            query_filter=query_filter,
            link_columns=[group_type + "group_name"],
            description=description,
        )

    def request_vars_from_row(self, row: Row) -> dict[str, str]:
        varname = self.htmlvars[0]
        value = row.get(self.group_type + "group_name")
        if value:
            s = {varname: value}
            if self.query_filter.negateable:
                negvar = self.query_filter.request_vars[1]
                if request.var(negvar):  # This violates the idea of originating from row
                    s[negvar] = request.var(negvar)
            return s
        return {}

    def heading_info(self, value: FilterHTTPVariables) -> str | None:
        # TODO: This should be part of the general options query
        if current_value := value.get(self.query_filter.request_vars[0]):
            group_type = "contact" if self.group_type.endswith("_contact") else self.group_type
            alias = sites.live().query_value(
                f"GET {group_type}groups\nCache: reload\nColumns: alias\nFilter: name = {livestatus.lqencode(current_value)}\n",
                current_value,
            )
            return alias
        return None
