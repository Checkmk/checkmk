#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from functools import partial
from typing import override

from cmk.gui import query_filters
from cmk.gui.config import RequestCacheConfig
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _, _l
from cmk.gui.ifaceoper import interface_port_types
from cmk.gui.num_split import cmp_version
from cmk.gui.type_defs import (
    FilterHTTPVariables,
    Row,
    Rows,
    VisualContext,
)
from cmk.gui.visuals.filter import (
    CheckboxRowFilter,
    Filter,
    FilterGroup,
    FilterOption,
    InputTextFilter,
)
from cmk.gui.visuals.filter.components import (
    Checkbox,
    Dropdown,
    DualList,
    FilterComponent,
    HorizontalGroup,
    RadioButton,
    StaticText,
    TextInput,
)
from cmk.inventory.raw_paths import InventoryPath
from cmk.inventory.trees import SDValue
from cmk.inventory_ui.v1 import Comparable
from cmk.web.utils.request_cache import RequestCache
from cmk.web.utils.speaklater import LazyString


# Legacy display hints name the following filter classes and the hint
# parser replaces each by a generic table filter. Keep the names until the
# legacy display hint API is removed in 3.1.0.
class FilterInvtableTimestampAsAge: ...


class FilterInvtableOperStatus: ...


class FilterInvtableAdminStatus: ...


class FilterInvtableAvailable: ...


class FilterInvtableInterfaceType: ...


# Legacy display hint plug-ins may import this function. Keep it until the
# legacy display hint API is removed in 3.1.0.
def port_types(_info: str) -> list[tuple[str, str]]:
    return [(str(k), str(v)) for k, v in sorted(interface_port_types().items(), key=lambda t: t[0])]


def _make_filter_row_bool(inventory_path: InventoryPath) -> Callable[[bool, Row], bool]:
    def keep_row(on: bool, row: Row) -> bool:
        return row["host_inventory"].get_attribute(inventory_path.path, inventory_path.key) is on

    return keep_row


class _FilterInvOption(FilterOption):
    @override
    def need_inventory(self, value: FilterHTTPVariables) -> bool:
        return self.query_filter.selection_value(value) != self.query_filter.ignore


class FilterInvBool(_FilterInvOption):
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
                filter_code=lambda _x: "",  # No Livestatus filtering right now
                filter_row=_make_filter_row_bool(inventory_path),
            ),
            is_show_more=is_show_more,
            group=FilterGroup.INVENTORY,
        )


@dataclass(frozen=True)
class FilterInvFloatChoice:
    unit: str
    factor: int


_MaybeBounds = tuple[int | float | None, int | float | None]


def _request_vars(ident: str) -> Sequence[str]:
    return [f"{ident}_from", f"{ident}_until"]


def _bound_labels() -> tuple[str, str]:
    return _("From:"), _("To:")


class _FilterNumberRange(Filter):
    def __init__(
        self,
        *,
        inv_info: str,
        ident: str,
        title: str,
        unit_choices: Mapping[str, FilterInvFloatChoice],
        filter_row: Callable[[Row, str, _MaybeBounds], bool],
    ) -> None:
        self._unit_choices = unit_choices
        self._filter_row = filter_row

        self._bound_vars = [(var, f"{var}_prefix") for var in _request_vars(ident)]
        super().__init__(
            ident=ident,
            title=title,
            sort_index=800,
            info=inv_info,
            htmlvars=[var for bound_vars in self._bound_vars for var in bound_vars],
            link_columns=[],
            group=FilterGroup.INVENTORY,
        )

    @override
    def display(
        self, value: FilterHTTPVariables, _request_cache: RequestCache[RequestCacheConfig]
    ) -> None:
        # keep this in sync with components(), remove once all filter menus are switched to vue
        # this special styling is not supported by the current components
        unit_choices = [(n, c.unit) for n, c in self._unit_choices.items()]

        html.open_table()
        for (var, prefix_var), label in zip(self._bound_vars, _bound_labels()):
            html.open_tr()
            html.open_td()
            html.write_text_permissive(label + "&nbsp;")
            html.close_td()

            html.open_td()
            html.text_input(
                varname=var,
                default_value=value.get(var, ""),
                style="width: 80px;",
            )
            html.close_td()

            if unit_choices:
                html.open_td()
                html.dropdown(prefix_var, unit_choices, deflt=value.get(prefix_var, ""))
                html.close_td()
            html.close_tr()
        html.close_table()

    @override
    def components(
        self, _request_cache: RequestCache[RequestCacheConfig]
    ) -> Iterable[FilterComponent]:
        unit_choices = {n: c.unit for n, c in self._unit_choices.items()}
        for (var, prefix_var), label in zip(self._bound_vars, _bound_labels()):
            text_input = TextInput(id=var, label=label)
            yield HorizontalGroup(
                components=(
                    [text_input, Dropdown(id=prefix_var, choices=unit_choices)]
                    if unit_choices
                    else [text_input]
                )
            )

    def _get_bound(self, var: str, var_prefix: str | None) -> int | float | None:
        if var_prefix is not None and (choice := self._unit_choices.get(var_prefix)):
            factor = choice.factor
        else:
            factor = 1
        try:
            return float(var) * factor
        except ValueError:
            return None

    def _get_bounds(self, filter_vars: FilterHTTPVariables) -> _MaybeBounds:
        from_bound, until_bound = (
            None
            if (value := filter_vars.get(var)) is None
            else self._get_bound(value, filter_vars.get(prefix_var))
            for var, prefix_var in self._bound_vars
        )
        return from_bound, until_bound

    @override
    def filter_table(self, context: VisualContext, rows: Rows) -> Rows:
        from_var, until_var = self._get_bounds(context.get(self.ident, {}))
        return (
            rows
            if from_var is None and until_var is None
            else [row for row in rows if self._filter_row(row, self.ident, (from_var, until_var))]
        )

    @override
    def need_inventory(self, value: FilterHTTPVariables) -> bool:
        return any(b is not None for b in self._get_bounds(value))


def _make_filter_row_float(
    inventory_path: InventoryPath,
) -> Callable[[Row, str, _MaybeBounds], bool]:
    def row_filter(row: Row, _column: str, bounds: _MaybeBounds) -> bool:
        if not isinstance(
            invdata := row["host_inventory"].get_attribute(inventory_path.path, inventory_path.key),
            int | float,
        ):
            return False
        return query_filters.value_in_range(invdata, bounds)

    return row_filter


class FilterInvFloat(_FilterNumberRange):
    def __init__(
        self,
        *,
        ident: str,
        title: str,
        inventory_path: InventoryPath,
        unit_choices: Mapping[str, FilterInvFloatChoice],
    ) -> None:
        super().__init__(
            inv_info="host",
            ident=ident,
            title=title,
            unit_choices=unit_choices,
            filter_row=_make_filter_row_float(inventory_path),
        )


def _make_filter_row_text(
    inventory_path: InventoryPath,
) -> Callable[[str, str], Callable[[Row], bool]]:
    def row_filter(filtertext: str, column: str) -> Callable[[Row], bool]:
        regex = query_filters.re_ignorecase(filtertext, column)

        def filt(row: Row) -> bool:
            value = row["host_inventory"].get_attribute(inventory_path.path, inventory_path.key)
            return value is not None and bool(regex.search(str(value)))

        return filt

    return row_filter


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
                ident=ident, row_filter=_make_filter_row_text(inventory_path)
            ),
            show_heading=False,
            is_show_more=is_show_more,
            group=FilterGroup.INVENTORY,
        )

    @override
    def need_inventory(self, value: FilterHTTPVariables) -> bool:
        return bool(value.get(self.htmlvars[0], "").strip())


def _sort_key_in_range(
    *,
    value: SDValue,
    sort_key: Callable[[str], Comparable],
    lower: Comparable | None,
    upper: Comparable | None,
) -> bool:
    if value is None:
        return False

    if not isinstance(value, str):
        raise TypeError(value)

    sortable_value = sort_key(value)

    above_lower = lower is None or not sortable_value < lower
    below_upper = upper is None or not upper < sortable_value
    return above_lower and below_upper


def _filter_rows_with_sort_key(
    ident: str,
    value_of: Callable[[Row], SDValue],
    sort_key: Callable[[str], Comparable],
    context: VisualContext,
    rows: Rows,
) -> Rows:
    from_value, until_value = (
        context.get(ident, {}).get(v, "").strip() for v in _request_vars(ident)
    )
    if not from_value and not until_value:
        return rows

    lower = sort_key(from_value) if from_value else None
    upper = sort_key(until_value) if until_value else None
    return [
        r
        for r in rows
        if _sort_key_in_range(value=value_of(r), sort_key=sort_key, lower=lower, upper=upper)
    ]


class _FilterTextRange(Filter):
    def __init__(
        self,
        *,
        inv_info: str,
        ident: str,
        title: str | LazyString,
        from_label: str,
        until_label: str,
        rows_filter: Callable[[VisualContext, Rows], Rows],
        is_show_more: bool = False,
    ) -> None:
        self._from_label = from_label
        self._until_label = until_label
        self.query_filter = query_filters.Query(
            ident=ident,
            request_vars=list(_request_vars(ident)),
            rows_filter=rows_filter,
        )
        super().__init__(
            ident=self.query_filter.ident,
            title=title,
            sort_index=800,
            info=inv_info,
            htmlvars=self.query_filter.request_vars,
            link_columns=[],
            is_show_more=is_show_more,
            group=FilterGroup.INVENTORY,
        )

    @override
    def display(
        self, value: FilterHTTPVariables, _request_cache: RequestCache[RequestCacheConfig]
    ) -> None:
        # keep this in sync with components(), remove once all filter menus are switched to vue
        # this special styling is not supported by the current components
        html.write_text_permissive(self._from_label)
        html.text_input(
            varname=self.htmlvars[0], default_value=value.get(self.htmlvars[0], ""), size=7
        )
        html.write_text_permissive(" &nbsp; ")
        html.write_text_permissive(self._until_label)
        html.text_input(
            varname=self.htmlvars[1], default_value=value.get(self.htmlvars[1], ""), size=7
        )

    @override
    def components(
        self, _request_cache: RequestCache[RequestCacheConfig]
    ) -> Iterable[FilterComponent]:
        yield HorizontalGroup(
            components=[
                TextInput(id=self.htmlvars[0], label=self._from_label),
                TextInput(id=self.htmlvars[1], label=self._until_label),
            ]
        )

    @override
    def filter_table(self, context: VisualContext, rows: Rows) -> Rows:
        return self.query_filter.filter_table(context, rows)


class FilterInvTextWithSortKey(_FilterTextRange):
    def __init__(
        self,
        *,
        ident: str,
        title: str | LazyString,
        inventory_path: InventoryPath,
        sort_key: Callable[[str], Comparable],
        is_show_more: bool = True,
    ) -> None:
        super().__init__(
            inv_info="host",
            ident=ident,
            title=title,
            from_label=_("From:"),
            until_label=_("To:"),
            rows_filter=partial(
                _filter_rows_with_sort_key,
                ident,
                lambda row: row["host_inventory"].get_attribute(
                    inventory_path.path, inventory_path.key
                ),
                sort_key,
            ),
            is_show_more=is_show_more,
        )

    @override
    def need_inventory(self, value: FilterHTTPVariables) -> bool:
        return any(value.get(var, "").strip() for var in self.htmlvars)


def _make_filter_row_choice(inventory_path: InventoryPath) -> Callable[[str, Row], bool]:
    def keep_row(selection: str, row: Row) -> bool:
        value = row["host_inventory"].get_attribute(inventory_path.path, inventory_path.key)
        return value is not None and str(value) == selection

    return keep_row


class FilterInvChoice(_FilterInvOption):
    def __init__(
        self,
        *,
        ident: str,
        title: str,
        inventory_path: InventoryPath,
        options: Sequence[tuple[str, str]],
        is_show_more: bool = True,
    ) -> None:
        super().__init__(
            title=title,
            sort_index=800,
            info="host",
            query_filter=query_filters.SingleOptionQuery(
                ident=ident,
                options=[*options, ("", _("(ignore)"))],
                filter_code=lambda _x: "",
                filter_row=_make_filter_row_choice(inventory_path),
            ),
            is_show_more=is_show_more,
            group=FilterGroup.INVENTORY,
        )


def _filter_rows_table_choice(ident: str, context: VisualContext, rows: Rows) -> Rows:
    filter_vars = context.get(ident, {})

    def _add_row(row: Row) -> bool:
        if (value := row.get(ident)) is not None and (
            filter_key := f"{ident}_{value}"
        ) in filter_vars:
            return filter_vars[filter_key] == "on"
        return True

    return [row for row in rows if _add_row(row)]


class FilterInvtableChoice(CheckboxRowFilter):
    def __init__(
        self,
        *,
        inv_info: str,
        ident: str,
        title: str,
        options: Sequence[tuple[str, str]],
    ) -> None:
        super().__init__(
            title=title,
            sort_index=800,
            info=inv_info,
            query_filter=query_filters.MultipleOptionsQuery(
                ident=ident,
                options=[(f"{ident}_{k}", v) for k, v in options],
                rows_filter=partial(_filter_rows_table_choice, ident),
            ),
            group=FilterGroup.INVENTORY,
        )


class FilterInvtableIntegerRange(_FilterNumberRange):
    def __init__(
        self,
        *,
        inv_info: str,
        ident: str,
        title: str,
        unit_choices: Mapping[str, FilterInvFloatChoice],
    ) -> None:
        super().__init__(
            inv_info=inv_info,
            ident=ident,
            title=title,
            unit_choices=unit_choices,
            filter_row=query_filters.column_value_in_range,
        )


class FilterInvtableAgeRange(_FilterNumberRange):
    def __init__(
        self,
        *,
        inv_info: str,
        ident: str,
        title: str,
        unit_choices: Mapping[str, FilterInvFloatChoice],
    ) -> None:
        super().__init__(
            inv_info=inv_info,
            ident=ident,
            title=title,
            unit_choices=unit_choices,
            filter_row=query_filters.column_age_in_range,
        )


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
            group=FilterGroup.INVENTORY,
        )


class FilterInvtableTextWithSortKey(_FilterTextRange):
    def __init__(
        self,
        *,
        inv_info: str,
        ident: str,
        title: str,
        sort_key: Callable[[str], Comparable],
    ) -> None:
        super().__init__(
            inv_info=inv_info,
            ident=ident,
            title=title,
            from_label=_("From:"),
            until_label=_("To:"),
            rows_filter=partial(
                _filter_rows_with_sort_key, ident, lambda row: row.get(ident), sort_key
            ),
        )


class FilterInvtableDualChoice(Filter):
    def __init__(
        self, *, inv_info: str, ident: str, title: str, choices: Sequence[tuple[str, str]]
    ) -> None:
        self._choices = choices
        self._html_var = ident
        super().__init__(
            ident=ident,
            title=title,
            sort_index=800,
            info=inv_info,
            htmlvars=[self._html_var],
            link_columns=[],
            group=FilterGroup.INVENTORY,
        )

    @override
    def components(
        self, _request_cache: RequestCache[RequestCacheConfig]
    ) -> Iterable[FilterComponent]:
        if self._choices:
            yield DualList(id=self._html_var, choices=dict(self._choices))
        else:
            yield StaticText(text=_("There are no elements for selection."))

    @override
    def filter_table(self, context: VisualContext, rows: Rows) -> Rows:
        if selection := [
            v
            for v in context.get(self._html_var, {}).get(self._html_var, "").strip().split("|")
            if v
        ]:
            return [row for row in rows if str(row[self._html_var]) in selection]
        return rows


class FilterInvtableVersion(_FilterTextRange):
    def __init__(self, *, inv_info: str, ident: str, title: str) -> None:
        super().__init__(
            inv_info=inv_info,
            ident=ident,
            title=title,
            from_label=_("Min.&nbsp;Version:"),
            until_label=_("Max.&nbsp;Version:"),
            rows_filter=partial(query_filters.version_in_range, ident, list(_request_vars(ident))),
        )


class FilterHasInv(_FilterInvOption):
    def __init__(self) -> None:
        super().__init__(
            title=_l("Has inventory data"),
            sort_index=801,
            info="host",
            query_filter=query_filters.TristateQuery(
                ident="has_inv",
                filter_code=lambda _x: "",  # No Livestatus filtering right now
                filter_row=query_filters.has_inventory,
            ),
            is_show_more=True,
            group=FilterGroup.HOST_HAS,
        )


def _find_package(
    packages: Sequence[Mapping[str, SDValue]],
    name: str | re.Pattern[str],
    from_version: str,
    to_version: str,
) -> bool:
    for package in packages:
        if isinstance(name, str):
            if package["name"] != name:
                continue
        elif not name.search(str(package["name"])):
            continue
        if not from_version and not to_version:
            return True
        if (version := package.get("version")) is None:
            continue
        if from_version and cmp_version(str(version), from_version) == -1:
            continue
        if to_version and cmp_version(str(version), to_version) == 1:
            continue
        return True
    return False


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
            group=FilterGroup.HOST_HAS,
        )

    @override
    def need_inventory(self, value: FilterHTTPVariables) -> bool:
        return bool(value.get(self._varprefix + "name", "").strip())

    @override
    def display(
        self, value: FilterHTTPVariables, _request_cache: RequestCache[RequestCacheConfig]
    ) -> None:
        # keep this in sync with components(), remove once all filter menus are switched to vue
        # this special styling is not supported by the current components
        html.text_input(
            varname=self._varprefix + "name",
            default_value=value.get(self._varprefix + "name", ""),
        )
        html.br()
        RadioButton(
            id=self._varprefix + "match",
            choices={
                "exact": _("exact match"),
                "regex": _("regular expression, substring match"),
            },
            default_value="exact",
        ).render_html(self.ident, value)
        html.br()
        html.open_span(class_="min_max_row")
        html.write_text_permissive(_("Min.&nbsp;Version: "))
        html.text_input(
            varname=self._varprefix + "version_from",
            default_value=value.get(self._varprefix + "version_from", ""),
            size=9,
        )
        html.write_text_permissive(" &nbsp; ")
        html.write_text_permissive(_("Max.&nbsp;Version: "))
        html.text_input(
            varname=self._varprefix + "version_to",
            default_value=value.get(self._varprefix + "version_to", ""),
            size=9,
        )
        html.close_span()
        html.br()
        html.checkbox(
            self._varprefix + "negate",
            False,
            label=_("Negate: find hosts <b>not</b> having this package"),
        )

    @override
    def components(
        self, _request_cache: RequestCache[RequestCacheConfig]
    ) -> Iterable[FilterComponent]:
        yield TextInput(id=self._varprefix + "name")
        yield RadioButton(
            id=self._varprefix + "match",
            choices={
                "exact": _("exact match"),
                "regex": _("regular expression, substring match"),
            },
            default_value="exact",
        )
        yield HorizontalGroup(
            components=[
                TextInput(
                    id=self._varprefix + "version_from",
                    label=_("Min.&nbsp;Version:"),
                ),
                TextInput(
                    id=self._varprefix + "version_to",
                    label=_("Max.&nbsp;Version:"),
                ),
            ]
        )
        yield Checkbox(
            id=self._varprefix + "negate",
            label=_("Negate: find hosts <b>not</b> having this package"),
            default_value=False,
        )

    @override
    def filter_table(self, context: VisualContext, rows: Rows) -> Rows:
        value = context.get(self.ident, {})
        name = value.get(self._varprefix + "name", "")
        if not name.strip():
            return rows

        package_name: str | re.Pattern[str] = name
        if value.get(self._varprefix + "match", "") == "regex":
            try:
                package_name = re.compile(name)
            except re.error:
                raise MKUserError(
                    self._varprefix + "name",
                    _(
                        "Your search statement is not valid. You need to provide a regular "
                        "expression (regex). For example you need to use <tt>\\\\</tt> instead of <tt>\\</tt> "
                        "if you want to search for a single backslash."
                    ),
                )
        from_version = value.get(self._varprefix + "version_from", "").strip()
        to_version = value.get(self._varprefix + "version_to", "").strip()
        negate = bool(value.get(self._varprefix + "negate", ""))
        return [
            row
            for row in rows
            if _find_package(
                row["host_inventory"].get_rows(("software", "packages")),
                package_name,
                from_version,
                to_version,
            )
            != negate
        ]
