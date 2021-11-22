#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Here are livestatus filters isolated out of the visuals GUI logic. They shall
# then later be replaced using the new query helpers.

from typing import Callable, List, Literal, Optional, Tuple

import livestatus

import cmk.gui.inventory as inventory
from cmk.gui.globals import config, user
from cmk.gui.i18n import _
from cmk.gui.type_defs import FilterHeader, FilterHTTPVariables, Rows, VisualContext

Options = List[Tuple[str, str]]


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
        ("-1", _("Show all phases of notifications")),
        ("1", _("Show just preliminary notifications")),
        ("0", _("Show just end-user-notifications")),
    ]


class FilterTristate:
    def __init__(
        self,
        *,
        ident: str,
        filter_code: Callable[[bool], FilterHeader],
        filter_rows: Optional[Callable[[bool, VisualContext, Rows], Rows]] = None,
        options: Optional[Options] = None,
        default: Literal[-1, 0, 1] = -1,
    ):
        self.ident = ident
        self.filter_code = filter_code
        self.filter_rows = filter_rows
        self.varname = "is_" + ident
        self.deflt = default
        self.options = options or default_tri_state_options()

    def tristate_value(self, value: FilterHTTPVariables) -> int:
        try:
            return int(value.get(self.varname, ""))
        except ValueError:
            return self.deflt

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        current = self.tristate_value(value)
        if current == -1:  # ignore
            return ""
        return self.filter_code(current == 1)

    def filter_table(self, context: VisualContext, rows: Rows) -> Rows:
        value = context.get(self.ident, {})
        tri = self.tristate_value(value)
        if tri == -1 or self.filter_rows is None:
            return rows
        return self.filter_rows(tri == 1, context, rows)


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
