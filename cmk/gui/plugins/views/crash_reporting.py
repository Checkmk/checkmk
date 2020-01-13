#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import json
from typing import Dict, Text, Optional, List  # pylint: disable=unused-import
import livestatus

import cmk.gui.config as config
import cmk.gui.sites as sites
from cmk.gui.i18n import _
from cmk.gui.globals import html

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

    def get_crash_report_rows(self, only_sites, filter_headers):
        # type: (Optional[List[config.SiteId]], Text) -> List[Dict[Text, Text]]

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
                sites.live().set_only_sites([config.SiteId(bytes(crash_info["site"]))])

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

    def _get_crash_report_info(self, only_sites, filter_headers=None):
        # type: (Optional[List[config.SiteId]], Optional[Text]) -> List[Dict[Text, Text]]
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

    @property
    def title(self):
        return _("Crash Ident")

    @property
    def short_title(self):
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

    @property
    def title(self):
        return _("Crash Type")

    @property
    def short_title(self):
        return _("Type")

    @property
    def columns(self):
        return ["crash_type"]

    def render(self, row, cell):
        return (None, html.escaper.escape_text(row["crash_type"]))


@painter_registry.register
class PainterCrashTime(Painter):
    @property
    def ident(self):
        return "crash_time"

    @property
    def title(self):
        return _("Crash Time")

    @property
    def short_title(self):
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

    @property
    def title(self):
        return _("Crash Checkmk Version")

    @property
    def short_title(self):
        return _("Version")

    @property
    def columns(self):
        return ["crash_version"]

    def render(self, row, cell):
        return (None, html.escaper.escape_text(row["crash_version"]))


@painter_registry.register
class PainterCrashException(Painter):
    @property
    def ident(self):
        return "crash_exception"

    @property
    def title(self):
        return _("Crash Exception")

    @property
    def short_title(self):
        return _("Exc.")

    @property
    def columns(self):
        return ["crash_exc_type", "crash_exc_value"]

    def render(self, row, cell):
        return (None, "%s: %s" % \
            (html.escaper.escape_text(row["crash_exc_type"]), html.escaper.escape_text(row["crash_exc_value"])))


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


@permission_registry.register
class PermissionActionDeleteCrashReport(Permission):
    @property
    def section(self):
        return PermissionSectionAction

    @property
    def permission_name(self):
        return "delete_crash_report"

    @property
    def title(self):
        return _("Delete crash reports")

    @property
    def description(self):
        return _("Delete crash reports created by Checkmk")

    @property
    def defaults(self):
        return ["admin"]


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
