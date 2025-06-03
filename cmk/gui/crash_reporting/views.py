#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Iterable, Iterator, Mapping, Sequence
from typing import Any, Literal

import livestatus
from livestatus import MKLivestatusNotFoundError, OnlySites, Query, QuerySpecification

from cmk.gui.config import Config
from cmk.gui.data_source import (
    ABCDataSource,
    DataSourceLivestatus,
    query_livestatus,
    query_row,
    RowTable,
)
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.http import Request
from cmk.gui.http import request as active_request
from cmk.gui.i18n import _, _l, ungettext
from cmk.gui.logged_in import LoggedInUser
from cmk.gui.painter.v0 import Cell, Painter
from cmk.gui.painter_options import paint_age
from cmk.gui.permissions import Permission, permission_registry
from cmk.gui.type_defs import ColumnName, Row, Rows, SingleInfos, VisualContext
from cmk.gui.utils.html import HTML
from cmk.gui.utils.urls import makeuri_contextless
from cmk.gui.view_utils import CellSpec
from cmk.gui.views.command import (
    Command,
    CommandActionResult,
    CommandGroupVarious,
    PERMISSION_SECTION_ACTION,
)
from cmk.gui.views.sorter import cmp_simple_number, Sorter
from cmk.gui.visuals.filter import Filter

from .helpers import local_files_involved_in_crash


class DataSourceCrashReports(DataSourceLivestatus):
    @property
    def ident(self) -> str:
        return "crash_reports"

    @property
    def title(self) -> str:
        return _("Crash reports")

    @property
    def infos(self) -> SingleInfos:
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
    def query(
        self,
        datasource: ABCDataSource,
        cells: Sequence[Cell],
        columns: list[ColumnName],
        context: VisualContext,
        headers: str,
        only_sites: OnlySites,
        limit: int | None,
        all_active_filters: list[Filter],
    ) -> Rows | tuple[Rows, int]:
        return sorted(
            self.parse_rows(self.get_crash_report_rows(only_sites, filter_headers="")),
            key=lambda r: r["crash_time"],
        )

    def parse_rows(self, rows: Iterable[Row]) -> Iterable[Row]:
        for raw_row in rows:
            crash_info = raw_row.get("crash_info")
            if crash_info is None:
                continue  # skip broken crash reports

            try:
                crash_info_raw = json.loads(crash_info)
            except json.JSONDecodeError:
                continue  # skip broken crash infos like b'' or b'\n'

            yield {
                "site": raw_row["site"],
                "crash_id": raw_row["crash_id"],
                "crash_type": raw_row["crash_type"],
                "crash_time": crash_info_raw["time"],
                "crash_version": crash_info_raw["version"],
                "crash_exc_type": crash_info_raw["exc_type"],
                "crash_exc_value": crash_info_raw["exc_value"],
                "crash_exc_traceback": crash_info_raw["exc_traceback"],
            }

    def get_crash_report_rows(
        self, only_sites: OnlySites, filter_headers: str
    ) -> Iterator[dict[str, str]]:
        # First fetch the information that is needed to query for the dynamic columns (crash_info,
        # ...)
        for crash_info in self._get_crash_report_info(only_sites, filter_headers):
            file_path = "/".join([crash_info["crash_type"], crash_info["crash_id"]])

            headers = ["site", "crash_info"]
            columns = ["file:crash_info:%s/crash.info" % livestatus.lqencode(file_path)]

            if crash_info["crash_type"] in ("check", "section"):
                headers += ["agent_output", "snmp_info"]
                columns += [
                    "file:agent_output:%s/agent_output" % livestatus.lqencode(file_path),
                    "file:snmp_info:%s/snmp_info" % livestatus.lqencode(file_path),
                ]

            try:
                raw_row = query_row(
                    Query(
                        QuerySpecification(
                            table="crashreports",
                            columns=columns,
                            headers="Filter: id = %s" % livestatus.lqencode(crash_info["crash_id"]),
                        )
                    ),
                    only_sites=only_sites,
                    limit=None,
                    auth_domain="read",
                )
            except MKLivestatusNotFoundError:
                continue

            crash_info.update(dict(zip(headers, raw_row)))
            yield crash_info

    def _get_crash_report_info(
        self, only_sites: OnlySites, filter_headers: str | None = None
    ) -> Iterator[dict[str, str]]:
        rows = query_livestatus(
            Query(
                QuerySpecification(
                    table="crashreports",
                    columns=["id", "component"],
                    headers=filter_headers or "",
                )
            ),
            only_sites=only_sites,
            limit=None,
            auth_domain="read",
        )

        columns = ["site", "crash_id", "crash_type"]
        return (dict(zip(columns, r)) for r in rows)


class PainterCrashIdent(Painter):
    @property
    def ident(self) -> str:
        return "crash_ident"

    def title(self, cell: Cell) -> str:
        return _("Crash Ident")

    def short_title(self, cell: Cell) -> str:
        return _("ID")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["crash_id"]

    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        url = makeuri_contextless(
            self.request,
            [
                ("crash_id", row["crash_id"]),
                ("site", row["site"]),
            ],
            filename="crash.py",
        )
        return None, HTMLWriter.render_a(row["crash_id"], href=url)


class PainterCrashType(Painter):
    @property
    def ident(self) -> str:
        return "crash_type"

    def title(self, cell: Cell) -> str:
        return _("Crash type")

    def short_title(self, cell: Cell) -> str:
        return _("Type")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["crash_type"]

    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        return None, row["crash_type"]


class PainterCrashSource(Painter):
    @property
    def ident(self) -> str:
        return "crash_source"

    def title(self, cell: Cell) -> str:
        return _("Crash source")

    def short_title(self, cell: Cell) -> str:
        return _("Source")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["crash_exc_traceback"]

    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        return (
            None,
            (
                _("Extension")
                if local_files_involved_in_crash(row["crash_exc_traceback"])
                else _("Built-in")
            ),
        )


class PainterCrashTime(Painter):
    @property
    def ident(self) -> str:
        return "crash_time"

    def title(self, cell: Cell) -> str:
        return _("Crash Time")

    def short_title(self, cell: Cell) -> str:
        return _("Time")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["crash_time"]

    @property
    def painter_options(self):
        return ["ts_format", "ts_date"]

    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        return paint_age(
            row["crash_time"],
            has_been_checked=True,
            bold_if_younger_than=3600,
            request=self.request,
            painter_options=self._painter_options,
        )


class PainterCrashVersion(Painter):
    @property
    def ident(self) -> str:
        return "crash_version"

    def title(self, cell: Cell) -> str:
        return _("Crash Checkmk Version")

    def short_title(self, cell: Cell) -> str:
        return _("Version")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["crash_version"]

    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        return None, row["crash_version"]


class PainterCrashException(Painter):
    @property
    def ident(self) -> str:
        return "crash_exception"

    def title(self, cell: Cell) -> str:
        return _("Crash Exception")

    def short_title(self, cell: Cell) -> str:
        return _("Exc.")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["crash_exc_type", "crash_exc_value"]

    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        return None, "{}: {}".format(row["crash_exc_type"], row["crash_exc_value"])


def _sort_crash_time(
    r1: Row,
    r2: Row,
    *,
    parameters: Mapping[str, Any] | None,
    config: Config,
    request: Request,
) -> int:
    return cmp_simple_number("crash_time", r1, r2)


SorterCrashTime = Sorter(
    ident="crash_time",
    title=_l("Crash time"),
    columns=["crash_time"],
    sort_function=_sort_crash_time,
)


PermissionActionDeleteCrashReport = permission_registry.register(
    Permission(
        section=PERMISSION_SECTION_ACTION,
        name="delete_crash_report",
        title=_l("Delete crash reports"),
        description=_l("Delete crash reports created by Checkmk"),
        defaults=["admin"],
    )
)


def command_delete_crash_report_affected(
    len_action_rows: int, cmdtag: Literal["HOST", "SVC"]
) -> HTML:
    return HTML.without_escaping(
        _("Affected %s: %s")
        % (
            ungettext(
                "crash report",
                "crash reports",
                len_action_rows,
            ),
            len_action_rows,
        )
    )


def command_delete_crash_report_render(what: str) -> None:
    html.open_div(class_="group")
    html.button("_delete_crash_reports", _("Delete"), cssclass="hot")
    html.button("_cancel", _("Cancel"))
    html.close_div()


def command_delete_crash_report_action(
    command: Command,
    cmdtag: Literal["HOST", "SVC"],
    spec: str,
    row: dict,
    row_index: int,
    action_rows: Rows,
) -> CommandActionResult:
    if active_request.has_var("_delete_crash_reports"):
        commands = [("DEL_CRASH_REPORT;%s" % row["crash_id"])]
        return commands, command.confirm_dialog_options(cmdtag, row, action_rows)
    return None


CommandDeleteCrashReports = Command(
    ident="delete_crash_reports",
    title=_l("Delete crash reports"),
    confirm_title=_l("Delete crash reports?"),
    confirm_button=_l("Delete"),
    permission=PermissionActionDeleteCrashReport,
    group=CommandGroupVarious,
    tables=["crash"],
    render=command_delete_crash_report_render,
    action=command_delete_crash_report_action,
    affected_output_cb=command_delete_crash_report_affected,
)
