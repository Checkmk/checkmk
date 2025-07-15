#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Here are livestatus filters isolated out of the visuals GUI logic. They shall
# then later be replaced using the new query helpers.

import re
import time
from collections.abc import Callable
from typing import Literal, override

import livestatus

from cmk.utils.labels import LabelGroups
from cmk.utils.tags import TagGroupID

from cmk.gui.config import active_config
from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.num_split import cmp_version
from cmk.gui.type_defs import FilterHeader, FilterHTTPVariables, Row, Rows, VisualContext
from cmk.gui.utils.labels import (
    encode_label_groups_for_livestatus,
    encode_labels_for_livestatus,
    Label,
    Labels,
    parse_label_groups_from_http_vars,
    parse_labels_value,
)
from cmk.gui.utils.user_errors import user_errors

SitesOptions = list[tuple[str, str]]


def lq_logic(filter_condition: str, values: list[str], join: str) -> str:
    """JOIN with (Or, And) FILTER_CONDITION the VALUES for a livestatus query"""
    conditions = "".join(f"{filter_condition} {livestatus.lqencode(x)}\n" for x in values)
    connective = "%s: %d\n" % (join, len(values)) if len(values) > 1 else ""
    return conditions + connective


class Query:
    "This is the Null filter and default class as it does nothing."

    def __init__(
        self,
        *,
        ident: str,
        request_vars: list[str],
        livestatus_query: Callable[..., FilterHeader] | None = None,
        rows_filter: Callable[..., Rows] | None = None,
    ):
        self.ident = ident
        self.request_vars = request_vars
        self.livestatus_query = livestatus_query or (lambda x: "")
        self.rows_filter = rows_filter or (lambda _ctx, rows: rows)

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        return self.livestatus_query(value)

    def filter_table(self, context: VisualContext, rows: Rows) -> Rows:
        return self.rows_filter(context, rows)


class MultipleOptionsQuery(Query):
    def __init__(
        self,
        *,
        ident: str,
        options: SitesOptions,
        livestatus_query: Callable[[FilterHTTPVariables], FilterHeader] | None = None,
        rows_filter: Callable[..., Rows] | None = None,
    ):
        # TODO: options helps with data validation but conflicts with the Filter job
        super().__init__(
            ident=ident,
            request_vars=[v[0] for v in options],
            livestatus_query=livestatus_query,
            rows_filter=rows_filter,
        )
        self.options = options

    @override
    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        if self.ident == "hostgroupvisibility":
            # jump directly because selection is empty filter
            return self.livestatus_query(value)

        if all(value.values()):  # everything on, skip filter
            return ""
        return self.livestatus_query(value)


# Tri State filter
def default_tri_state_options() -> SitesOptions:
    return [("1", _("yes")), ("0", _("no")), ("-1", _("(ignore)"))]


def tri_state_type_options() -> SitesOptions:
    return [
        ("0", _("SOFT")),
        ("1", _("HARD")),
        ("-1", _("(ignore)")),
    ]


def tri_state_log_notifications_options() -> SitesOptions:
    return [
        ("1", _("Show just preliminary notifications")),
        ("0", _("Show just end-user-notifications")),
        ("-1", _("Show all phases of notifications")),
    ]


class SingleOptionQuery(Query):
    def __init__(
        self,
        *,
        ident: str,
        options: SitesOptions,
        filter_code: Callable[[str], FilterHeader],
        filter_row: Callable[[str, Row], bool] | None = None,
    ):
        super().__init__(ident=ident, request_vars=[ident])
        # TODO: options helps with data validation but conflicts with the Filter job
        self.options = options
        self.filter_code = filter_code
        self.filter_row = filter_row or (lambda _selection, _row: True)
        self.ignore = self.options[-1][0]

    def selection_value(self, value: FilterHTTPVariables) -> str:
        selection = value.get(self.request_vars[0], "")
        if selection in [x for (x, _) in self.options]:
            return selection
        return self.ignore

    @override
    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        selection = self.selection_value(value)
        if selection == self.ignore:
            return ""
        return self.filter_code(selection)

    @override
    def filter_table(self, context: VisualContext, rows: Rows) -> Rows:
        value = context.get(self.ident, {})
        selection = self.selection_value(value)
        if selection == self.ignore:
            return rows

        return [row for row in rows if self.filter_row(selection, row)]


class TristateQuery(SingleOptionQuery):
    def __init__(
        self,
        *,
        ident: str,
        filter_code: Callable[[bool], FilterHeader],
        filter_row: Callable[[bool, Row], bool] | None = None,
        options: SitesOptions | None = None,
    ):
        super().__init__(
            ident=ident,
            filter_code=lambda pick: filter_code(pick == "1"),
            filter_row=(
                lambda pick, row: (filter_row(pick == "1", row) if filter_row is not None else True)
            ),
            options=options or default_tri_state_options(),
        )
        self.request_vars = ["is_" + ident]


def state_type(on: bool) -> FilterHeader:
    return "Filter: state_type = %d\n" % int(on)


def service_perfdata_toggle(on: bool) -> FilterHeader:
    return f"Filter: service_perf_data {'!=' if on else '='} \n"


def host_service_perfdata_toggle(on: bool) -> FilterHeader:
    if on:
        return "Filter: service_scheduled_downtime_depth > 0\nFilter: host_scheduled_downtime_depth > 0\nOr: 2\n"
    return "Filter: service_scheduled_downtime_depth = 0\nFilter: host_scheduled_downtime_depth = 0\nAnd: 2\n"


def staleness(obj: Literal["host", "service"]) -> Callable[[bool], FilterHeader]:
    def toggler(on: bool) -> FilterHeader:
        operator = ">=" if on else "<"
        return f"Filter: {obj}_staleness {operator} {active_config.staleness_threshold:0.2f}\n"

    return toggler


def column_flag(column: str) -> Callable[[bool], FilterHeader]:
    return lambda positive: f"Filter: {column} {'!=' if positive else '='} 0\n"


def log_notification_phase(column: str) -> Callable[[bool], FilterHeader]:
    def filterheader(positive: bool) -> FilterHeader:
        # Note: this filter also has to work for entries that are no notification.
        # In that case the filter is passive and lets everything through
        if positive:
            return f"Filter: {column} = check-mk-notify\nFilter: {column} =\nOr: 2\n"
        return "Filter: %s != check-mk-notify\n" % column

    return filterheader


def starred(what: Literal["host", "service"]) -> Callable[[bool], FilterHeader]:
    def filterheader(positive: bool) -> FilterHeader:
        if positive:
            aand, oor, eq = "And", "Or", "="
        else:
            aand, oor, eq = "Or", "And", "!="

        stars = user.stars
        filters = ""
        count = 0
        if what == "host":
            for star in stars:
                if ";" in star:
                    continue
                filters += f"Filter: host_name {eq} {livestatus.lqencode(star)}\n"
                count += 1
        else:
            for star in stars:
                if ";" not in star:
                    continue
                h, s = star.split(";")
                filters += f"Filter: host_name {eq} {livestatus.lqencode(h)}\n"
                filters += f"Filter: service_description {eq} {livestatus.lqencode(s)}\n"
                filters += "%s: 2\n" % aand
                count += 1

        # No starred object and show only starred -> show nothing
        if count == 0 and positive:
            return "Filter: host_state = -4612\n"

        # no starred object and show unstarred -> show everything
        if count == 0:
            return ""

        filters += "%s: %d\n" % (oor, count)
        return filters

    return filterheader


def has_inventory(on: bool, row: Row) -> bool:
    if "host_inventory" not in row:
        return False
    return bool(row["host_inventory"]) is on


# Filter Time
def time_filter_options() -> SitesOptions:
    ranges = [(86400, _("days")), (3600, _("hours")), (60, _("min")), (1, _("sec"))]
    choices = [(str(sec), title + " " + _("ago")) for sec, title in ranges]
    choices += [
        ("abs", _("Date (YYYY-MM-DD)")),
        ("ts", _("Timestamp (YYYY-MM-DD HH:mm:ss)")),
        ("unix", _("UNIX timestamp")),
    ]
    return choices


MaybeBounds = tuple[int | float | None, int | float | None]


class NumberRangeQuery(Query):
    def __init__(
        self,
        *,
        ident: str,
        column: str | None = None,
        filter_livestatus: bool = True,
        filter_row: Callable[[Row, str, MaybeBounds], bool] | None = None,
        request_var_suffix: str = "",
        bound_rescaling: int | float = 1,
    ):
        super().__init__(
            ident=ident,
            request_vars=[
                ident + "_from" + request_var_suffix,
                ident + "_until" + request_var_suffix,
            ],
        )
        self.column = column or ident
        self.filter_livestatus = filter_livestatus
        self.filter_row = filter_row
        self.request_var_suffix = request_var_suffix
        self.bound_rescaling = bound_rescaling

    def extractor(self, value: FilterHTTPVariables) -> MaybeBounds:
        return (
            self.get_bound(self.ident + "_from" + self.request_var_suffix, value),
            self.get_bound(self.ident + "_until" + self.request_var_suffix, value),
        )

    def get_bound(self, var: str, value: FilterHTTPVariables) -> int | float | None:
        try:
            if isinstance(self.bound_rescaling, int):
                return int(value.get(var, "")) * self.bound_rescaling
            return float(value.get(var, "")) * self.bound_rescaling
        except ValueError:
            return None

    @override
    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        if not self.filter_livestatus:
            return ""

        filtertext = ""
        for op, bound in zip((">=", "<="), self.extractor(value)):
            if bound is not None:
                filtertext += "Filter: %s %s %d\n" % (self.column, op, bound)
        return filtertext

    @override
    def filter_table(self, context: VisualContext, rows: Rows) -> Rows:
        values = context.get(self.ident, {})
        from_value, to_value = self.extractor(values)

        if (self.filter_row is None) or (from_value is None and to_value is None):
            return rows

        return [row for row in rows if self.filter_row(row, self.column, (from_value, to_value))]


def value_in_range(value: int | float, bounds: MaybeBounds) -> bool:
    from_value, to_value = bounds

    if from_value and value < from_value:
        return False

    if to_value and value > to_value:
        return False
    return True


def column_value_in_range(row: Row, column: str, bounds: MaybeBounds) -> bool:
    value = row.get(column)
    if not isinstance(value, int | float):
        return False
    return value_in_range(value, bounds)


def column_age_in_range(row: Row, column: str, bounds: MaybeBounds) -> bool:
    value = row.get(column)
    if not isinstance(value, int | float):
        return False
    return value_in_range(time.time() - value, bounds)


def version_in_range(
    ident: str, request_vars: list[str], context: VisualContext, rows: Rows
) -> Rows:
    values = context.get(ident, {})
    from_version, to_version = (values.get(v) for v in request_vars)

    new_rows = []
    for row in rows:
        version = row.get(ident, "")
        if from_version and cmp_version(version, from_version) == -1:
            continue
        if to_version and cmp_version(version, to_version) == 1:
            continue
        new_rows.append(row)

    return new_rows


class TimeQuery(NumberRangeQuery):
    def __init__(self, *, ident: str, column: str | None = None) -> None:
        super().__init__(ident=ident, column=column)
        self.request_vars.extend([var + "_range" for var in self.request_vars])

    @override
    def get_bound(self, var: str, value: FilterHTTPVariables) -> int | None:
        rangename = value.get(var + "_range")
        if rangename == "ts":
            try:
                return int(time.mktime(time.strptime(value[var], "%Y-%m-%d %H:%M:%S")))
            except ValueError:
                user_errors.add(
                    MKUserError(
                        var,
                        _("Please enter the date in the format YYYY-MM-DD HH:mm:ss."),
                    )
                )
                return None
        if rangename == "abs":
            try:
                return int(time.mktime(time.strptime(value[var], "%Y-%m-%d")))
            except ValueError:
                user_errors.add(
                    MKUserError(var, _("Please enter the date in the format YYYY-MM-DD."))
                )
                return None

        if rangename == "unix":
            return int(value[var])
        if rangename is None:
            return None

        try:
            if (count := value.get(var)) is None:
                return None
            secs = int(count) * int(rangename)
            return int(time.time()) - secs
        except ValueError:
            return None


class KubernetesQuery(Query):
    def __init__(
        self,
        *,
        ident: str,
        kubernetes_object_type: str,
    ):
        super().__init__(ident=ident, request_vars=[ident])
        self.column = "host_labels"
        self.link_columns: list[str] = []
        self.negateable = False
        self._kubernetes_object_type = kubernetes_object_type

    @override
    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        if filter_value := value.get(self.request_vars[0]):
            return encode_labels_for_livestatus(
                column=self.column,
                labels=[
                    Label(
                        f"cmk/kubernetes/{self._kubernetes_object_type}",
                        filter_value,
                        False,
                    )
                ],
            )
        return ""


class TextQuery(Query):
    def __init__(
        self,
        *,
        ident: str,
        op: str,
        negateable: bool = False,
        request_var: str | None = None,
        column: str | None = None,
    ):
        request_vars = [request_var or ident]
        if negateable:
            request_vars.append("neg_" + (request_var or ident))

        super().__init__(ident=ident, request_vars=request_vars)
        self.op = op
        self.column = column or ident
        self.negateable = negateable
        self.link_columns = [self.column]

    @override
    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        if value.get(self.request_vars[0]):
            return self._filter(value)
        return ""

    def _negate_symbol(self, value: FilterHTTPVariables) -> str:
        return "!" if self.negateable and value.get(self.request_vars[1]) else ""

    def _filter(self, value: FilterHTTPVariables) -> FilterHeader:
        return f"Filter: {self.column} {self._negate_symbol(value)}{self.op} {livestatus.lqencode(value[self.request_vars[0]])}\n"


class TableTextQuery(TextQuery):
    def __init__(
        self, *, ident: str, row_filter: Callable[[str, str], Callable[[Row], bool]]
    ) -> None:
        super().__init__(ident=ident, op="=")
        self.link_columns = []
        self.row_filter = row_filter

    @override
    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        return ""

    @override
    def filter_table(self, context: VisualContext, rows: Rows) -> Rows:
        value = context.get(self.ident, {})
        column = self.column
        filtertext = value.get(column, "").strip().lower()
        if not filtertext:
            return rows
        keep = self.row_filter(filtertext, column)

        return [row for row in rows if keep(row)]


def re_ignorecase(text: str, varprefix: str) -> re.Pattern:
    try:
        return re.compile(text, re.IGNORECASE)
    except re.error:
        raise MKUserError(
            varprefix,
            _(
                "Your search statement is not valid. You need to provide a regular "
                "expression (regex). For example you need to use <tt>\\\\</tt> instead of <tt>\\</tt> "
                "if you like to search for a single backslash."
            ),
        )


def filter_by_column_textregex(filtertext: str, column: str) -> Callable[[Row], bool]:
    regex = re_ignorecase(filtertext, column)
    return lambda row: bool(regex.search(str(row.get(column, ""))))


class CheckCommandQuery(TextQuery):
    @override
    def _filter(self, value: FilterHTTPVariables) -> FilterHeader:
        return f"Filter: {self.column} {self.op} ^{livestatus.lqencode(value[self.request_vars[0]])}(!.*)?\n"


class HostnameOrAliasQuery(TextQuery):
    def __init__(self) -> None:
        super().__init__(ident="hostnameoralias", column="host_name", op="~~", negateable=False)
        self.link_columns = ["host_alias", "host_name"]

    @override
    def _filter(self, value: FilterHTTPVariables) -> FilterHeader:
        host = livestatus.lqencode(value[self.request_vars[0]])

        return lq_logic("Filter:", [f"host_name {self.op} {host}", f"alias {self.op} {host}"], "Or")


class OptEventEffectiveContactgroupQuery(TextQuery):
    def __init__(self) -> None:
        super().__init__(
            ident="optevent_effective_contactgroup",
            request_var="optevent_effective_contact_group",
            column="host_contact_groups",
            op=">=",
            negateable=True,
        )

        self.link_columns = [
            "event_contact_groups",
            "event_contact_groups_precedence",
            "host_contact_groups",
        ]

    @override
    def _filter(self, value: FilterHTTPVariables) -> FilterHeader:
        negate = self._negate_symbol(value)
        selected_value = livestatus.lqencode(value[self.request_vars[0]])

        return (
            "Filter: event_contact_groups_precedence = host\n"
            "Filter: host_contact_groups %s>= %s\n"
            "And: 2\n"
            "Filter: event_contact_groups_precedence = rule\n"
            "Filter: event_contact_groups %s>= %s\n"
            "And: 2\n"
            "Or: 2\n" % (negate, selected_value, negate, selected_value)
        )


class IPAddressQuery(Query):
    def __init__(self, *, ident: str, what: str) -> None:
        request_vars = [ident, ident + "_prefix"]
        super().__init__(ident=ident, request_vars=request_vars)
        self._what = what

    @override
    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        address_val = value.get(self.request_vars[0])
        if not address_val:
            return ""
        if value.get(self.request_vars[1]) == "yes":
            op = "~"
            address = "^" + livestatus.lqencode(address_val)
        else:
            op = "="
            address = livestatus.lqencode(address_val)
        if self._what == "primary":
            return f"Filter: host_address {op} {address}\n"
        varname = "ADDRESS_4" if self._what == "ipv4" else "ADDRESS_6"
        return f"Filter: host_custom_variables {op} {varname} {address}\n"


def ip_match_options() -> SitesOptions:
    return [("yes", _("Prefix match")), ("no", _("Exact match"))]


def address_family(family: str) -> FilterHeader:
    return "Filter: tags = address_family ip-v%s-only\n" % livestatus.lqencode(family)


def ip_address_family_options() -> SitesOptions:
    return [("4", _("IPv4")), ("6", _("IPv6")), ("both", _("Both"))]


def address_families(family: str) -> FilterHeader:
    v4_key_val_str = "ip-v4 ip-v4"
    v6_key_val_str = "ip-v6 ip-v6"
    match family:
        case "both":
            return lq_logic("Filter: tags =", [v4_key_val_str, v6_key_val_str], "Or")
        case "4":
            return f"Filter: tags = {v4_key_val_str}\n"
        case "4_only":
            return f"Filter: tags = {v4_key_val_str}\nFilter: tags != {v6_key_val_str}\n"
        case "6":
            return f"Filter: tags = {v6_key_val_str}\n"
        case "6_only":
            return f"Filter: tags = {v6_key_val_str}\nFilter: tags != {v4_key_val_str}\n"
        case _:
            raise ValueError()


def ip_address_families_options() -> SitesOptions:
    return [
        ("4", "v4"),
        ("6", "v6"),
        ("both", _("Both")),
        ("4_only", _("only v4")),
        ("6_only", _("only v6")),
        ("", _("(ignore)")),
    ]


class MultipleQuery(TextQuery):
    def selection(self, value: FilterHTTPVariables) -> list[str]:
        if folders := value.get(self.request_vars[0], "").strip():
            return folders.split("|")
        return []

    @override
    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        negate = self._negate_symbol(value)
        # not (A or B) => (not A) and (not B)
        joiner = "And" if negate else "Or"

        return lq_logic(f"Filter: {self.column} {negate}{self.op}", self.selection(value), joiner)


class AllLabelGroupsQuery(Query):
    def __init__(self, *, object_type: Literal["host", "service"]) -> None:
        self.object_type = object_type
        self.column = f"{object_type}_labels"
        # Request vars can be empty here. They are gathered dynamically within the
        # LabelGroupFilter class, value() method
        super().__init__(ident=f"{object_type}_labels", request_vars=[])

    @override
    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        return encode_label_groups_for_livestatus(self.column, self.parse_value(value))

    def parse_value(self, value: FilterHTTPVariables) -> LabelGroups:
        prefix: str = self.ident  # "[host|service]_labels"
        return parse_label_groups_from_http_vars(prefix, value)


class ABCTagsQuery(Query):
    column: str
    object_type: Literal["host", "service"]

    @override
    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        return encode_labels_for_livestatus(self.column, self.parse_value(value))

    def parse_value(self, value: FilterHTTPVariables) -> Labels:
        return parse_labels_value(value.get(self.request_vars[0], ""))


class TagsQuery(ABCTagsQuery):
    def __init__(
        self,
        *,
        object_type: Literal["host", "service"],
    ):
        self.object_type = object_type
        self.column = f"{object_type}_tags"

        self.count = 3
        self.var_prefix = "%s_tag" % object_type

        request_vars: list[str] = []
        for num in range(self.count):
            request_vars += [
                "%s_%d_grp" % (self.var_prefix, num),
                "%s_%d_op" % (self.var_prefix, num),
                "%s_%d_val" % (self.var_prefix, num),
            ]
        super().__init__(ident=f"{object_type}_tags", request_vars=request_vars)

    @override
    def parse_value(self, value: FilterHTTPVariables) -> Labels:
        # Do not restrict to a certain number, because we'd like to link to this
        # via an URL, e.g. from the virtual host tree snap-in
        num = 0
        while value.get("%s_%d_grp" % (self.var_prefix, num)):
            prefix = "%s_%d" % (self.var_prefix, num)
            num += 1

            op = value.get(prefix + "_op")
            tag_group = active_config.tags.get_tag_group(TagGroupID(value.get(prefix + "_grp", "")))

            if tag_group and op:
                tag = value.get(prefix + "_val", "")
                yield Label(tag_group.id, tag, negate=op != "is")


class AuxTagsQuery(ABCTagsQuery):
    def __init__(self, *, object_type: Literal["host"]) -> None:
        self.object_type = object_type
        self.column = f"{object_type}_tags"
        self.count = 3
        self.var_prefix = f"{object_type}_auxtags"

        request_vars = []
        for num in range(self.count):
            request_vars += [
                "%s_%d" % (self.var_prefix, num),
                "%s_%d_neg" % (self.var_prefix, num),
            ]

        super().__init__(ident=f"{object_type}_auxtags", request_vars=request_vars)

    @override
    def parse_value(self, value: FilterHTTPVariables) -> Labels:
        # Do not restrict to a certain number, because we'd like to link to this
        # via an URL, e.g. from the virtual host tree snap-in
        num = 0
        while (this_tag := value.get("%s_%d" % (self.var_prefix, num))) is not None:
            if this_tag:
                negate = bool(value.get("%s_%d_neg" % (self.var_prefix, num)))
                yield Label(this_tag, this_tag, negate)

            num += 1


def service_state_filter(prefix: str, value: FilterHTTPVariables) -> FilterHeader:
    if not any(value.values()):  # empty selection discard
        return ""

    headers = []
    for request_var, toggled in value.items():
        if toggled:
            continue

        if request_var.endswith("p"):
            headers.append("Filter: service_has_been_checked = 1\n")
        else:
            if prefix == "hd":
                column = "service_last_hard_state"
            else:
                column = "service_state"
            headers.append(
                "Filter: %s = %s\n"
                "Filter: service_has_been_checked = 1\n"
                "And: 2\nNegate:\n" % (column, request_var[-1])
            )

    return "".join(headers)


def host_state_filter(value: FilterHTTPVariables) -> FilterHeader:
    if not any(value.values()):  # empty selection discard
        return ""
    headers = []
    for request_var, toggled in value.items():
        if toggled:
            continue

        if request_var == "hstp":
            headers.append("Filter: host_has_been_checked = 1\n")

        else:
            headers.append(
                "Filter: host_state = %s\n"
                "Filter: host_has_been_checked = 1\n"
                "And: 2\nNegate:\n" % request_var[-1]
            )
    return "".join(headers)


def host_having_svc_problems_filter(value: FilterHTTPVariables) -> FilterHeader:
    conditions = [
        "host_num_services_%s > 0" % var
        for var in ["warn", "crit", "pending", "unknown"]
        if value.get("hosts_having_services_%s" % var)
    ]

    return lq_logic("Filter:", conditions, "Or")


def hostgroup_problems_filter(value: FilterHTTPVariables) -> FilterHeader:
    headers = []
    for svc_var in ["warn", "crit", "pending", "unknown"]:
        if value.get("hostgroups_having_services_%s" % svc_var):
            headers.append("num_services_%s > 0\n" % svc_var)

    for host_var in ["down", "unreach", "pending"]:
        if value.get("hostgroups_having_hosts_%s" % host_var):
            headers.append("num_hosts_%s > 0\n" % host_var)

    if value.get("hostgroups_show_unhandled_host"):
        headers.append("num_hosts_unhandled_problems > 0\n")

    if value.get("hostgroups_show_unhandled_svc"):
        headers.append("num_services_unhandled_problems > 0\n")

    return lq_logic("Filter:", headers, "Or")


def log_alerts_filter(value: FilterHTTPVariables) -> FilterHeader:
    if not any(value.values()):
        return "Limit: 0\n"  # no allowed state

    headers = []
    for request_var, toggled in value.items():
        if toggled:
            log_type = "HOST" if request_var[-2] == "h" else "SERVICE"
            state = request_var[-1]
            headers.append(
                lq_logic(
                    "Filter:",
                    [f"log_type ~ {log_type} .*", f"log_state = {state}"],
                    "And",
                )
            )

    return "".join(headers) + ("Or: %d\n" % len(headers))


def empty_hostgroup_filter(value: FilterHTTPVariables) -> FilterHeader:
    if any(value.values()):  # Selected to show empty
        return ""
    return "Filter: hostgroup_num_hosts > 0\n"


def options_toggled_filter(column: str, value: FilterHTTPVariables) -> FilterHeader:
    "When VALUE keys are the options, return filterheaders that equal column to option."

    def drop_column_prefix(var: str) -> str:
        if var.startswith(column + "_"):
            return var[len(column) + 1 :]
        return var

    selected = sorted(drop_column_prefix(name) for name, on in value.items() if on == "on")

    return lq_logic("Filter: %s =" % column, selected, "Or")


def svc_state_min_options(prefix: str) -> list[tuple[str, str]]:
    return [
        (prefix + "0", _("OK")),
        (prefix + "1", _("WARN")),
        (prefix + "2", _("CRIT")),
        (prefix + "3", _("UNKN")),
    ]


def svc_state_options(prefix: str) -> list[tuple[str, str]]:
    return svc_state_min_options(prefix + "st") + [(prefix + "stp", _("PEND"))]


def svc_problems_options(prefix: str) -> list[tuple[str, str]]:
    return [
        (prefix + "warn", _("WARN")),
        (prefix + "crit", _("CRIT")),
        (prefix + "pending", _("PEND")),
        (prefix + "unknown", _("UNKNOWN")),
    ]


def host_problems_options(prefix: str) -> SitesOptions:
    return [
        (prefix + "down", _("DOWN")),
        (prefix + "unreach", _("UNREACH")),
        (prefix + "pending", _("PEND")),
    ]


def host_state_options() -> list[tuple[str, str]]:
    return [
        ("hst0", _("UP")),
        ("hst1", _("DOWN")),
        ("hst2", _("UNREACH")),
        ("hstp", _("PEND")),
    ]


def discovery_state_options() -> list[tuple[str, str]]:
    return [
        ("discovery_state_ignored", _("Hidden")),
        ("discovery_state_vanished", _("Vanished")),
        ("discovery_state_unmonitored", _("New")),
    ]


def log_class_options() -> SitesOptions:
    # NOTE: We have to keep this table in sync with the enum LogEntry::Class on the C++ side.
    # INFO          0 // all messages not in any other class
    # ALERT         1 // alerts: the change service/host state
    # PROGRAM       2 // important programm events (restart, ...)
    # NOTIFICATION  3 // host/service notifications
    # PASSIVECHECK  4 // passive checks
    # COMMAND       5 // external commands
    # STATE         6 // initial or current states
    # ALERT HANDLERS 8

    return [
        ("logclass0", _("Informational")),
        ("logclass1", _("Alerts")),
        ("logclass2", _("Program")),
        ("logclass3", _("Notifications")),
        ("logclass4", _("Passive checks")),
        ("logclass5", _("Commands")),
        ("logclass6", _("States")),
        ("logclass8", _("Alert handlers")),
    ]


def discovery_state_filter_table(ident: str, context: VisualContext, rows: Rows) -> Rows:
    filter_options = context.get(ident, {})
    return [row for row in rows if filter_options.get("discovery_state_" + row["discovery_state"])]


def log_class_filter(value: FilterHTTPVariables) -> FilterHeader:
    if not any(value.values()):
        return "Limit: 0\n"  # no class allowed

    toggled = [request_var[-1] for request_var, value in value.items() if value == "on"]
    return lq_logic("Filter: class =", toggled, "Or")


def if_oper_status_filter_table(ident: str, context: VisualContext, rows: Rows) -> Rows:
    values = context.get(ident, {})

    def _add_row(row: Row) -> bool:
        # Apply filter if and only if a filter value is set
        if (oper_status := row.get("invinterface_oper_status")) is not None and (
            filter_key := "%s_%d" % (ident, oper_status)
        ) in values:
            return values[filter_key] == "on"
        return True

    return [row for row in rows if _add_row(row)]
