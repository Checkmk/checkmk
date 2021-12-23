#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Here are livestatus filters isolated out of the visuals GUI logic. They shall
# then later be replaced using the new query helpers.

import time
from typing import Callable, List, Literal, Optional, Tuple

import livestatus

import cmk.utils.version as cmk_version

import cmk.gui.inventory as inventory
import cmk.gui.sites as sites
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

    def __init__(
        self,
        *,
        ident: str,
        request_vars: List[str],
        filter_lq: Optional[Callable[..., FilterHeader]] = None,
        filter_rows: Optional[Callable[..., Rows]] = None,
    ):
        self.ident = ident
        self.request_vars = request_vars
        self.filter_lq = filter_lq or (lambda x: "")
        self.filter_rows = filter_rows or (lambda _ctx, rows: rows)

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        return self.filter_lq(value)

    def filter_table(self, context: VisualContext, rows: Rows) -> Rows:
        return self.filter_rows(context, rows)


class FilterMultipleOptions(Filter):
    def __init__(
        self,
        *,
        ident: str,
        options: Options,
        filter_lq: Optional[Callable[[FilterHTTPVariables], FilterHeader]] = None,
        filter_rows: Optional[Callable[..., Rows]] = None,
    ):
        # TODO: options helps with data validation but conflicts with the Filter job
        super().__init__(
            ident=ident,
            request_vars=[v[0] for v in options],
            filter_lq=filter_lq,
            filter_rows=filter_rows,
        )
        self.options = options


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


class FilterSingleOption(Filter):
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
        self.filter_rows: Callable[[str, VisualContext, Rows], Rows] = filter_rows or (
            lambda _s, _ctx, rows: rows
        )
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
        if selection == self.ignore:
            return rows
        return self.filter_rows(selection, context, rows)


class FilterTristate(FilterSingleOption):
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


MaybeIntBounds = Tuple[Optional[int], Optional[int]]


class FilterNumberRange(Filter):
    def __init__(self, *, ident: str, column: Optional[str] = None):
        super().__init__(ident=ident, request_vars=[ident + "_from", ident + "_until"])
        self.column = column or ident

    def extractor(self, value: FilterHTTPVariables) -> MaybeIntBounds:
        return (
            self.get_bound(self.ident + "_from", value),
            self.get_bound(self.ident + "_until", value),
        )

    @staticmethod
    def get_bound(var: str, value: FilterHTTPVariables) -> Optional[int]:
        try:
            return int(value.get(var, ""))
        except ValueError:
            return None

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        filtertext = ""
        for op, bound in zip((">=", "<="), self.extractor(value)):
            if bound is not None:
                filtertext += "Filter: %s %s %d\n" % (self.column, op, bound)
        return filtertext


class FilterTime(FilterNumberRange):
    def __init__(self, *, ident: str, column: Optional[str] = None):

        super().__init__(ident=ident, column=column)
        self.request_vars.extend([var + "_range" for var in self.request_vars])

    @staticmethod
    def get_bound(var: str, value: FilterHTTPVariables) -> Optional[int]:
        rangename = value.get(var + "_range")
        if rangename == "abs":
            try:
                return int(time.mktime(time.strptime(value[var], "%Y-%m-%d")))
            except Exception:
                user_errors.add(
                    MKUserError(var, _("Please enter the date in the format YYYY-MM-DD."))
                )
                return None

        if rangename == "unix":
            return int(value[var])
        if rangename is None:
            return None

        try:
            count = int(value[var])
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


class FilterCheckCommand(FilterText):
    def _filter(self, value: FilterHTTPVariables) -> FilterHeader:
        return "Filter: %s %s ^%s(!.*)?\n" % (
            self.column,
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


def service_state_filter(prefix: str, value: FilterHTTPVariables) -> FilterHeader:
    headers = []
    filter_is_used = any(value.values())
    for i in [0, 1, 2, 3]:
        check_result = bool(value.get(prefix + "st%d" % i))

        if filter_is_used and check_result is False:
            if prefix == "hd":
                column = "service_last_hard_state"
            else:
                column = "service_state"
            headers.append(
                "Filter: %s = %d\n"
                "Filter: service_has_been_checked = 1\n"
                "And: 2\nNegate:\n" % (column, i)
            )

    if filter_is_used and bool(value.get(prefix + "stp")) is False:
        headers.append("Filter: service_has_been_checked = 1\n")

    if len(headers) == 5:  # none allowed = all allowed (makes URL building easier)
        return ""
    return "".join(headers)


def host_state_filter(value: FilterHTTPVariables) -> FilterHeader:
    headers = []
    filter_is_used = any(value.values())
    for i in [0, 1, 2]:
        check_result = bool(value.get("hst%d" % i))

        if filter_is_used and check_result is False:
            headers.append(
                "Filter: host_state = %d\n"
                "Filter: host_has_been_checked = 1\n"
                "And: 2\nNegate:\n" % i
            )

    if filter_is_used and bool(value.get("hstp")) is False:
        headers.append("Filter: host_has_been_checked = 1\n")

    if len(headers) == 4:  # none allowed = all allowed (makes URL building easier)
        return ""
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


def empty_hostgroup_filter(value: FilterHTTPVariables) -> FilterHeader:
    if any(value.values()):  # Selected to show empty
        return ""
    return "Filter: hostgroup_num_hosts > 0\n"


def options_toggled_filter(column: str, value: FilterHTTPVariables) -> FilterHeader:
    "When VALUE keys are the options, return filterheaders that equal column to option."
    if all(value.values()):  # everything on, skip filter
        return ""

    def drop_column_prefix(var: str):
        if var.startswith(column + "_"):
            return var[len(column) + 1 :]
        return var

    selected = sorted(drop_column_prefix(name) for name, on in value.items() if on == "on")

    return lq_logic("Filter: %s =" % column, selected, "Or")


def svc_state_min_options(prefix: str):
    return [
        (prefix + "0", _("OK")),
        (prefix + "1", _("WARN")),
        (prefix + "2", _("CRIT")),
        (prefix + "3", _("UNKN")),
    ]


def svc_state_options(prefix: str) -> List[Tuple[str, str]]:
    return svc_state_min_options(prefix + "st") + [(prefix + "stp", _("PEND"))]


def svc_problems_options(prefix: str) -> List[Tuple[str, str]]:
    return [
        (prefix + "warn", _("WARN")),
        (prefix + "crit", _("CRIT")),
        (prefix + "pending", _("PEND")),
        (prefix + "unknown", _("UNKNOWN")),
    ]


def host_problems_options(prefix: str) -> Options:
    return [
        (prefix + "down", _("DOWN")),
        (prefix + "unreach", _("UNREACH")),
        (prefix + "pending", _("PEND")),
    ]


def host_state_options() -> List[Tuple[str, str]]:
    return [
        ("hst0", _("UP")),
        ("hst1", _("DOWN")),
        ("hst2", _("UNREACH")),
        ("hstp", _("PEND")),
    ]


def discovery_state_options() -> List[Tuple[str, str]]:
    return [
        ("discovery_state_ignored", _("Hidden")),
        ("discovery_state_vanished", _("Vanished")),
        ("discovery_state_unmonitored", _("New")),
    ]


def discovery_state_filter_table(ident: str, context: VisualContext, rows: Rows) -> Rows:
    filter_options = context.get(ident, {})
    return [row for row in rows if filter_options.get("discovery_state_" + row["discovery_state"])]


def cre_sites_options() -> Options:

    return sorted(
        [
            (sitename, sites.get_site_config(sitename)["alias"])
            for sitename, state in sites.states().items()
            if state["state"] == "online"
        ],
        key=lambda a: a[1].lower(),
    )


def sites_options() -> Options:
    if cmk_version.is_managed_edition():
        from cmk.gui.cme.plugins.visuals.managed import (  # pylint: disable=no-name-in-module
            filter_cme_choices,
        )

        return filter_cme_choices()
    return cre_sites_options()
