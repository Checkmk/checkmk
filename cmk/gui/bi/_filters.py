#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from typing import Any

from cmk.gui import query_filters
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _, _l
from cmk.gui.type_defs import Choices, FilterHeader, FilterHTTPVariables, Row, Rows, VisualContext
from cmk.gui.utils.speaklater import LazyString
from cmk.gui.utils.user_errors import user_errors
from cmk.gui.visuals.filter import Filter, FilterOption, FilterRegistry

from ._compiler import is_part_of_aggregation
from ._packs import aggregation_group_choices, get_aggregation_group_trees


def register(filter_registry: FilterRegistry) -> None:
    filter_registry.register(_FilterAggrGroup())
    filter_registry.register(_FilterAggrGroupTree())
    filter_registry.register(_BIFrozenAggregations())

    filter_registry.register(
        BITextFilter(
            ident="aggr_name_regex",
            title=_l("Aggregation name regex"),
            sort_index=120,
            what="name",
            suffix="_regex",
        )
    )

    filter_registry.register(
        BITextFilter(
            ident="aggr_name",
            title=_l("Aggregation name (exact match)"),
            sort_index=120,
            what="name",
            how="exact",
        )
    )

    filter_registry.register(
        BITextFilter(
            ident="aggr_output",
            title=_l("Aggregation output"),
            sort_index=121,
            what="output",
        )
    )

    filter_registry.register(_FilterAggrHosts())
    filter_registry.register(_FilterAggrService())
    filter_registry.register(
        BIStatusFilter(
            ident="aggr_state",
            title=_l(" State"),
            sort_index=150,
            what="",
        )
    )

    filter_registry.register(
        BIStatusFilter(
            ident="aggr_effective_state",
            title=_l("Effective  State"),
            sort_index=151,
            what="effective_",
        )
    )

    filter_registry.register(
        BIStatusFilter(
            ident="aggr_assumed_state",
            title=_l("Assumed  State"),
            sort_index=152,
            what="assumed_",
        )
    )

    filter_registry.register(
        FilterOption(
            title=_l("Used in BI aggregate"),
            sort_index=300,
            info="service",
            query_filter=query_filters.TristateQuery(
                ident="aggr_service_used",
                filter_code=lambda x: "",
                filter_row=bi_aggr_service_used,
            ),
            is_show_more=True,
        )
    )


def bi_aggr_service_used(on: bool, row: Row) -> bool:
    # should be in query_filters, but it creates a cyclical import at the moment
    return is_part_of_aggregation(row["host_name"], row["service_description"]) is on


class _FilterAggrGroup(Filter):
    def __init__(self) -> None:
        self.column = "aggr_group"
        super().__init__(
            ident="aggr_group",
            title=_l("Aggregation group"),
            sort_index=90,
            info=self.column,
            htmlvars=[self.column],
            link_columns=[self.column],
        )

    def request_vars_from_row(self, row: Row) -> dict[str, str]:
        return {self.htmlvars[0]: row[self.column]}

    def display(self, value: FilterHTTPVariables) -> None:
        htmlvar = self.htmlvars[0]
        html.dropdown(htmlvar, self._options(), deflt=value.get(htmlvar, ""))

    @staticmethod
    def _options() -> Choices:
        empty_choices: Choices = [("", "")]
        return empty_choices + list(aggregation_group_choices())

    def filter_table(self, context: VisualContext, rows: Rows) -> Rows:
        value = context.get(self.ident, {})
        if group := value.get(self.htmlvars[0], ""):
            return [row for row in rows if row[self.column] == group]
        return rows

    def heading_info(self, value: FilterHTTPVariables) -> str | None:
        return value.get(self.htmlvars[0])


class _FilterAggrGroupTree(Filter):
    def __init__(self) -> None:
        self.column = "aggr_group_tree"
        super().__init__(
            ident="aggr_group_tree",
            title=_l("Aggregation group tree"),
            sort_index=91,
            info="aggr_group",
            htmlvars=[self.column],
            link_columns=[self.column],
        )

    def request_vars_from_row(self, row: Row) -> dict[str, str]:
        return {self.htmlvars[0]: row[self.column]}

    def display(self, value: FilterHTTPVariables) -> None:
        htmlvar = self.htmlvars[0]
        html.dropdown(htmlvar, self._options(), deflt=value.get(htmlvar, ""))

    def heading_info(self, value: FilterHTTPVariables) -> str | None:
        return value.get(self.htmlvars[0])

    @staticmethod
    def _options() -> Choices:
        def _build_tree(group, parent, path):
            this_node = group[0]
            path = path + (this_node,)
            child = parent.setdefault(this_node, {"__path__": path})
            children = group[1:]
            if children:
                child = child.setdefault("__children__", {})
                _build_tree(children, child, path)

        def _build_selection(selection, tree, index):
            index += 1
            for _unused, sub_tree in tree.items():
                selection.append(_get_selection_entry(sub_tree, index, True))
                _build_selection(selection, sub_tree.get("__children__", {}), index)

        def _get_selection_entry(tree, index, prefix=None):
            path = tree["__path__"]
            if prefix:
                title_prefix = ("\u00a0" * 6 * index) + "\u2514\u2500 "
            else:
                title_prefix = ""
            return ("/".join(path), title_prefix + path[index])

        tree: dict[str, Any] = {}
        for group in get_aggregation_group_trees():
            _build_tree(group.split("/"), tree, tuple())

        selection: Choices = []
        index = 0
        for _unused, sub_tree in tree.items():
            selection.append(_get_selection_entry(sub_tree, index))
            _build_selection(selection, sub_tree.get("__children__", {}), index)

        empty: Choices = [("", "")]

        return empty + selection


class _BIFrozenAggregations(Filter):
    def __init__(self):
        super().__init__(
            ident="aggregation_types",
            title=_("Aggregation types"),
            sort_index=90,
            info="aggr",
            htmlvars=["aggr_type_frozen", "aggr_type_dynamic"],
            link_columns=[],
        )

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        return ""

    def display(self, value: FilterHTTPVariables) -> None:
        html.checkbox(
            self.htmlvars[0], deflt=bool(value.get(self.htmlvars[0], True)), label=_("Show frozen")
        )
        html.checkbox(
            self.htmlvars[1], deflt=bool(value.get(self.htmlvars[1], True)), label=_("Show dynamic")
        )

    def filter_table(self, context: VisualContext, rows: Rows) -> Rows:
        if self.ident not in context:
            return rows
        show_frozen = bool(context.get(self.ident, {}).get(self.htmlvars[0]))
        show_dynamic = bool(context.get(self.ident, {}).get(self.htmlvars[1]))
        if show_frozen and show_dynamic:
            return rows
        if not show_frozen and not show_dynamic:
            return []

        new_rows = []
        for row in rows:
            if (compiled_aggregation := row.get("aggr_compiled_aggregation")) is None:
                continue

            if compiled_aggregation.frozen_info:
                if show_frozen:
                    new_rows.append(row)
            elif show_dynamic:
                new_rows.append(row)

        return new_rows


# how is either "regex" or "exact"
class BITextFilter(Filter):
    def __init__(
        self,
        *,
        ident: str,
        title: str | LazyString,
        sort_index: int,
        what: str,
        how: str = "regex",
        suffix: str = "",
    ) -> None:
        self.how = how
        self.column = "aggr_" + what
        super().__init__(
            ident=ident,
            title=title,
            sort_index=sort_index,
            info="aggr",
            htmlvars=[self.column + suffix],
            link_columns=[self.column],
        )

    def request_vars_from_row(self, row: Row) -> dict[str, str]:
        return {self.htmlvars[0]: row[self.column]}

    def display(self, value: FilterHTTPVariables) -> None:
        html.text_input(self.htmlvars[0], default_value=value.get(self.htmlvars[0], ""))

    def heading_info(self, value: FilterHTTPVariables) -> str | None:
        return value.get(self.htmlvars[0])

    def filter_table(self, context: VisualContext, rows: Rows) -> Rows:
        values = context.get(self.ident, {})
        val = values.get(self.htmlvars[0])

        if not val:
            return rows
        if self.how == "regex":
            try:
                reg = re.compile(val.lower())
            except re.error as e:
                user_errors.add(
                    MKUserError(self.htmlvars[0], _("Invalid regular expression: %s") % e)
                )
                return rows

            return [row for row in rows if reg.search(row[self.column].lower())]
        return [row for row in rows if row[self.column] == val]


class _FilterAggrHosts(Filter):
    def __init__(self) -> None:
        super().__init__(
            ident="aggr_hosts",
            title=_l("Affected hosts contain"),
            sort_index=130,
            info="aggr",
            htmlvars=["aggr_host_site", "aggr_host_host"],
            link_columns=[],
            description=_l(
                "Filter for all aggregations that base on status information of that host. "
                "Exact match (no regular expression)"
            ),
        )

    def display(self, value: FilterHTTPVariables) -> None:
        html.text_input(self.htmlvars[1], default_value=value.get(self.htmlvars[1], ""))

    def heading_info(self, value: FilterHTTPVariables) -> str | None:
        return value.get(self.htmlvars[1])

    def find_host(self, host, hostlist):
        return any((h == host for _s, h in hostlist))

    def request_vars_from_row(self, row: Row) -> dict[str, str]:
        return {
            "aggr_host_host": row["host_name"],
            "aggr_host_site": row["site"],
        }

    def filter_table(self, context: VisualContext, rows: Rows) -> Rows:
        values = context.get(self.ident, {})
        if val := values.get(self.htmlvars[1]):
            return [row for row in rows if self.find_host(val, row["aggr_hosts"])]
        return rows


class _FilterAggrService(Filter):
    """Not performing filter(), nor filter_table(). The filtering is done directly in BI by
    bi.table(), which calls service_spec()."""

    def __init__(self) -> None:
        super().__init__(
            ident="aggr_service",
            title=_l("Affected by service"),
            sort_index=131,
            info="aggr",
            htmlvars=["aggr_service_site", "aggr_service_host", "aggr_service_service"],
            link_columns=[],
            description=_l(
                "Filter for all aggregations that are affected by one specific service on a specific host (no regular expression)"
            ),
        )

    def display(self, value: FilterHTTPVariables) -> None:
        html.write_text_permissive(_("Host") + ": ")
        html.text_input(self.htmlvars[1], default_value=value.get(self.htmlvars[1], ""))
        html.write_text_permissive(_("Service") + ": ")
        html.text_input(self.htmlvars[2], default_value=value.get(self.htmlvars[2], ""))

    def heading_info(self, value: FilterHTTPVariables) -> str | None:
        return value.get(self.htmlvars[1], "") + " / " + value.get(self.htmlvars[2], "")

    def request_vars_from_row(self, row: Row) -> dict[str, str]:
        return {
            "site": row["site"],
            "host": row["host_name"],
            "service": row["service_description"],
        }


class BIStatusFilter(Filter):
    # TODO: Rename "what"
    def __init__(self, ident: str, title: str | LazyString, sort_index: int, what: str) -> None:
        self.column = "aggr_" + what + "state"
        if what == "":
            self.code = "r"
        else:
            self.code = what[0]
        self.prefix = "bi%ss" % self.code
        vars_ = [f"{self.prefix}{x}" for x in [-1, 0, 1, 2, 3, "_filled"]]
        if self.code == "a":
            vars_.append(self.prefix + "n")
        super().__init__(
            ident=ident,
            title=title,
            sort_index=sort_index,
            info="aggr",
            htmlvars=vars_,
            link_columns=[],
        )

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        return ""

    def _filter_used(self, value: FilterHTTPVariables) -> FilterHeader:
        return value.get(self.prefix + "_filled", "")

    def display(self, value: FilterHTTPVariables) -> None:
        html.hidden_field(self.prefix + "_filled", "1", add_var=True)
        checkbox_default = not self._filter_used(value)  # everything by default

        for varend, text in self._options():
            if self.code != "a" and varend == "n":
                continue  # no unset for read and effective state
            if varend == "n":
                html.br()
            var = self.prefix + varend
            html.checkbox(var, deflt=bool(value.get(var, checkbox_default)), label=text)

    @staticmethod
    def _options() -> list[tuple[str, str]]:
        return [
            ("0", _("OK")),
            ("1", _("WARN")),
            ("2", _("CRIT")),
            ("3", _("UNKN")),
            ("-1", _("PEND")),
            ("n", _("no assumed state set")),
        ]

    def filter_table(self, context: VisualContext, rows: Rows) -> Rows:
        value = context.get(self.ident, {})
        if not self._filter_used(value):
            return rows

        allowed_states = []
        for i in ["0", "1", "2", "3", "-1", "n"]:
            if value.get(self.prefix + i):
                if i == "n":
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
