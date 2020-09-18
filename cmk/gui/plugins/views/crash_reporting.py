#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from typing import Dict, Optional, List
from six import ensure_str

import livestatus

import cmk.gui.config as config
import cmk.gui.sites as sites
from cmk.gui.i18n import _, _l
from cmk.gui.globals import html
from cmk.gui.escaping import escape_text

from cmk.gui.plugins.views import (
    data_source_registry,
    DataSourceLivestatus,
    RowTable,
)

from cmk.gui.plugins.views import (
    painter_registry,
    Painter,
    paint_age,
    sorter_registry,
    Sorter,
    cmp_simple_number,
)

from cmk.gui.permissions import (
    permission_registry,
    Permission,
)

from cmk.gui.plugins.views.commands import PermissionSectionAction
from cmk.gui.plugins.views import (
    command_registry,
    Command,
)


@data_source_registry.register
class DataSourceCrashReports(DataSourceLivestatus):
    @property
    def ident(self):
        return "crash_reports"

    @property
    def title(self):
        return _("Crash reports")

    @property
    def infos(self):
        return ["crash"]

    @property
    def keys(self):
        return ["crash_id"]

    @property
    def id_keys(self):
        return ["crash_id"]

    @property
    def table(self):
        return CrashReportsRowTable()


class CrashReportsRowTable(RowTable):
    # TODO: Handle headers / all_active_filters, limit, ...
    def query(self, view, columns, headers, only_sites, limit, all_active_filters):
        rows = []
        for raw_row in self.get_crash_report_rows(only_sites, filter_headers=""):
            if raw_row["crash_info"] is None:
                continue  # skip broken crash reports

            crash_info_raw = json.loads(raw_row["crash_info"])
            rows.append({
                "site": raw_row["site"],
                "crash_id": raw_row["crash_id"],
                "crash_type": raw_row["crash_type"],
                "crash_time": crash_info_raw["time"],
                "crash_version": crash_info_raw["version"],
                "crash_exc_type": crash_info_raw["exc_type"],
                "crash_exc_value": crash_info_raw["exc_value"],
                "crash_exc_traceback": crash_info_raw["exc_traceback"],
            })
        return sorted(rows, key=lambda r: r["crash_time"])

    def get_crash_report_rows(self, only_sites: Optional[List[config.SiteId]],
                              filter_headers: str) -> List[Dict[str, str]]:

        # First fetch the information that is needed to query for the dynamic columns (crash_info,
        # ...)
        crash_infos = self._get_crash_report_info(only_sites, filter_headers)
        if not crash_infos:
            return []

        rows = []
        for crash_info in crash_infos:
            file_path = "/".join([crash_info["crash_type"], crash_info["crash_id"]])

            headers = ["crash_info"]
            columns = ["file:crash_info:%s/crash.info" % livestatus.lqencode(file_path)]

            if crash_info["crash_type"] == "check":
                headers += ["agent_output", "snmp_info"]
                columns += [
                    "file:agent_output:%s/agent_output" % livestatus.lqencode(file_path),
                    "file:snmp_info:%s/snmp_info" % livestatus.lqencode(file_path),
                ]

            try:
                sites.live().set_prepend_site(False)
                sites.live().set_only_sites([config.SiteId(ensure_str(crash_info["site"]))])

                raw_row = sites.live().query_row(
                    "GET crashreports\n"
                    "Columns: %s\n"
                    "Filter: id = %s" %
                    (" ".join(columns), livestatus.lqencode(crash_info["crash_id"])))
            finally:
                sites.live().set_only_sites(None)
                sites.live().set_prepend_site(False)

            crash_info.update(dict(zip(headers, raw_row)))
            rows.append(crash_info)

        return rows

    def _get_crash_report_info(self,
                               only_sites: Optional[List[config.SiteId]],
                               filter_headers: Optional[str] = None) -> List[Dict[str, str]]:
        try:
            sites.live().set_prepend_site(True)
            sites.live().set_only_sites(only_sites)
            rows = sites.live().query("GET crashreports\nColumns: id component\n%s" %
                                      (filter_headers or ""))
        finally:
            sites.live().set_only_sites(None)
            sites.live().set_prepend_site(False)

        columns = ["site", "crash_id", "crash_type"]
        return [dict(zip(columns, r)) for r in rows]


@painter_registry.register
class PainterCrashIdent(Painter):
    @property
    def ident(self):
        return "crash_ident"

    def title(self, cell):
        return _("Crash Ident")

    def short_title(self, cell):
        return _("ID")

    @property
    def columns(self):
        return ["crash_id"]

    def render(self, row, cell):
        url = html.makeuri_contextless(
            [
                ("crash_id", row["crash_id"]),
                ("site", row["site"]),
            ],
            filename="crash.py",
        )
        return (None, html.render_a(row["crash_id"], href=url))


@painter_registry.register
class PainterCrashType(Painter):
    @property
    def ident(self):
        return "crash_type"

    def title(self, cell):
        return _("Crash Type")

    def short_title(self, cell):
        return _("Type")

    @property
    def columns(self):
        return ["crash_type"]

    def render(self, row, cell):
        return (None, escape_text(row["crash_type"]))


@painter_registry.register
class PainterCrashTime(Painter):
    @property
    def ident(self):
        return "crash_time"

    def title(self, cell):
        return _("Crash Time")

    def short_title(self, cell):
        return _("Time")

    @property
    def columns(self):
        return ["crash_time"]

    @property
    def painter_options(self):
        return ['ts_format', 'ts_date']

    def render(self, row, cell):
        return paint_age(row["crash_time"], has_been_checked=True, bold_if_younger_than=3600)


@painter_registry.register
class PainterCrashVersion(Painter):
    @property
    def ident(self):
        return "crash_version"

    def title(self, cell):
        return _("Crash Checkmk Version")

    def short_title(self, cell):
        return _("Version")

    @property
    def columns(self):
        return ["crash_version"]

    def render(self, row, cell):
        return (None, escape_text(row["crash_version"]))


@painter_registry.register
class PainterCrashException(Painter):
    @property
    def ident(self):
        return "crash_exception"

    def title(self, cell):
        return _("Crash Exception")

    def short_title(self, cell):
        return _("Exc.")

    @property
    def columns(self):
        return ["crash_exc_type", "crash_exc_value"]

    def render(self, row, cell):
        return (None, "%s: %s" %
                (escape_text(row["crash_exc_type"]), escape_text(row["crash_exc_value"])))


@sorter_registry.register
class SorterCrashTime(Sorter):
    @property
    def ident(self):
        return "crash_time"

    @property
    def title(self):
        return _("Crash time")

    @property
    def columns(self):
        return ['crash_time']

    def cmp(self, r1, r2):
        return cmp_simple_number("crash_time", r1, r2)


PermissionActionDeleteCrashReport = permission_registry.register(
    Permission(
        section=PermissionSectionAction,
        name="delete_crash_report",
        title=_l("Delete crash reports"),
        description=_l("Delete crash reports created by Checkmk"),
        defaults=["admin"],
    ))


@command_registry.register
class CommandDeleteCrashReports(Command):
    @property
    def ident(self):
        return "delete_crash_reports"

    @property
    def title(self):
        return _("Delete crash reports")

    @property
    def permission(self):
        return PermissionActionDeleteCrashReport

    @property
    def tables(self):
        return ["crash"]

    def render(self, what):
        html.button("_delete_crash_reports", _("Delete"))

    def action(self, cmdtag, spec, row, row_index, num_rows):
        if html.request.has_var("_delete_crash_reports"):
            commands = [("DEL_CRASH_REPORT;%s" % row["crash_id"])]
            return commands, _("remove")
