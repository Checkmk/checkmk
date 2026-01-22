#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

import json
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from typing import Any, Literal

import livestatus
from livestatus import MKLivestatusNotFoundError, OnlySites, Query, QuerySpecification

from cmk.gui import query_filters
from cmk.gui.config import Config
from cmk.gui.data_source import (
    ABCDataSource,
    DataSourceLivestatus,
    query_livestatus,
    query_row,
    RowTableLivestatus,
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
from cmk.gui.views.sorter import (
    cmp_insensitive_string,
    cmp_simple_number,
    cmp_simple_string,
    Sorter,
)
from cmk.gui.visuals import SiteFilter
from cmk.gui.visuals._site_filters import default_site_filter_heading_info
from cmk.gui.visuals.filter import Filter, FilterOption, FilterTime, InputTextFilter
from cmk.livestatus_client import DeleteCrashReport

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
    def keys(self) -> list[str]:
        return ["crash_id"]

    @property
    def id_keys(self) -> list[str]:
        return ["crash_id"]

    @property
    def table(self) -> RowTableLivestatus:
        return CrashReportsRowTable()


class CrashReportsRowTable(RowTableLivestatus):
    def __init__(self) -> None:
        super().__init__("crashreports")

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

            row = {
                "site": raw_row["site"],
                "crash_id": raw_row["crash_id"],
                "crash_type": raw_row["crash_type"],
                "crash_time": crash_info_raw["time"],
                "crash_version": crash_info_raw["version"],
                "crash_exc_type": crash_info_raw["exc_type"],
                "crash_exc_value": crash_info_raw["exc_value"],
                "crash_exc_traceback": crash_info_raw["exc_traceback"],
            }
            details = crash_info_raw.get("details")
            if not isinstance(details, dict):
                yield row
                continue
            yield {
                **row,
                **({"crash_host": h} if (h := details.get("host")) else {}),
                **({"crash_item": i} if (i := details.get("item")) else {}),
                **({"crash_check_type": c} if (c := details.get("check_type")) else {}),
                **({"crash_service_name": s} if (s := details.get("description")) else {}),
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
        return _("Crash ident")

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
        return _("Crash time")

    def short_title(self, cell: Cell) -> str:
        return _("Time")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["crash_time"]

    @property
    def painter_options(self) -> list[str]:
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
        return _("Crash Checkmk version")

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
        return _("Crash exception")

    def short_title(self, cell: Cell) -> str:
        return _("Exc.")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["crash_exc_type", "crash_exc_value"]

    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        return (
            None,
            "{}: {}".format(row["crash_exc_type"], row["crash_exc_value"])
            if user.may("general.see_crash_reports")
            else _("Insufficient permissions to view exception details."),
        )


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
        commands = DeleteCrashReport(row["crash_id"])
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


class PainterCrashHost(Painter):
    @property
    def ident(self) -> str:
        return "crash_host"

    def title(self, cell: Cell) -> str:
        return _("Crash host")

    def short_title(self, cell: Cell) -> str:
        return _("Host")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["crash_host"]

    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        if not row.get("crash_host"):
            return None, ""

        url = makeuri_contextless(
            self.request,
            [
                ("host", row["crash_host"]),
                ("site", row["site"]),
                ("view_name", "host"),
            ],
            filename="view.py",
        )
        return None, HTMLWriter.render_a(row["crash_host"], href=url)


class PainterCrashItem(Painter):
    @property
    def ident(self) -> str:
        return "crash_item"

    def title(self, cell: Cell) -> str:
        return _("Crash service item")

    def short_title(self, cell: Cell) -> str:
        return _("Item")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["crash_item"]

    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        return None, row.get("crash_item", "")


class PainterCrashCheckType(Painter):
    @property
    def ident(self) -> str:
        return "crash_check_type"

    def title(self, cell: Cell) -> str:
        return _("Crash check type")

    def short_title(self, cell: Cell) -> str:
        return _("Check")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["crash_check_type"]

    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        return None, row.get("crash_check_type", "")


class PainterCrashServiceName(Painter):
    @property
    def ident(self) -> str:
        return "crash_service_name"

    def title(self, cell: Cell) -> str:
        return _("Crash service name")

    def short_title(self, cell: Cell) -> str:
        return _("Service")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["crash_service_name"]

    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        if not row.get("crash_service_name"):
            return None, ""

        url = makeuri_contextless(
            self.request,
            [
                ("host", row["crash_host"]),
                ("site", row["site"]),
                ("view_name", "service"),
                ("service", row["crash_service_name"]),
            ],
            filename="view.py",
        )
        return None, HTMLWriter.render_a(row["crash_service_name"], href=url)


def _sort_crash_host(
    r1: Row,
    r2: Row,
    *,
    parameters: Mapping[str, Any] | None,
    config: Config,
    request: Request,
) -> int:
    return cmp_simple_string("crash_host", r1, r2)


SorterCrashHost = Sorter(
    ident="crash_host",
    title=_l("Crash host"),
    columns=["crash_host"],
    sort_function=_sort_crash_host,
)


def _sort_crash_item(
    r1: Row,
    r2: Row,
    *,
    parameters: Mapping[str, Any] | None,
    config: Config,
    request: Request,
) -> int:
    return cmp_simple_string("crash_item", r1, r2)


SorterCrashItem = Sorter(
    ident="crash_item",
    title=_l("Crash item"),
    columns=["crash_item"],
    sort_function=_sort_crash_item,
)


def _sort_crash_check_type(
    r1: Row,
    r2: Row,
    *,
    parameters: Mapping[str, Any] | None,
    config: Config,
    request: Request,
) -> int:
    return cmp_simple_string("crash_check_type", r1, r2)


SorterCrashCheckType = Sorter(
    ident="crash_check_type",
    title=_l("Crash check type"),
    columns=["crash_check_type"],
    sort_function=_sort_crash_check_type,
)


def _sort_crash_service_name(
    r1: Row,
    r2: Row,
    *,
    parameters: Mapping[str, Any] | None,
    config: Config,
    request: Request,
) -> int:
    return cmp_simple_string("crash_service_name", r1, r2)


SorterCrashServiceName = Sorter(
    ident="crash_service_name",
    title=_l("Crash service name"),
    columns=["crash_service_name"],
    sort_function=_sort_crash_service_name,
)


def cmp_simple_string_columns(columns: Sequence[ColumnName], r1: Row, r2: Row) -> int:
    v1 = " ".join([r1.get(column, "") for column in columns])
    v2 = " ".join([r2.get(column, "") for column in columns])
    return cmp_insensitive_string(v1, v2)


def _sort_crash_exception(
    r1: Row,
    r2: Row,
    *,
    parameters: Mapping[str, Any] | None,
    config: Config,
    request: Request,
) -> int:
    return cmp_simple_string_columns(["crash_exception", "crash_exc_value"], r1, r2)


SorterCrashException = Sorter(
    ident="crash_exception",
    title=_l("Crash exception"),
    columns=["crash_exception", "crash_exc_value"],
    sort_function=_sort_crash_exception,
)


def _sort_crash_ident(
    r1: Row,
    r2: Row,
    *,
    parameters: Mapping[str, Any] | None,
    config: Config,
    request: Request,
) -> int:
    return cmp_simple_string("crash_id", r1, r2)


SorterCrashIdent = Sorter(
    ident="crash_ident",
    title=_("Crash ID"),
    columns=["crash_id"],
    sort_function=_sort_crash_ident,
)


def cmp_crash_source(column: ColumnName, r1: Row, r2: Row) -> int:
    v1 = str(local_files_involved_in_crash(r1.get(column, [])))
    v2 = str(local_files_involved_in_crash(r2.get(column, [])))
    return cmp_insensitive_string(v1, v2)


def _sort_crash_source(
    r1: Row,
    r2: Row,
    *,
    parameters: Mapping[str, Any] | None,
    config: Config,
    request: Request,
) -> int:
    return cmp_crash_source("crash_exc_traceback", r1, r2)


SorterCrashSource = Sorter(
    ident="crash_source",
    title=_("Crash source"),
    columns=["crash_exc_traceback"],
    sort_function=_sort_crash_source,
)


def _sort_crash_type(
    r1: Row,
    r2: Row,
    *,
    parameters: Mapping[str, Any] | None,
    config: Config,
    request: Request,
) -> int:
    return cmp_simple_string("crash_type", r1, r2)


SorterCrashType = Sorter(
    ident="crash_type",
    title=_("Crash type"),
    columns=["crash_type"],
    sort_function=_sort_crash_type,
)


def _sort_crash_version(
    r1: Row,
    r2: Row,
    *,
    parameters: Mapping[str, Any] | None,
    config: Config,
    request: Request,
) -> int:
    return cmp_simple_string("crash_version", r1, r2)


SorterCrashVersion = Sorter(
    ident="crash_version",
    title=_("Crash version"),
    columns=["crash_version"],
    sort_function=_sort_crash_version,
)


FilterCrashSite = SiteFilter(
    title=_l("Site"),
    sort_index=100,
    query_filter=query_filters.Query(
        ident="siteopt",
        request_vars=["site"],
    ),
    description=_l("Optional selection of a site"),
    heading_info=default_site_filter_heading_info,
)
FilterCrashSite.info = "crash"


class FilterCrashText(InputTextFilter):
    def __init__(self, *, ident: str, title: str, sort_index: int) -> None:
        super().__init__(
            title=title,
            sort_index=sort_index,
            info="crash",
            query_filter=query_filters.TableTextQuery(
                ident=ident, row_filter=query_filters.filter_by_column_textregex
            ),
            show_heading=False,
        )


FilterCrashId = FilterCrashText(title="Crash ID", ident="crash_id", sort_index=110)
FilterCrashHost = FilterCrashText(title="Crash host", ident="crash_host", sort_index=120)
FilterCrashServiceName = FilterCrashText(
    title="Crash service name",
    ident="crash_service_name",
    sort_index=130,
)
FilterCrashCheckType = FilterCrashText(
    title="Crash check type", ident="crash_check_type", sort_index=140
)
FilterCrashItem = FilterCrashText(title="Crash item", ident="crash_item", sort_index=150)
FilterCrashType = FilterCrashText(title="Crash type", ident="crash_type", sort_index=160)
FilterCrashVersion = FilterCrashText(title="Crash version", ident="crash_version", sort_index=170)


def crash_exception_row_filter(filtertext: str, column: str) -> Callable[[Row], bool]:
    regex = query_filters.re_ignorecase(filtertext, column)
    return lambda row: bool(
        regex.search(str("{}: {}".format(row["crash_exc_type"], row["crash_exc_value"])))
    )


FilterCrashException = FilterCrashText(
    title="Crash exception", ident="crash_exception", sort_index=175
)
FilterCrashException.query_filter = query_filters.TableTextQuery(
    ident=FilterCrashException.ident, row_filter=crash_exception_row_filter
)


def check_crash_source(selection: str, row: dict[str, Any]) -> bool:
    is_extension = local_files_involved_in_crash(row["crash_exc_traceback"])

    if selection == "built_in" and is_extension:
        return False

    if selection == "extension" and not is_extension:
        return False

    return True


FilterCrashSource = FilterOption(
    title="Crash source",
    sort_index=180,
    info="crash",
    query_filter=query_filters.SingleOptionQuery(
        ident="crash_source",
        options=[
            ("built_in", _("Built-in")),
            ("extension", _("Extension")),
            ("ignore", _("(ignore)")),
        ],
        filter_code=lambda x: "",
        filter_row=check_crash_source,
    ),
)

FilterCrashTime = FilterTime(
    title=_("Crash time"),
    sort_index=190,
    info="crash",
    query_filter=query_filters.TimeQuery(
        ident="crash_time",
        column="crash_time",
    ),
)

FilterCrashTime.query_filter.filter_row = query_filters.column_value_in_range
