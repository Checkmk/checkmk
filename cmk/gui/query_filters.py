#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Here are livestatus filters isolated out of the visuals GUI logic. They shall
# then later be replaced using the new query helpers.

import time
from typing import Callable, List, Literal, Optional, Tuple, Union

import livestatus

import cmk.gui.inventory as inventory
from cmk.gui.exceptions import MKUserError
from cmk.gui.globals import config, user, user_errors
from cmk.gui.i18n import _
from cmk.gui.type_defs import FilterHeader, FilterHTTPVariables, Rows, VisualContext

Options = List[Tuple[str, str]]


def lq_logic(filter_condition: str, values: List[str], join: str) -> str:
    """JOIN with (Or, And) FILTER_CONDITION the VALUES for a livestatus query"""
    conditions = "".join("%s %s\n" % (filter_condition, livestatus.lqencode(x)) for x in values)
    connective = "%s: %d\n" % (join, len(values)) if len(values) > 1 else ""
    return conditions + connective


class Filter:
    "This is the Null filter and default class as it does nothing."

    def __init__(self, *, ident: str, request_vars: List[str]):
        self.ident = ident
        self.request_vars = request_vars

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        return ""

    def filter_table(self, context: VisualContext, rows: Rows) -> Rows:
        return rows


### Tri State filter
def default_tri_state_options() -> Options:
    return [("1", _("yes")), ("0", _("no")), ("-1", _("(ignore)"))]


def tri_state_type_options() -> Options:
    return [
        ("0", _("SOFT")),
        ("1", _("HARD")),
        ("-1", _("(ignore)")),
    ]


def tri_state_log_notifications_options() -> Options:
    return [
        ("1", _("Show just preliminary notifications")),
        ("0", _("Show just end-user-notifications")),
        ("-1", _("Show all phases of notifications")),
    ]


class FilterOption(Filter):
    def __init__(
        self,
        *,
        ident: str,
        options: Options,
        filter_code: Callable[[str], FilterHeader],
        filter_rows: Optional[Callable[[str, VisualContext, Rows], Rows]] = None,
    ):
        super().__init__(ident=ident, request_vars=[ident])
        # TODO: options helps with data validation but conflicts with the Filter job
        self.options = options
        self.filter_code = filter_code
        self.filter_rows = filter_rows
        self.ignore = self.options[-1][0]

    def selection_value(self, value: FilterHTTPVariables) -> str:
        selection = value.get(self.request_vars[0], "")
        if selection in [x for (x, _) in self.options]:
            return selection
        return self.ignore

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        selection = self.selection_value(value)
        if selection == self.ignore:
            return ""
        return self.filter_code(selection)

    def filter_table(self, context: VisualContext, rows: Rows) -> Rows:
        value = context.get(self.ident, {})
        selection = self.selection_value(value)
        if selection == self.ignore or self.filter_rows is None:
            return rows
        return self.filter_rows(selection, context, rows)


class FilterTristate(FilterOption):
    def __init__(
        self,
        *,
        ident,
        filter_code: Callable[[bool], FilterHeader],
        filter_rows: Optional[Callable[[bool, VisualContext, Rows], Rows]] = None,
        options=None,
    ):
        super().__init__(
            ident=ident,
            filter_code=lambda pick: filter_code(pick == "1"),
            filter_rows=(
                lambda pick, ctx, rows: filter_rows(pick == "1", ctx, rows)
                if filter_rows is not None
                else rows
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
        return "Filter: %s_staleness %s %0.2f\n" % (
            obj,
            operator,
            config.staleness_threshold,
        )

    return toggler


def column_flag(column: str) -> Callable[[bool], FilterHeader]:
    return lambda positive: f"Filter: {column} {'!=' if positive else '='} 0\n"


def log_notification_phase(column: str) -> Callable[[bool], FilterHeader]:
    def filterheader(positive: bool) -> FilterHeader:
        # Note: this filter also has to work for entries that are no notification.
        # In that case the filter is passive and lets everything through
        if positive:
            return "Filter: %s = check-mk-notify\nFilter: %s =\nOr: 2\n" % (
                column,
                column,
            )
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
                filters += "Filter: host_name %s %s\n" % (eq, livestatus.lqencode(star))
                count += 1
        else:
            for star in stars:
                if ";" not in star:
                    continue
                h, s = star.split(";")
                filters += "Filter: host_name %s %s\n" % (eq, livestatus.lqencode(h))
                filters += "Filter: service_description %s %s\n" % (eq, livestatus.lqencode(s))
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


## Filter tables
def inside_inventory(invpath: str) -> Callable[[bool, VisualContext, Rows], Rows]:
    def filter_rows(on: bool, context: VisualContext, rows: Rows) -> Rows:
        return [
            row
            for row in rows
            if inventory.get_inventory_attribute(row["host_inventory"], invpath) is on
        ]

    return filter_rows


def has_inventory(on: bool, context: VisualContext, rows: Rows) -> Rows:
    if on:
        return [row for row in rows if row["host_inventory"]]
    return [row for row in rows if not row["host_inventory"]]


### Filter Time
def time_filter_options() -> Options:
    ranges = [(86400, _("days")), (3600, _("hours")), (60, _("min")), (1, _("sec"))]
    choices = [(str(sec), title + " " + _("ago")) for sec, title in ranges]
    choices += [("abs", _("Date (YYYY-MM-DD)")), ("unix", _("UNIX timestamp"))]
    return choices


class FilterTime(Filter):
    def __init__(
        self,
        *,
        ident: str,
        column: str,
    ):
        varnames = [
            ident + "_from",
            ident + "_from_range",
            ident + "_until",
            ident + "_until_range",
        ]

        super().__init__(ident=ident, request_vars=varnames)
        self.column = column

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        fromsecs, untilsecs = self.get_time_range(value)
        filtertext = ""
        if fromsecs is not None:
            filtertext += "Filter: %s >= %d\n" % (self.column, fromsecs)
        if untilsecs is not None:
            filtertext += "Filter: %s <= %d\n" % (self.column, untilsecs)
        return filtertext

    # Extract timerange user has selected from HTML variables
    def get_time_range(
        self, value: FilterHTTPVariables
    ) -> Tuple[Union[None, int, float], Union[None, int, float]]:
        return self._get_time_range_of(value, "from"), self._get_time_range_of(value, "until")

    def _get_time_range_of(self, value: FilterHTTPVariables, what: str) -> Union[None, int, float]:
        varprefix = self.ident + "_" + what

        rangename = value.get(varprefix + "_range")
        if rangename == "abs":
            try:
                return time.mktime(time.strptime(value[varprefix], "%Y-%m-%d"))
            except Exception:
                user_errors.add(
                    MKUserError(varprefix, _("Please enter the date in the format YYYY-MM-DD."))
                )
                return None

        if rangename == "unix":
            return int(value[varprefix])
        if rangename is None:
            return None

        try:
            count = int(value[varprefix])
            secs = count * int(rangename)
            return int(time.time()) - secs
        except Exception:
            return None


### TextFilter
class FilterText(Filter):
    def __init__(
        self,
        *,
        ident: str,
        op: str,
        negateable: bool = False,
        request_var: Optional[str] = None,
        column: Optional[str] = None,
    ):

        request_vars = [request_var or ident]
        if negateable:
            request_vars.append("neg_" + (request_var or ident))

        super().__init__(ident=ident, request_vars=request_vars)
        self.op = op
        self.column = column or ident
        self.negateable = negateable
        self.link_columns = [self.column]

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        if value.get(self.request_vars[0]):
            return self._filter(value)
        return ""

    def _negate_symbol(self, value: FilterHTTPVariables) -> str:
        return "!" if self.negateable and value.get(self.request_vars[1]) else ""

    def _filter(self, value: FilterHTTPVariables) -> FilterHeader:
        return "Filter: %s %s%s %s\n" % (
            self.column,
            self._negate_symbol(value),
            self.op,
            livestatus.lqencode(value[self.request_vars[0]]),
        )


class FilterHostnameOrAlias(FilterText):
    def __init__(self):
        super().__init__(ident="hostnameoralias", column="host_name", op="~~", negateable=False)
        self.link_columns = ["host_alias", "host_name"]

    def _filter(self, value: FilterHTTPVariables) -> FilterHeader:
        host = livestatus.lqencode(value[self.request_vars[0]])

        return lq_logic("Filter:", [f"host_name {self.op} {host}", f"alias {self.op} {host}"], "Or")


class FilterOptEventEffectiveContactgroup(FilterText):
    def __init__(self):
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


### IPAddress
class FilterIPAddress(Filter):
    def __init__(self, *, ident: str, what: str):
        request_vars = [ident, ident + "_prefix"]
        super().__init__(ident=ident, request_vars=request_vars)
        self._what = what

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
            return "Filter: host_address %s %s\n" % (op, address)
        varname = "ADDRESS_4" if self._what == "ipv4" else "ADDRESS_6"
        return "Filter: host_custom_variables %s %s %s\n" % (op, varname, address)


def ip_match_options() -> Options:
    return [("yes", _("Prefix match")), ("no", _("Exact match"))]


def address_family(family: str) -> FilterHeader:
    return "Filter: tags = address_family ip-v%s-only\n" % livestatus.lqencode(family)


def ip_address_family_options() -> Options:
    return [("4", _("IPv4")), ("6", _("IPv6")), ("both", _("Both"))]


def address_families(family: str) -> FilterHeader:
    if family == "both":
        return lq_logic("Filter: tags =", ["ip-v4 ip-v4", "ip-v6 ip-v6"], "Or")

    if family[0] == "4":
        tag = livestatus.lqencode("ip-v4")
    elif family[0] == "6":
        tag = livestatus.lqencode("ip-v6")
    filt = "Filter: tags = %s %s\n" % (tag, tag)

    if family.endswith("_only"):
        if family[0] == "4":
            tag = livestatus.lqencode("ip-v6")
        elif family[0] == "6":
            tag = livestatus.lqencode("ip-v4")
        filt += "Filter: tags != %s %s\n" % (tag, tag)

    return filt


def ip_address_families_options() -> Options:
    return [
        ("4", "v4"),
        ("6", "v6"),
        ("both", _("Both")),
        ("4_only", _("only v4")),
        ("6_only", _("only v6")),
        ("", _("(ignore)")),
    ]


### Multipick
class FilterMultiple(FilterText):
    def selection(self, value: FilterHTTPVariables) -> List[str]:
        if folders := value.get(self.request_vars[0], "").strip():
            return folders.split("|")
        return []

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        negate = self._negate_symbol(value)
        # not (A or B) => (not A) and (not B)
        joiner = "And" if negate else "Or"

        return lq_logic(f"Filter: {self.column} {negate}{self.op}", self.selection(value), joiner)
