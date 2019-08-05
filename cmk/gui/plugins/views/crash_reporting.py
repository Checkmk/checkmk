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

import cmk.utils.paths
import cmk.utils.crash_reporting

import cmk.gui.config as config
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
    def query(self, view, columns, headers, only_sites, limit, all_active_filters):
        rows = []
        for raw_row in self._crash_report_rows_from_local_site():
            crash_info_raw = json.loads(raw_row["crash_info"])
            rows.append({
                "site": raw_row["site"],
                "crash_id": raw_row["crash_id"],
                "crash_time": crash_info_raw["time"],
                "crash_type": crash_info_raw["crash_type"],
                "crash_version": crash_info_raw["version"],
                "crash_exc_type": crash_info_raw["exc_type"],
                "crash_exc_value": crash_info_raw["exc_value"],
                "crash_exc_traceback": crash_info_raw["exc_traceback"],
            })
        return rows

    # Simulate the crash reports as they will be reported via livestatus
    # TODO: Drop this once the livestatus table is ready
    def _crash_report_rows_from_local_site(self):
        raw_rows = []
        store = cmk.utils.crash_reporting.CrashReportStore()
        for crash_dir in cmk.utils.paths.crash_dir.glob("*/*"):  # pylint: disable=no-member
            serialized_crash = store.load_serialized_from_directory(crash_dir)

            raw_row = {
                "site": config.omd_site(),
                "crash_id": crash_dir.name,
            }

            for key, value in serialized_crash.iteritems():
                raw_row[key] = json.dumps(value)

            raw_rows.append(raw_row)
        return sorted(raw_rows, key=lambda r: r["crash_id"])


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
