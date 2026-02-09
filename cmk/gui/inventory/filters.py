#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="type-arg"

import re
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from functools import partial

from cmk.gui import query_filters
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _, _l
from cmk.gui.ifaceoper import interface_oper_states, interface_port_types
from cmk.gui.num_split import cmp_version
from cmk.gui.type_defs import (
    FilterHeader,
    FilterHTTPVariables,
    Row,
    Rows,
    VisualContext,
)
from cmk.gui.utils.speaklater import LazyString
from cmk.gui.visuals.filter import (
    CheckboxRowFilter,
    DualListFilter,
    Filter,
    FilterGroup,
    FilterNumberRange,
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
from cmk.inventory.structured_data import SDValue
from cmk.inventory_ui.v1_unstable import Comparable

from ._tree import InventoryPath


# Filter tables
def _make_filter_row_bool(inventory_path: InventoryPath) -> Callable[[bool, Row], bool]:
    def keep_row(on: bool, row: Row) -> bool:
        return row["host_inventory"].get_attribute(inventory_path.path, inventory_path.key) is on

    return keep_row


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
                filter_row=_make_filter_row_bool(inventory_path),
            ),
            is_show_more=is_show_more,
            group=FilterGroup.INVENTORY,
        )

    def need_inventory(self, value: FilterHTTPVariables) -> bool:
        return self.query_filter.selection_value(value) != self.query_filter.ignore


@dataclass(frozen=True)
class FilterInvFloatChoice:
    unit: str
    factor: int


_MaybeBounds = tuple[int | float | None, int | float | None]


class _FilterNumberRange(Filter):
    """Filter for choosing a range in which a certain integer lies"""

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

        self._html_var_from = f"{ident}_from"
        self._html_var_from_prefix = f"{ident}_from_prefix"
        self._html_var_until = f"{ident}_until"
        self._html_var_until_prefix = f"{ident}_until_prefix"
        super().__init__(
            ident=ident,
            title=title,
            sort_index=800,
            info=inv_info,
            htmlvars=[
                self._html_var_from,
                self._html_var_from_prefix,
                self._html_var_until,
                self._html_var_until_prefix,
            ],
            link_columns=[],
            group=FilterGroup.INVENTORY,
        )

    def display(self, value: FilterHTTPVariables) -> None:
        # keep this in sync with components(), remove once all filter menus are switched to vue
        # this special styling is not supported by the current components
        unit_choices = [(n, c.unit) for n, c in self._unit_choices.items()]

        html.open_table()

        html.open_tr()
        html.open_td()
        html.write_text_permissive(_("From:") + "&nbsp;")
        html.close_td()

        html.open_td()
        html.text_input(
            self._html_var_from,
            default_value=value.get(self._html_var_from, ""),
            style="width: 80px;",
        )
        html.close_td()

        if unit_choices:
            html.open_td()
            html.dropdown(
                self._html_var_from_prefix,
                unit_choices,
                deflt=value.get(self._html_var_from_prefix, ""),
            )
            html.close_td()
            html.close_tr()

        html.open_tr()
        html.open_td()
        html.write_text_permissive(_("To:") + "&nbsp;")
        html.close_td()

        html.open_td()
        html.text_input(
            self._html_var_until,
            default_value=value.get(self._html_var_until, ""),
            style="width: 80px;",
        )
        html.close_td()

        if unit_choices:
            html.open_td()
            html.dropdown(
                self._html_var_until_prefix,
                unit_choices,
                deflt=value.get(self._html_var_until_prefix, ""),
            )
            html.close_td()
            html.close_tr()

        html.close_table()

    def components(self) -> Iterable[FilterComponent]:
        unit_choices = {n: c.unit for n, c in self._unit_choices.items()}

        def _from() -> Iterator[TextInput | Dropdown]:
            yield TextInput(
                id=self._html_var_from,
                label=_("From:"),
            )
            if unit_choices:
                yield Dropdown(
                    id=self._html_var_from_prefix,
                    choices=unit_choices,
                )

        def _to() -> Iterator[TextInput | Dropdown]:
            yield TextInput(
                id=self._html_var_until,
                label=_("To:"),
            )
            if unit_choices:
                yield Dropdown(
                    id=self._html_var_until_prefix,
                    choices=unit_choices,
                )

        yield HorizontalGroup(components=list(_from()))
        yield HorizontalGroup(components=list(_to()))

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
        return (
            (
                None
                if (var := filter_vars.get(self._html_var_from)) is None
                else self._get_bound(var, filter_vars.get(self._html_var_from_prefix))
            ),
            (
                None
                if (var := filter_vars.get(self._html_var_until)) is None
                else self._get_bound(var, filter_vars.get(self._html_var_until_prefix))
            ),
        )

    def filter_table(self, context: VisualContext, rows: Rows) -> Rows:
        from_var, until_var = self._get_bounds(context.get(self.ident, {}))
        return (
            rows
            if from_var is None and until_var is None
            else [row for row in rows if self._filter_row(row, self.ident, (from_var, until_var))]
        )

    def need_inventory(self, value: FilterHTTPVariables) -> bool:
        return any(b is not None for b in self._get_bounds(value))


def _make_filter_row_float(
    inventory_path: InventoryPath,
) -> Callable[[Row, str, _MaybeBounds], bool]:
    def row_filter(row: Row, column: str, bounds: _MaybeBounds) -> bool:
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
            return bool(
                regex.search(
                    str(
                        row["host_inventory"].get_attribute(inventory_path.path, inventory_path.key)
                    )
                )
            )

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

    def need_inventory(self, value: FilterHTTPVariables) -> bool:
        return bool(value.get(self.htmlvars[0], "").strip().lower())


def _filter_with_sort_key(
    *,
    value: SDValue,
    from_value: str | None,
    until_value: str | None,
    sort_key: Callable[[str], Comparable],
) -> bool:
    if value is None:
        return not from_value and not until_value

    if not isinstance(value, str):
        raise TypeError(value)

    sortable_value = sort_key(value)

    if from_value and until_value:
        return sort_key(from_value) < sortable_value < sort_key(until_value)

    if from_value and not until_value:
        return sort_key(from_value) < sortable_value

    if not from_value and until_value:
        return sortable_value < sort_key(until_value)

    return True


def _filter_rows_text_with_sort_key(
    ident: str,
    request_vars: list[str],
    inventory_path: InventoryPath,
    sort_key: Callable[[str], Comparable],
    context: VisualContext,
    rows: Rows,
) -> Rows:
    from_value, until_value = (context.get(ident, {}).get(v) for v in request_vars)
    return [
        r
        for r in rows
        if _filter_with_sort_key(
            value=r["host_inventory"].get_attribute(inventory_path.path, inventory_path.key),
            from_value=from_value,
            until_value=until_value,
            sort_key=sort_key,
        )
    ]


class FilterInvTextWithSortKey(Filter):
    def __init__(
        self,
        *,
        ident: str,
        title: str | LazyString,
        inventory_path: InventoryPath,
        sort_key: Callable[[str], Comparable],
        is_show_more: bool = True,
    ) -> None:
        request_vars = [ident + "_from", ident + "_until"]
        self.query_filter = query_filters.Query(
            ident=ident,
            request_vars=request_vars,
            rows_filter=partial(
                _filter_rows_text_with_sort_key, ident, request_vars, inventory_path, sort_key
            ),
        )
        super().__init__(
            ident=self.query_filter.ident,
            title=title,
            sort_index=800,
            info="host",
            htmlvars=self.query_filter.request_vars,
            link_columns=[],
            is_show_more=is_show_more,
            group=FilterGroup.INVENTORY,
        )

    def display(self, value: FilterHTTPVariables) -> None:
        # keep this in sync with components(), remove once all filter menus are switched to vue
        # this special styling is not supported by the current components
        html.write_text_permissive(_("From:") + "&nbsp;")
        html.text_input(
            self.htmlvars[0], default_value=value.get(self.htmlvars[0], ""), style="width: 80px;"
        )
        html.write_text_permissive(" &nbsp; " + _("To:") + "&nbsp;")
        html.text_input(
            self.htmlvars[1], default_value=value.get(self.htmlvars[1], ""), style="width: 80px;"
        )

    def components(self) -> Iterable[FilterComponent]:
        yield HorizontalGroup(
            components=[
                TextInput(id=self.query_filter.request_vars[0], label=_("From:")),
                TextInput(id=self.query_filter.request_vars[1], label=_("To:")),
            ]
        )

    def filter_table(self, context: VisualContext, rows: Rows) -> Rows:
        return self.query_filter.filter_table(context, rows)

    def need_inventory(self, value: FilterHTTPVariables) -> bool:
        return bool(value.get(self.htmlvars[0], "").strip().lower())


class FilterInvChoice(FilterOption):
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
                options=list(options),
                filter_code=lambda x: "",
                filter_row=lambda selection, row: (selection == "yes") == row.get(ident),
            ),
            is_show_more=is_show_more,
            group=FilterGroup.INVENTORY,
        )

    def need_inventory(self, value: FilterHTTPVariables) -> bool:
        return self.query_filter.selection_value(value) != self.query_filter.ignore


def _filter_rows_table_choice(ident: str, context: VisualContext, rows: Rows) -> Rows:
    filter_vars = context.get(ident, {})

    def _add_row(row: Row) -> bool:
        # Apply filter if and only if a filter value is set
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


def _filter_rows_table_text_with_sort_key(
    ident: str,
    request_vars: list[str],
    sort_key: Callable[[str], Comparable],
    context: VisualContext,
    rows: Rows,
) -> Rows:
    from_value, until_value = (context.get(ident, {}).get(v) for v in request_vars)
    return [
        r
        for r in rows
        if _filter_with_sort_key(
            value=r.get(ident),
            from_value=from_value,
            until_value=until_value,
            sort_key=sort_key,
        )
    ]


class FilterInvtableTextWithSortKey(Filter):
    def __init__(
        self,
        *,
        inv_info: str,
        ident: str,
        title: str,
        sort_key: Callable[[str], Comparable],
    ) -> None:
        request_vars = [ident + "_from", ident + "_until"]
        self.query_filter = query_filters.Query(
            ident=ident,
            request_vars=request_vars,
            rows_filter=partial(
                _filter_rows_table_text_with_sort_key, ident, request_vars, sort_key
            ),
        )
        super().__init__(
            ident=self.query_filter.ident,
            title=title,
            sort_index=800,
            info=inv_info,
            htmlvars=self.query_filter.request_vars,
            link_columns=[],
            group=FilterGroup.INVENTORY,
        )

    def display(self, value: FilterHTTPVariables) -> None:
        # keep this in sync with components(), remove once all filter menus are switched to vue
        # this special styling is not supported by the current components
        html.write_text_permissive(_("From:"))
        html.text_input(self.htmlvars[0], default_value=value.get(self.htmlvars[0], ""), size=7)
        html.write_text_permissive(" &nbsp; ")
        html.write_text_permissive(_("To:"))
        html.text_input(self.htmlvars[1], default_value=value.get(self.htmlvars[1], ""), size=7)

    def components(self) -> Iterable[FilterComponent]:
        yield HorizontalGroup(
            components=[
                TextInput(id=self.htmlvars[0], label=_("From:")),
                TextInput(id=self.htmlvars[1], label=_("To:")),
            ]
        )

    def filter_table(self, context: VisualContext, rows: Rows) -> Rows:
        return self.query_filter.filter_table(context, rows)


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

    def display(self, value: FilterHTTPVariables) -> None:
        if not self._choices:
            html.write_text_permissive(_("There are no elements for selection."))
            return

        selected_from_value = value.get(self._html_var, "").strip().split("|")
        selected = []
        unselected = []
        for k, v in self._choices:
            if k in selected_from_value:
                selected.append((k, v))
            else:
                unselected.append((k, v))

        select_func = "cmk.valuespecs.duallist_switch('unselected', '%s', %d);" % (
            self._html_var,
            0,
        )
        unselect_func = "cmk.valuespecs.duallist_switch('selected', '%s', %d);" % (
            self._html_var,
            0,
        )

        html.open_table(class_=["vs_duallist"])

        html.open_tr()
        html.open_td(class_="head")
        html.write_text_permissive(_("Available"))
        html.a(">", href="javascript:%s;" % select_func, class_=["control", "add"])
        html.close_td()

        html.open_td(class_="head")
        html.write_text_permissive(_("Selected"))
        html.a("<", href="javascript:%s;" % unselect_func, class_=["control", "del"])
        html.close_td()
        html.close_tr()

        html.open_tr()
        for suffix, choices, func in [
            ("unselected", unselected, select_func),
            ("selected", selected, unselect_func),
        ]:
            html.open_td()
            html.dropdown(
                f"{self._html_var}_{suffix}",
                choices,
                deflt="",
                multiple=True,
                style="height: 64px",
                ondblclick=func,
                onchange="",
                locked_choice=None,
            )

            html.close_td()
        html.close_tr()

        html.close_table()

        html.hidden_field(
            self._html_var,
            "|".join([str(k) for k, v in selected]),
            id_=self._html_var,
            add_var=True,
        )

    def components(self) -> Iterable[FilterComponent]:
        if self._choices:
            yield DualList(id=self._html_var, choices=dict(self._choices))
        else:
            yield StaticText(text=_("There are no elements for selection."))

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        return ""

    def filter_table(self, context: VisualContext, rows: Rows) -> Rows:
        if selection := [
            v
            for v in context.get(self._html_var, {}).get(self._html_var, "").strip().split("|")
            if v
        ]:
            return [row for row in rows if str(row[self._html_var]) in selection]
        return rows  # No types selected, filter is unused


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
            group=FilterGroup.INVENTORY,
        )


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
            group=FilterGroup.INVENTORY,
        )

    def display(self, value: FilterHTTPVariables) -> None:
        # keep this in sync with components(), remove once all filter menus are switched to vue
        # this special styling is not supported by the current components
        html.write_text_permissive(_("Min.&nbsp;Version:"))
        html.text_input(self.htmlvars[0], default_value=value.get(self.htmlvars[0], ""), size=7)
        html.write_text_permissive(" &nbsp; ")
        html.write_text_permissive(_("Max.&nbsp;Version:"))
        html.text_input(self.htmlvars[1], default_value=value.get(self.htmlvars[1], ""), size=7)

    def components(self) -> Iterable[FilterComponent]:
        yield HorizontalGroup(
            components=[
                TextInput(
                    id=self.htmlvars[0],
                    label=_("Min.&nbsp;Version:"),
                ),
                TextInput(
                    id=self.htmlvars[1],
                    label=_("Max.&nbsp;Version:"),
                ),
            ]
        )

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
            group=FilterGroup.INVENTORY,
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
            group=FilterGroup.INVENTORY,
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
            group=FilterGroup.INVENTORY,
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
            group=FilterGroup.INVENTORY,
        )

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        return ""

    def filter_table(self, context: VisualContext, rows: Rows) -> Rows:
        value = context.get(self.query_filter.ident, {})
        selection = self.query_filter.selection(value)

        if not selection:
            return rows  # No types selected, filter is unused
        return [row for row in rows if str(row[self.query_filter.column]) in selection]


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
            group=FilterGroup.HOST_HAS,
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
            group=FilterGroup.HOST_HAS,
        )

    def need_inventory(self, value: FilterHTTPVariables) -> bool:
        return bool(value.get(self._varprefix + "name"))

    def display(self, value: FilterHTTPVariables) -> None:
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

    def components(self) -> Iterable[FilterComponent]:
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

    def find_package(
        self,
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
                return True  # version not relevant
            version = package["version"]
            if from_version == to_version and from_version != version:
                continue
            if from_version and self.version_is_lower(str(version), from_version):
                continue
            if to_version and self.version_is_higher(str(version), to_version):
                continue
            return True
        return False

    def version_is_lower(self, a: str | None, b: str | None) -> bool:
        return a != b and not self.version_is_higher(a, b)

    def version_is_higher(self, a: str | None, b: str | None) -> bool:
        return cmp_version(a, b) == 1
