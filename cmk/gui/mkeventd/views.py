#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="no-untyped-call"


import urllib.parse
from collections.abc import Callable, Mapping, Sequence
from typing import Any, Literal, TypeGuard, TypeVar

from livestatus import OnlySites

from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.ccc.site import SiteId
from cmk.ccc.user import UserId
from cmk.gui import sites
from cmk.gui.config import Config, default_authorized_builtin_role_ids
from cmk.gui.dashboard.type_defs import DashletConfig, LinkedViewDashletConfig, ViewDashletConfig
from cmk.gui.data_source import ABCDataSource, DataSourceRegistry, row_id, RowTableLivestatus
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.http import Request
from cmk.gui.http import request as active_request
from cmk.gui.i18n import _, _l, ungettext
from cmk.gui.logged_in import LoggedInUser, user
from cmk.gui.painter.v0 import Cell, Painter, PainterRegistry
from cmk.gui.painter.v0.helpers import paint_nagiosflag
from cmk.gui.painter.v0.painters import paint_custom_var
from cmk.gui.painter_options import paint_age
from cmk.gui.permissions import Permission, PermissionRegistry
from cmk.gui.theme import Theme
from cmk.gui.type_defs import (
    ColumnName,
    ColumnSpec,
    DynamicIconName,
    HTTPVariables,
    IconNames,
    Row,
    Rows,
    SingleInfos,
    SorterName,
    SorterSpec,
    StaticIcon,
    ViewSpec,
    VisualContext,
    VisualLinkSpec,
)
from cmk.gui.utils import escaping
from cmk.gui.utils.html import HTML
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import makeactionuri, makeuri_contextless, urlencode_vars
from cmk.gui.valuespec import MonitoringState
from cmk.gui.view_utils import CellSpec
from cmk.gui.views.command import (
    Command,
    CommandActionResult,
    CommandGroupVarious,
    CommandRegistry,
    CommandSpec,
)
from cmk.gui.views.sorter import (
    cmp_custom_variable,
    cmp_ec_sl_simple_number,
    cmp_num_split,
    cmp_simple_number,
    cmp_simple_string,
    declare_1to1_sorter,
    Sorter,
    SorterRegistry,
)
from cmk.gui.views.store import get_permitted_views, multisite_builtin_views
from cmk.gui.visuals.filter import Filter
from cmk.livestatus_client import (
    Command as LivestatusCommand,
)
from cmk.livestatus_client import (
    ECAction,
    ECChangeState,
    ECDelete,
    ECDeleteEventsOfHost,
    ECUpdate,
    LivestatusClient,
)
from cmk.utils.statename import short_service_state_name

from .defines import action_whats, phase_names, syslog_facilities, syslog_priorities
from .helpers import action_choices
from .permission_section import PERMISSION_SECTION_EVENT_CONSOLE


def register(
    data_source_registry: DataSourceRegistry,
    painter_registry: PainterRegistry,
    command_registry: CommandRegistry,
    sorter_registry: SorterRegistry,
    permission_registry: PermissionRegistry,
) -> None:
    data_source_registry.register(DataSourceECEvents)
    data_source_registry.register(DataSourceECEventHistory)

    multisite_builtin_views["ec_events"] = EC_EVENTS
    multisite_builtin_views["ec_events_of_monhost"] = EC_EVENTS_OF_MONHOST
    multisite_builtin_views["ec_events_of_host"] = EC_EVENTS_OF_HOST
    multisite_builtin_views["ec_event"] = EC_EVENT
    multisite_builtin_views["ec_history_recent"] = EC_HISTORY_RECENT
    multisite_builtin_views["ec_historyentry"] = EC_HISTORYENTRY
    multisite_builtin_views["ec_history_of_event"] = EC_HISTORY_OF_EVENT
    multisite_builtin_views["ec_history_of_host"] = EC_HISTORY_OF_HOST
    multisite_builtin_views["ec_event_mobile"] = EC_EVENT_MOBILE
    multisite_builtin_views["ec_events_mobile"] = EC_EVENTS_MOBILE

    painter_registry.register(PainterSvcServicelevel)
    painter_registry.register(PainterHostServicelevel)
    painter_registry.register(PainterEventId)
    painter_registry.register(PainterEventCount)
    painter_registry.register(PainterEventText)
    painter_registry.register(PainterEventMatchGroups)
    painter_registry.register(PainterEventFirst)
    painter_registry.register(PainterEventLast)
    painter_registry.register(PainterEventComment)
    painter_registry.register(PainterEventSl)
    painter_registry.register(PainterEventHost)
    painter_registry.register(PainterEventIpaddress)
    painter_registry.register(PainterEventHostInDowntime)
    painter_registry.register(PainterEventOwner)
    painter_registry.register(PainterEventContact)
    painter_registry.register(PainterEventApplication)
    painter_registry.register(PainterEventPid)
    painter_registry.register(PainterEventPriority)
    painter_registry.register(PainterEventFacility)
    painter_registry.register(PainterEventRuleId)
    painter_registry.register(PainterEventState)
    painter_registry.register(PainterEventPhase)
    painter_registry.register(PainterEventIcons)
    painter_registry.register(PainterEventHistoryIcons)
    painter_registry.register(PainterEventContactGroups)
    painter_registry.register(PainterEventEffectiveContactGroups)
    painter_registry.register(PainterHistoryLine)
    painter_registry.register(PainterHistoryTime)
    painter_registry.register(PainterHistoryWhat)
    painter_registry.register(PainterHistoryWhatExplained)
    painter_registry.register(PainterHistoryWho)
    painter_registry.register(PainterHistoryAddinfo)

    command_registry.register(CommandECUpdateEvent)
    command_registry.register(CommandECChangeState)
    command_registry.register(CommandECCustomAction)
    command_registry.register(CommandECArchiveEvent)
    command_registry.register(CommandECArchiveEventsOfHost)

    sorter_registry.register(SorterServicelevel)

    declare_1to1_sorter("svc_servicelevel", cmp_ec_sl_simple_number)
    declare_1to1_sorter("host_servicelevel", cmp_ec_sl_simple_number)
    declare_1to1_sorter("event_id", cmp_simple_number)
    declare_1to1_sorter("event_count", cmp_simple_number)
    declare_1to1_sorter("event_text", cmp_simple_string)
    declare_1to1_sorter("event_first", cmp_simple_number)
    declare_1to1_sorter("event_last", cmp_simple_number)
    declare_1to1_sorter("event_comment", cmp_simple_string)
    declare_1to1_sorter("event_sl", cmp_simple_number)
    declare_1to1_sorter("event_host", cmp_num_split)
    declare_1to1_sorter("event_ipaddress", cmp_num_split)
    declare_1to1_sorter("event_contact", cmp_simple_string)
    declare_1to1_sorter("event_application", cmp_simple_string)
    declare_1to1_sorter("event_pid", cmp_simple_number)
    declare_1to1_sorter("event_priority", cmp_simple_number)
    declare_1to1_sorter("event_facility", cmp_simple_number)  # maybe convert to text
    declare_1to1_sorter("event_rule_id", cmp_simple_string)
    declare_1to1_sorter("event_state", cmp_simple_state)
    declare_1to1_sorter("event_phase", cmp_simple_string)
    declare_1to1_sorter("event_owner", cmp_simple_string)

    declare_1to1_sorter("history_line", cmp_simple_number)
    declare_1to1_sorter("history_time", cmp_simple_number)
    declare_1to1_sorter("history_what", cmp_simple_string)
    declare_1to1_sorter("history_who", cmp_simple_string)
    declare_1to1_sorter("history_addinfo", cmp_simple_string)

    permission_registry.register(PermissionECSeeAll)
    permission_registry.register(PermissionECSeeUnrelated)
    permission_registry.register(PermissionECSeeInTacticalOverview)
    permission_registry.register(PermissionECUpdateEvent)
    permission_registry.register(PermissionECUpdateComment)
    permission_registry.register(PermissionECUpdateContact)
    permission_registry.register(PermissionECChangeEventState)
    permission_registry.register(PermissionECCustomActions)
    permission_registry.register(PermissionECArchiveEvent)
    permission_registry.register(PermissionECArchiveEventsOfHost)


#   .--Datasources---------------------------------------------------------.
#   |       ____        _                                                  |
#   |      |  _ \  __ _| |_ __ _ ___  ___  _   _ _ __ ___ ___  ___         |
#   |      | | | |/ _` | __/ _` / __|/ _ \| | | | '__/ __/ _ \/ __|        |
#   |      | |_| | (_| | || (_| \__ \ (_) | |_| | | | (_|  __/\__ \        |
#   |      |____/ \__,_|\__\__,_|___/\___/ \__,_|_|  \___\___||___/        |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class RowTableEC(RowTableLivestatus):
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
        for c in ["event_contact_groups", "host_contact_groups", "event_host"]:
            if c not in columns:
                columns.append(c)

        row_data = super().query(
            datasource, cells, columns, context, headers, only_sites, limit, all_active_filters
        )

        if isinstance(row_data, tuple):
            rows, _unfiltered_amount_of_rows = row_data
        else:
            rows = row_data

        if not rows:
            return rows

        _ec_filter_host_information_of_not_permitted_hosts(rows)

        if not user.may("mkeventd.seeall") and not user.may("mkeventd.seeunrelated"):
            # user is not allowed to see all events returned by the core
            rows = [r for r in rows if r["event_contact_groups"] != [] or r["host_name"] != ""]

        # Now we don't need to distinguish anymore between unrelated and related events. We
        # need the host_name field for rendering the views. Try our best and use the
        # event_host value as host_name.
        for row in rows:
            if not row.get("host_name"):
                row["host_name"] = row["event_host"]
                row["event_is_unrelated"] = True

        return rows


# Handle the case where a user is allowed to see all events (-> events for hosts he
# is not permitted for). In this case the user should be allowed to see the event
# information, but not the host related information.
#
# To realize this, we filter all data from the host_* columns from the response.
# See Gitbug #2462 for some more information.
#
# This should be handled in the core, but the core does not know anything about
# the "mkeventd.seeall" permissions. So it is simply not possible to do this on
# core level at the moment.
def _ec_filter_host_information_of_not_permitted_hosts(rows: Rows) -> None:
    if user.may("mkeventd.seeall"):
        return  # Don't remove anything. The user may see everything

    user_groups = set(user.contact_groups)

    def is_contact(row: Row) -> bool:
        return bool(user_groups.intersection(row["host_contact_groups"]))

    if rows:
        remove_keys = [c for c in rows[0].keys() if c.startswith("host_")]
    else:
        remove_keys = []

    for row in rows:
        if row["host_name"] == "":
            continue  # This is an "unrelated host", don't treat it here

        if is_contact(row):
            continue  # The user may see these host information

        # Now remove the host information. This can sadly not apply the cores
        # default values for the different columns. We try our best to clean up
        for key in remove_keys:
            if isinstance(row[key], list):
                row[key] = []
            elif isinstance(row[key], int):
                row[key] = 0
            elif isinstance(row[key], float):
                row[key] = 0.0
            elif isinstance(row[key], str):
                row[key] = ""
            elif isinstance(row[key], str):
                row[key] = ""


PermissionECSeeAll = Permission(
    section=PERMISSION_SECTION_EVENT_CONSOLE,
    name="seeall",
    title=_("See all events"),
    description=_(
        "If a user lacks this permission then he/she can see only those events that "
        "originate from a host that he/she is a contact for."
    ),
    defaults=default_authorized_builtin_role_ids,
)

PermissionECSeeUnrelated = Permission(
    section=PERMISSION_SECTION_EVENT_CONSOLE,
    name="seeunrelated",
    title=_("See events not related to a known host"),
    description=_(
        "If that user does not have the permission <i>See all events</i> then this permission "
        "controls whether he/she can see events that are not related to a host in the monitoring "
        "and that do not have been assigned specific contact groups to via the event rule."
    ),
    defaults=default_authorized_builtin_role_ids,
)

PermissionECSeeInTacticalOverview = Permission(
    section=PERMISSION_SECTION_EVENT_CONSOLE,
    name="see_in_tactical_overview",
    title=_("See events in the sidebar element 'Overview'"),
    description=_(
        "Whether or not the user is permitted to see the number of open events in the "
        "sidebar element 'Overview'."
    ),
    defaults=default_authorized_builtin_role_ids,
)


class DataSourceECEvents(ABCDataSource):
    @property
    def ident(self) -> str:
        return "mkeventd_events"

    @property
    def title(self) -> str:
        return _("Event Console: Current events")

    @property
    def table(self) -> RowTableEC:
        return RowTableEC("eventconsoleevents")

    @property
    def infos(self) -> SingleInfos:
        return ["event", "host"]

    @property
    def keys(self) -> list[ColumnName]:
        return []

    @property
    def id_keys(self) -> list[ColumnName]:
        return ["site", "host_name", "event_id"]

    @property
    def auth_domain(self) -> str:
        return "ec"

    @property
    def time_filters(self) -> list[ColumnName]:
        return ["event_first"]


class DataSourceECEventHistory(ABCDataSource):
    @property
    def ident(self) -> str:
        return "mkeventd_history"

    @property
    def title(self) -> str:
        return _("Event Console: Event history")

    @property
    def table(self) -> RowTableEC:
        return RowTableEC("eventconsolehistory")

    @property
    def infos(self) -> SingleInfos:
        return ["history", "event", "host"]

    @property
    def keys(self) -> list[ColumnName]:
        return []

    @property
    def id_keys(self) -> list[ColumnName]:
        return ["site", "host_name", "event_id", "history_line"]

    @property
    def auth_domain(self) -> str:
        return "ec"

    @property
    def time_filters(self) -> list[ColumnName]:
        return ["history_time"]


# .
#   .--Painters------------------------------------------------------------.
#   |                 ____       _       _                                 |
#   |                |  _ \ __ _(_)_ __ | |_ ___ _ __ ___                  |
#   |                | |_) / _` | | '_ \| __/ _ \ '__/ __|                 |
#   |                |  __/ (_| | | | | | ||  __/ |  \__ \                 |
#   |                |_|   \__,_|_|_| |_|\__\___|_|  |___/                 |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class PainterSvcServicelevel(Painter):
    @property
    def ident(self) -> str:
        return "svc_servicelevel"

    def title(self, cell: Cell) -> str:
        return _("Service service level")

    def short_title(self, cell: Cell) -> str:
        return _("Service level")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["service_custom_variable_names", "service_custom_variable_values"]

    @property
    def sorter(self) -> SorterName:
        return "servicelevel"

    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        return paint_custom_var(
            "service",
            "EC_SL",
            row,
            self.config.mkeventd_service_levels,
        )


class PainterHostServicelevel(Painter):
    @property
    def ident(self) -> str:
        return "host_servicelevel"

    def title(self, cell: Cell) -> str:
        return _("Host service level")

    def short_title(self, cell: Cell) -> str:
        return _("Service level")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_custom_variable_names", "host_custom_variable_values"]

    @property
    def sorter(self) -> SorterName:
        return "servicelevel"

    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        return paint_custom_var(
            "host",
            "EC_SL",
            row,
            self.config.mkeventd_service_levels,
        )


class PainterEventId(Painter):
    @property
    def ident(self) -> str:
        return "event_id"

    def title(self, cell: Cell) -> str:
        return _("ID of the event")

    def short_title(self, cell: Cell) -> str:
        return _("ID")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["event_id"]

    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        return ("number", str(row["event_id"]))


class PainterEventCount(Painter):
    @property
    def ident(self) -> str:
        return "event_count"

    def title(self, cell: Cell) -> str:
        return _("Count (number of recent occurrences)")

    def short_title(self, cell: Cell) -> str:
        return _("Cnt.")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["event_count"]

    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        return ("number", str(row["event_count"]))


class PainterEventText(Painter):
    @property
    def ident(self) -> str:
        return "event_text"

    def title(self, cell: Cell) -> str:
        return _("Text/Message of the event")

    def short_title(self, cell: Cell) -> str:
        return _("Message")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["event_text"]

    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        return "", HTML.without_escaping(
            escaping.escape_attribute(row["event_text"]).replace("\x01", "<br>")
        )


class PainterEventMatchGroups(Painter):
    @property
    def ident(self) -> str:
        return "event_match_groups"

    def title(self, cell: Cell) -> str:
        return _("Match groups")

    def short_title(self, cell: Cell) -> str:
        return _("Match")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["event_match_groups"]

    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        groups = row["event_match_groups"]
        if groups:
            code = HTML.empty()
            for text in groups:
                code += HTMLWriter.render_span(text)
            return "matchgroups", code
        return "", HTML.empty()


class PainterEventFirst(Painter):
    @property
    def ident(self) -> str:
        return "event_first"

    def title(self, cell: Cell) -> str:
        return _("Time of first occurrence of this serial")

    def short_title(self, cell: Cell) -> str:
        return _("First")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["event_first"]

    @property
    def painter_options(self) -> list[str]:
        return ["ts_format", "ts_date"]

    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        return paint_age(
            row["event_first"],
            True,
            True,
            request=self.request,
            painter_options=self._painter_options,
        )


class PainterEventLast(Painter):
    @property
    def ident(self) -> str:
        return "event_last"

    def title(self, cell: Cell) -> str:
        return _("Time of last occurrence")

    def short_title(self, cell: Cell) -> str:
        return _("Last")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["event_last"]

    @property
    def painter_options(self) -> list[str]:
        return ["ts_format", "ts_date"]

    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        return paint_age(
            row["event_last"],
            True,
            True,
            request=self.request,
            painter_options=self._painter_options,
        )


class PainterEventComment(Painter):
    @property
    def ident(self) -> str:
        return "event_comment"

    def title(self, cell: Cell) -> str:
        return _("Comment to the event")

    def short_title(self, cell: Cell) -> str:
        return _("Comment")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["event_comment"]

    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        return ("", row["event_comment"])


class PainterEventSl(Painter):
    @property
    def ident(self) -> str:
        return "event_sl"

    def title(self, cell: Cell) -> str:
        return _("Service-level")

    def short_title(self, cell: Cell) -> str:
        return _("Level")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["event_sl"]

    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        sl_txt = dict(self.config.mkeventd_service_levels).get(
            row["event_sl"], str(row["event_sl"])
        )
        return "", sl_txt


class PainterEventHost(Painter):
    @property
    def ident(self) -> str:
        return "event_host"

    def title(self, cell: "Cell") -> str:
        return _("Host name")

    def short_title(self, cell: "Cell") -> str:
        return _("Host")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["event_host", "host_name"]

    @property
    def use_painter_link(self) -> bool:
        return False

    def render(self, row: Row, cell: "Cell", user: LoggedInUser) -> CellSpec:
        event_host: HostAddress = row["event_host"]
        host_name = row.get("host_name", event_host)

        return "", html.render_a(
            host_name, _get_event_host_link(host_name, row, cell, request=self.request)
        )


def _get_event_host_link(host_name: HostName, row: Row, cell: "Cell", *, request: Request) -> str:
    """
    Needed to support links to views and dashboards. If no link is configured,
    always use ec_events_of_host as target view.
    """
    link_type: str = "view_name"
    filename: str = "view.py"
    link_target: str = "ec_events_of_host"
    if link_spec := cell._link_spec:
        if link_spec.type_name == "dashboards":
            link_type = "name"
            filename = "dashboard.py"
        link_target = link_spec.name

    # See SUP-10272 for a detailed explanation, hacks of view.py do not
    # work for SNMP traps
    return makeuri_contextless(
        request,
        [
            (link_type, link_target),
            ("host", host_name),
            ("event_host", row["event_host"]),
        ],
        filename=filename,
    )


class PainterEventIpaddress(Painter):
    @property
    def ident(self) -> str:
        return "event_ipaddress"

    def title(self, cell: Cell) -> str:
        return _("Original IP address")

    def short_title(self, cell: Cell) -> str:
        return _("Orig. IP")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["event_ipaddress"]

    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        return ("", row["event_ipaddress"])


class PainterEventHostInDowntime(Painter):
    @property
    def ident(self) -> str:
        return "event_host_in_downtime"

    def title(self, cell: Cell) -> str:
        return _("Host in downtime during event creation")

    def short_title(self, cell: Cell) -> str:
        return _("Dt.")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["event_host_in_downtime"]

    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        return paint_nagiosflag(row, "event_host_in_downtime", True)


class PainterEventOwner(Painter):
    @property
    def ident(self) -> str:
        return "event_owner"

    def title(self, cell: Cell) -> str:
        return _("Owner of event")

    def short_title(self, cell: Cell) -> str:
        return _("Owner")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["event_owner"]

    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        return ("", row["event_owner"])


class PainterEventContact(Painter):
    @property
    def ident(self) -> str:
        return "event_contact"

    def title(self, cell: Cell) -> str:
        return _("Contact person")

    def short_title(self, cell: Cell) -> str:
        return _("Contact")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["event_contact"]

    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        return ("", row["event_contact"])


class PainterEventApplication(Painter):
    @property
    def ident(self) -> str:
        return "event_application"

    def title(self, cell: Cell) -> str:
        return _("Application / Syslog-Tag")

    def short_title(self, cell: Cell) -> str:
        return _("Application")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["event_application"]

    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        return ("", row["event_application"])


class PainterEventPid(Painter):
    @property
    def ident(self) -> str:
        return "event_pid"

    def title(self, cell: Cell) -> str:
        return _("Process ID")

    def short_title(self, cell: Cell) -> str:
        return _("PID")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["event_pid"]

    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        return ("", "%s" % row["event_pid"])


# TODO: Rethink the typing of syslog_facilites/syslog_priorities.
T = TypeVar("T")


def _deref(x: T | Callable[[], T]) -> T:
    return x() if callable(x) else x


class PainterEventPriority(Painter):
    @property
    def ident(self) -> str:
        return "event_priority"

    def title(self, cell: Cell) -> str:
        return _("Syslog-Priority")

    def short_title(self, cell: Cell) -> str:
        return _("Prio")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["event_priority"]

    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        return ("", dict(_deref(syslog_priorities))[row["event_priority"]])


class PainterEventFacility(Painter):
    @property
    def ident(self) -> str:
        return "event_facility"

    def title(self, cell: Cell) -> str:
        return _("Syslog-Facility")

    def short_title(self, cell: Cell) -> str:
        return _("Facility")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["event_facility"]

    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        return ("", dict(_deref(syslog_facilities))[row["event_facility"]])


class PainterEventRuleId(Painter):
    @property
    def ident(self) -> str:
        return "event_rule_id"

    def title(self, cell: Cell) -> str:
        return _("Rule-ID")

    def short_title(self, cell: Cell) -> str:
        return _("Rule")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["event_rule_id"]

    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        rule_id = row["event_rule_id"]
        if user.may("mkeventd.edit"):
            urlvars = urlencode_vars([("mode", "mkeventd_edit_rule"), ("rule_id", rule_id)])
            return "", HTMLWriter.render_a(rule_id, "wato.py?%s" % urlvars)
        return "", rule_id


class PainterEventState(Painter):
    @property
    def ident(self) -> str:
        return "event_state"

    def title(self, cell: Cell) -> str:
        return _("State (severity) of event")

    def short_title(self, cell: Cell) -> str:
        return _("State")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["event_state"]

    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        state = row["event_state"]
        name = short_service_state_name(state, "")
        return "state svcstate state%s" % state, HTMLWriter.render_span(
            name, class_=["state_rounded_fill"]
        )


class PainterEventPhase(Painter):
    @property
    def ident(self) -> str:
        return "event_phase"

    def title(self, cell: Cell) -> str:
        return _("Phase of event (open, counting, etc.)")

    def short_title(self, cell: Cell) -> str:
        return _("Phase")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["event_phase"]

    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        return ("", phase_names.get(row["event_phase"], ""))


def paint_event_icons(
    row: Row,
    history: bool = False,
    *,
    request: Request,
    theme: Theme,
) -> CellSpec:
    phase = row["event_phase"]

    htmlcode: str | HTML
    if phase == "ack":
        htmlcode = html.render_icon(
            phase,
            title=_("This event has been acknowledged."),
            theme=theme,
        )
    elif phase == "counting":
        htmlcode = html.render_icon(
            phase,
            title=_("This event has not reached the target count yet."),
            theme=theme,
        )
    elif phase == "delayed":
        htmlcode = html.render_icon(
            phase,
            title=_("The action of this event is still delayed in the hope of a cancelling event."),
            theme=theme,
        )
    else:
        htmlcode = ""

    if not history:
        htmlcode += render_delete_event_icons(row, request=request)

    if row["event_host_in_downtime"]:
        htmlcode += html.render_static_icon(
            StaticIcon(IconNames.downtime),
            title=_("Host in downtime during event creation"),
        )

    if htmlcode:
        return "icons", htmlcode
    return "", ""


def render_delete_event_icons(row: Row, *, request: Request) -> str | HTML:
    if not user.may("mkeventd.delete"):
        return ""
    urlvars: HTTPVariables = []

    # Found no cleaner way to get the view. Sorry.
    # TODO: This needs to be cleaned up with the new view implementation.
    filename: str | None = None
    if _is_rendered_from_view_dashlet(request):
        ident = request.get_integer_input_mandatory("id")

        from cmk.gui import dashboard

        # With the typed dicts we currently don't have an easy way of determining the type
        dashlet_config = dashboard.get_dashlet(request.get_str_input_mandatory("name"), ident)
        view: ViewDashletConfig | ViewSpec
        if _is_view_dashlet(dashlet_config):
            view = dashlet_config
        elif _is_linked_view_dashlet(dashlet_config):
            view = get_permitted_views()[dashlet_config["name"]]
        else:
            return ""

        # These actions are not performed within the dashlet. Assume the title url still
        # links to the source view where the action can be performed.
        title_url = dashlet_config.get("title_url")
        if title_url:
            parsed_url = urllib.parse.urlparse(title_url)
            filename = parsed_url.path
            urlvars += urllib.parse.parse_qsl(parsed_url.query)
    else:
        # Regular view
        view = get_permitted_views()[request.get_str_input_mandatory("view_name")]

    urlvars += [
        ("filled_in", "actions"),
        ("actions", "yes"),
        ("_do_actions", "yes"),
        ("_row_id", row_id(view["datasource"], row)),
        ("_delete_event", _("Archive Event")),
        ("_show_result", "0"),
    ]
    url = makeactionuri(
        request, transactions, urlvars, filename=filename, delvars=["selection", "show_checkboxes"]
    )
    return html.render_icon_button(
        url, _("Archive this event"), StaticIcon(IconNames.archive_event)
    )


def _is_rendered_from_view_dashlet(request: Request) -> bool:
    return request.has_var("name") and request.has_var("id")


def _is_view_dashlet(dashlet_config: DashletConfig) -> TypeGuard[ViewDashletConfig]:
    return dashlet_config["type"] == "view"


def _is_linked_view_dashlet(dashlet_config: DashletConfig) -> TypeGuard[LinkedViewDashletConfig]:
    return dashlet_config["type"] == "linked_view"


class PainterEventIcons(Painter):
    @property
    def ident(self) -> str:
        return "event_icons"

    def title(self, cell: Cell) -> str:
        return _("Event icons")

    def short_title(self, cell: Cell) -> str:
        return _("Icons")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["event_phase", "event_host_in_downtime"]

    @property
    def printable(self) -> bool:
        return False

    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        return paint_event_icons(row, request=self.request, theme=self.theme)


class PainterEventHistoryIcons(Painter):
    @property
    def ident(self) -> str:
        return "event_history_icons"

    def title(self, cell: Cell) -> str:
        return _("Event history icons")

    def short_title(self, cell: Cell) -> str:
        return _("Icons")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["event_phase", "event_host_in_downtime"]

    @property
    def printable(self) -> bool:
        return False

    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        return paint_event_icons(row, history=True, request=self.request, theme=self.theme)


class PainterEventContactGroups(Painter):
    @property
    def ident(self) -> str:
        return "event_contact_groups"

    def title(self, cell: Cell) -> str:
        return _("Contact groups defined in rule")

    def short_title(self, cell: Cell) -> str:
        return _("Rule contact groups")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["event_contact_groups"]

    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        cgs = row.get("event_contact_groups")
        if cgs is None:
            return "", ""
        if cgs:
            return "", ", ".join(cgs)
        return "", "<i>" + _("none") + "</i>"


class PainterEventEffectiveContactGroups(Painter):
    @property
    def ident(self) -> str:
        return "event_effective_contact_groups"

    def title(self, cell: Cell) -> str:
        return _("Contact groups effective (host or rule contact groups)")

    def short_title(self, cell: Cell) -> str:
        return _("Contact groups")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return [
            "event_contact_groups",
            "event_contact_groups_precedence",
            "host_contact_groups",
        ]

    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        if row["event_contact_groups_precedence"] == "host":
            cgs = row["host_contact_groups"]
        else:
            cgs = row["event_contact_groups"]

        if cgs is None:
            return "", ""
        if cgs:
            return "", ", ".join(sorted(cgs))
        return "", HTMLWriter.render_i(_("none"))


# Event History


class PainterHistoryLine(Painter):
    @property
    def ident(self) -> str:
        return "history_line"

    def title(self, cell: Cell) -> str:
        return _("Line number in log file")

    def short_title(self, cell: Cell) -> str:
        return _("Line")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["history_line"]

    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        return ("number", "%s" % row["history_line"])


class PainterHistoryTime(Painter):
    @property
    def ident(self) -> str:
        return "history_time"

    def title(self, cell: Cell) -> str:
        return _("Time of entry in log file")

    def short_title(self, cell: Cell) -> str:
        return _("Time")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["history_time"]

    @property
    def painter_options(self) -> list[str]:
        return ["ts_format", "ts_date"]

    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        return paint_age(
            row["history_time"],
            True,
            True,
            request=self.request,
            painter_options=self._painter_options,
        )


class PainterHistoryWhat(Painter):
    @property
    def ident(self) -> str:
        return "history_what"

    def title(self, cell: Cell) -> str:
        return _("Type of event action")

    def short_title(self, cell: Cell) -> str:
        return _("Action")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["history_what"]

    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        what = row["history_what"]
        return "", HTMLWriter.render_span(what, title=str(action_whats[what]))


class PainterHistoryWhatExplained(Painter):
    @property
    def ident(self) -> str:
        return "history_what_explained"

    def title(self, cell: Cell) -> str:
        return _("Explanation for event action")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["history_what"]

    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        return ("", str(action_whats[row["history_what"]]))


class PainterHistoryWho(Painter):
    @property
    def ident(self) -> str:
        return "history_who"

    def title(self, cell: Cell) -> str:
        return _("User who performed action")

    def short_title(self, cell: Cell) -> str:
        return _("Who")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["history_who"]

    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        return ("", row["history_who"])


class PainterHistoryAddinfo(Painter):
    @property
    def ident(self) -> str:
        return "history_addinfo"

    def title(self, cell: Cell) -> str:
        return _("Additional information")

    def short_title(self, cell: Cell) -> str:
        return _("Info")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["history_addinfo"]

    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        return ("", row["history_addinfo"])


# .
#   .--Commands------------------------------------------------------------.
#   |         ____                                          _              |
#   |        / ___|___  _ __ ___  _ __ ___   __ _ _ __   __| |___          |
#   |       | |   / _ \| '_ ` _ \| '_ ` _ \ / _` | '_ \ / _` / __|         |
#   |       | |__| (_) | | | | | | | | | | | (_| | | | | (_| \__ \         |
#   |        \____\___/|_| |_| |_|_| |_| |_|\__,_|_| |_|\__,_|___/         |
#   |                                                                      |
#   '----------------------------------------------------------------------'

PermissionECUpdateEvent = Permission(
    section=PERMISSION_SECTION_EVENT_CONSOLE,
    name="update",
    title=_l("Update an event"),
    description=_l("Needed for acknowledging and changing the comment and contact of an event"),
    defaults=["user", "admin"],
)

# Sub-Permissions for Changing Comment, Contact and Acknowledgement
PermissionECUpdateComment = Permission(
    section=PERMISSION_SECTION_EVENT_CONSOLE,
    name="update_comment",
    title=_l("Update an event: change comment"),
    description=_l("Needed for changing a comment when updating an event"),
    defaults=["user", "admin"],
)

# Sub-Permissions for Changing Comment, Contact and Acknowledgement
PermissionECUpdateContact = Permission(
    section=PERMISSION_SECTION_EVENT_CONSOLE,
    name="update_contact",
    title=_l("Update an event: change contact"),
    description=_l("Needed for changing a contact when updating an event"),
    defaults=["user", "admin"],
)


class ECCommand(Command):
    def affected(self, len_action_rows: int, cmdtag: Literal["HOST", "SVC"]) -> HTML:
        return HTML.with_escaping(
            _("Affected %s: %s")
            % (
                ungettext(
                    "event",
                    "events",
                    len_action_rows,
                ),
                len_action_rows,
            )
        )

    def executor(self, command: CommandSpec, site: SiteId | None) -> None:
        assert isinstance(command, LivestatusCommand)
        LivestatusClient(sites.live()).command(command, site)


def command_update_event_render(what: str) -> None:
    html.open_table(border="0", cellpadding="0", cellspacing="3")
    if user.may("mkeventd.update_comment"):
        html.open_tr()
        html.td(_("Change comment:"))
        html.open_td()
        html.text_input("_mkeventd_comment", size=50)
        html.close_td()
        html.close_tr()
    if user.may("mkeventd.update_contact"):
        html.open_tr()
        html.td(_("Change contact:"))
        html.open_td()
        html.text_input("_mkeventd_contact", size=50)
        html.close_td()
        html.close_tr()
    html.open_tr()
    html.td("")
    html.open_td()
    html.checkbox("_mkeventd_acknowledge", True, label=_("Set event to acknowledged"))
    html.close_td()
    html.close_tr()
    html.close_table()
    html.open_div(class_="group")
    html.button("_mkeventd_update", _("Update"), cssclass="hot")
    html.button("_cancel", _("Cancel"))
    html.close_div()


def command_update_event_action(
    command: Command,
    cmdtag: Literal["HOST", "SVC"],
    spec: str,
    row: Row,
    row_index: int,
    action_rows: Rows,
) -> CommandActionResult:
    if active_request.var("_mkeventd_update"):
        if user.may("mkeventd.update_comment"):
            comment = (
                active_request.get_str_input_mandatory("_mkeventd_comment")
                .strip()
                .replace(";", ",")
            )
        else:
            comment = ""
        if user.may("mkeventd.update_contact"):
            contact = (
                active_request.get_str_input_mandatory("_mkeventd_contact")
                .strip()
                .replace(":", ",")
            )
        else:
            contact = ""
        ack = html.get_checkbox("_mkeventd_acknowledge")
        events = tuple(int(entry["event_id"]) for entry in action_rows)
        return ECUpdate(events, ack, user.ident, comment, contact), command.confirm_dialog_options(
            cmdtag, row, action_rows
        )

    return None


CommandECUpdateEvent = ECCommand(
    ident="ec_update_event",
    title=_l("Update & acknowledge"),
    confirm_title=lambda: (
        _l("Update & acknowledge event?")
        if active_request.var("_mkeventd_acknowledge")
        else _l("Update event?")
    ),
    confirm_button=lambda: (
        _l("Update & acknowledge") if active_request.var("_mkeventd_acknowledge") else _l("Update")
    ),
    permission=PermissionECUpdateEvent,
    group=CommandGroupVarious,
    tables=["event"],
    render=command_update_event_render,
    action=command_update_event_action,
)

PermissionECChangeEventState = Permission(
    section=PERMISSION_SECTION_EVENT_CONSOLE,
    name="changestate",
    title=_l("Change event state"),
    description=_l(
        "This permission allows to change the state classification of an event "
        "(e.g. from CRIT to WARN)."
    ),
    defaults=["user", "admin"],
)


def command_change_state_confirm_dialog_additions(
    cmdtag: Literal["HOST", "SVC"],
    row: Row,
    action_rows: Rows,
) -> HTML:
    value = MonitoringState().from_html_vars("_mkeventd_state")
    assert value is not None
    return (
        HTMLWriter.render_br()
        + HTMLWriter.render_br()
        + _("New state: %s")
        % {
            0: _("OK"),
            1: _("WARN"),
            2: _("CRIT"),
            3: _("UNKNOWN"),
        }[value]
    )


def command_change_state_render(what: str) -> None:
    MonitoringState(label="Select new event state").render_input("_mkeventd_state", 2)
    html.br()
    html.br()
    html.open_div(class_="group")
    html.button("_mkeventd_changestate", _("Change state"), cssclass="hot")
    html.button("_cancel", _("Cancel"))
    html.close_div()


def command_change_state_action(
    command: Command,
    cmdtag: Literal["HOST", "SVC"],
    spec: str,
    row: Row,
    row_index: int,
    action_rows: Rows,
) -> CommandActionResult:
    if active_request.var("_mkeventd_changestate"):
        events = tuple(int(entry["event_id"]) for entry in action_rows)
        state = MonitoringState().from_html_vars("_mkeventd_state")
        return (
            ECChangeState(events, user.ident, state),
            command.confirm_dialog_options(cmdtag, row, action_rows),
        )
    return None


CommandECChangeState = ECCommand(
    ident="ec_change_state",
    title=_l("Change state"),
    confirm_title=_l("Change event state?"),
    confirm_button=_l("Change"),
    permission=PermissionECChangeEventState,
    group=CommandGroupVarious,
    tables=["event"],
    render=command_change_state_render,
    action=command_change_state_action,
    confirm_dialog_additions=command_change_state_confirm_dialog_additions,
)

PermissionECCustomActions = Permission(
    section=PERMISSION_SECTION_EVENT_CONSOLE,
    name="actions",
    title=_l("Perform custom action"),
    description=_l(
        "This permission is needed for performing the configured actions "
        "(execution of scripts and sending emails)."
    ),
    defaults=["user", "admin"],
)


def command_custom_actions_render(what: str) -> None:
    html.open_div(class_="group")
    for action_id, title in action_choices(omit_hidden=True):
        html.button("_action_" + action_id, title, cssclass="border_hot")
        html.br()
        html.br()
    html.button("_cancel", _("Cancel"))
    html.close_div()


def command_custom_actions_action(
    command: Command,
    cmdtag: Literal["HOST", "SVC"],
    spec: str,
    row: Row,
    row_index: int,
    action_rows: Rows,
) -> CommandActionResult:
    for action_id, _title in action_choices(omit_hidden=True):
        if active_request.var("_action_" + action_id):
            events = tuple(int(entry["event_id"]) for entry in action_rows)
            return (
                ECAction(events, action_id, user.ident),
                command.confirm_dialog_options(cmdtag, row, action_rows),
            )
    return None


CommandECCustomAction = ECCommand(
    ident="ec_custom_actions",
    title=_l("Custom action"),
    confirm_title=lambda: (
        _l("Execute custom action '%s'?") % list(active_request.itervars(prefix="_action_"))[0][1]
    ),
    confirm_button=_l("Execute"),
    permission=PermissionECCustomActions,
    group=CommandGroupVarious,
    tables=["event"],
    render=command_custom_actions_render,
    action=command_custom_actions_action,
)

PermissionECArchiveEvent = Permission(
    section=PERMISSION_SECTION_EVENT_CONSOLE,
    name="delete",
    title=_l("Archive an event"),
    description=_l("Finally archive an event without any further action"),
    defaults=["user", "admin"],
)


def command_archive_event_render(what: str) -> None:
    html.open_div(class_="group")
    html.button("_delete_event", _("Archive Event"), cssclass="hot")
    html.button("_cancel", _("Cancel"))
    html.close_div()


def command_archive_event_action(
    command: Command,
    cmdtag: Literal["HOST", "SVC"],
    spec: str,
    row: Row,
    row_index: int,
    action_rows: Rows,
) -> CommandActionResult:
    if active_request.var("_delete_event"):
        events = tuple(int(entry["event_id"]) for entry in action_rows)
        cmd = ECDelete(events, user.ident)
        return cmd, command.confirm_dialog_options(cmdtag, row, action_rows)
    return None


CommandECArchiveEvent = ECCommand(
    ident="ec_archive_event",
    title=_l("Archive event"),
    confirm_title=_l("Archive event?"),
    confirm_button=_l("Archive"),
    permission=PermissionECArchiveEvent,
    group=CommandGroupVarious,
    tables=["event"],
    render=command_archive_event_render,
    action=command_archive_event_action,
)

PermissionECArchiveEventsOfHost = Permission(
    section=PERMISSION_SECTION_EVENT_CONSOLE,
    name="archive_events_of_hosts",
    title=_l("Archive events of hosts"),
    description=_l("Archive all open events of all hosts shown in host views"),
    defaults=["user", "admin"],
)


def command_archive_events_of_host_confirm_dialog_additions(
    cmdtag: Literal["HOST", "SVC"],
    row: Row,
    action_rows: Rows,
) -> HTML:
    return HTML.empty() + _(
        "All events of the host '%s' will be removed from the open events list. You can still access them in the archive."
    ) % active_request.var("host")


def command_archive_events_of_host_render(what: str) -> None:
    html.help(
        _(
            "Note: With this command you can archive all events of one host. "
            'Needs a rule "Check event state in Event Console" to be '
            "configured."
        )
    )
    html.open_div(class_="group")
    html.button("_archive_events_of_hosts", _("Archive events"), cssclass="hot")
    html.button("_cancel", _("Cancel"))
    html.close_div()


def command_archive_events_of_host_action(
    command: Command,
    cmdtag: Literal["HOST", "SVC"],
    spec: str,
    row: Row,
    row_index: int,
    action_rows: Rows,
) -> CommandActionResult:
    if active_request.var("_archive_events_of_hosts"):
        commands = [ECDeleteEventsOfHost(HostName(row["host_name"]), user.ident)]
        return (
            commands,
            command.confirm_dialog_options(cmdtag, row, action_rows),
        )
    return None


CommandECArchiveEventsOfHost = ECCommand(
    ident="ec_archive_events_of_host",
    title=_l("Archive events of hosts"),
    confirm_title=_l("Archive all events of this host?"),
    confirm_button=_l("Archive"),
    permission=PermissionECArchiveEventsOfHost,
    group=CommandGroupVarious,
    tables=["service"],
    render=command_archive_events_of_host_render,
    action=command_archive_events_of_host_action,
    confirm_dialog_additions=command_archive_events_of_host_confirm_dialog_additions,
    affected_output_cb=lambda _a, _b: HTML.empty(),
)

# .
#   .--Sorters-------------------------------------------------------------.
#   |                  ____             _                                  |
#   |                 / ___|  ___  _ __| |_ ___ _ __ ___                   |
#   |                 \___ \ / _ \| '__| __/ _ \ '__/ __|                  |
#   |                  ___) | (_) | |  | ||  __/ |  \__ \                  |
#   |                 |____/ \___/|_|   \__\___|_|  |___/                  |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def _sort_service_level(
    r1: Row,
    r2: Row,
    *,
    parameters: Mapping[str, Any] | None,
    config: Config,
    request: Request,
) -> int:
    return cmp_custom_variable(r1, r2, "EC_SL", cmp_simple_number)


SorterServicelevel = Sorter(
    ident="servicelevel",
    title=_("Service level"),
    columns=["custom_variables"],
    sort_function=_sort_service_level,
)


def cmp_simple_state(column: ColumnName, ra: Row, rb: Row) -> int:
    a = ra.get(column, -1)
    b = rb.get(column, -1)
    if a == 3:
        a = 1.5
    if b == 3:
        b = 1.5
    return (a > b) - (a < b)


# .
#   .--Views---------------------------------------------------------------.
#   |                    __     ___                                        |
#   |                    \ \   / (_) _____      _____                      |
#   |                     \ \ / /| |/ _ \ \ /\ / / __|                     |
#   |                      \ V / | |  __/\ V  V /\__ \                     |
#   |                       \_/  |_|\___| \_/\_/ |___/                     |
#   |                                                                      |
#   '----------------------------------------------------------------------'

_EC_VIEW_DEFAULTS = ViewSpec(
    {
        "topic": "events",
        "browser_reload": 60,
        "column_headers": "pergroup",
        "icon": DynamicIconName("event_console"),
        "mobile": False,
        "hidden": False,
        "mustsearch": False,
        "group_painters": [],
        "num_columns": 1,
        "hidebutton": False,
        "play_sounds": False,
        "public": True,
        "sorters": [],
        "user_sortable": True,
        "link_from": {},
        "add_context_to_title": True,
        "main_menu_search_terms": [],
        "owner": UserId.builtin(),
        "name": "",
        "single_infos": [],
        "context": {},
        "sort_index": 99,
        "is_show_more": False,
        "packaged": False,
        "title": "",
        "description": "",
        "datasource": "",
        "layout": "table",
        "painters": [],
    }
)


# Table of all open events
EC_EVENTS: ViewSpec = {
    **_EC_VIEW_DEFAULTS,
    "group_painters": [],
    "sorters": [SorterSpec(sorter="event_last", negate=False)],
    "sort_index": 10,
    "title": _l("Events"),
    "description": _l("Table of all currently open events (handled and unhandled)"),
    "datasource": "mkeventd_events",
    "layout": "table",
    "painters": [
        ColumnSpec(
            name="event_id",
            link_spec=VisualLinkSpec(type_name="views", name="ec_event"),
        ),
        ColumnSpec(name="event_icons"),
        ColumnSpec(name="event_state"),
        ColumnSpec(name="event_sl"),
        ColumnSpec(
            name="event_host",
            link_spec=VisualLinkSpec(type_name="views", name="ec_events_of_host"),
        ),
        ColumnSpec(name="event_rule_id"),
        ColumnSpec(name="event_application"),
        ColumnSpec(name="event_text"),
        ColumnSpec(name="event_last"),
        ColumnSpec(name="event_count"),
    ],
    "is_show_more": True,
    "packaged": False,
    "owner": UserId.builtin(),
    "name": "ec_events",
    "single_infos": [],
    "context": {
        "event_id": {},
        "event_rule_id": {},
        "event_text": {},
        "event_application": {},
        "event_contact": {},
        "event_comment": {},
        "event_host_regex": {},
        "event_ipaddress": {},
        "event_count": {},
        "event_phase": {
            "event_phase_counting": "",
            "event_phase_delayed": "",
            "event_phase_open": "on",
            "event_phase_ack": "on",
        },
        "event_state": {},
        "event_first": {},
        "event_last": {},
        "event_priority": {},
        "event_facility": {},
        "event_sl": {},
        "event_sl_max": {},
        "event_host_in_downtime": {},
        "hostregex": {},
        "siteopt": {},
    },
}

EC_EVENTS_OF_MONHOST = ViewSpec(
    {
        **_EC_VIEW_DEFAULTS,
        "hidden": True,
        "group_painters": [],
        "sorters": [SorterSpec(sorter="event_last", negate=False)],
        "title": _l("Events of monitored host"),
        "description": _l("Currently open events of a host that is monitored"),
        "datasource": "mkeventd_events",
        "layout": "table",
        "painters": [
            ColumnSpec(
                name="event_id",
                link_spec=VisualLinkSpec(type_name="views", name="ec_event"),
            ),
            ColumnSpec(name="event_icons"),
            ColumnSpec(name="event_state"),
            ColumnSpec(name="event_sl"),
            ColumnSpec(name="event_rule_id"),
            ColumnSpec(name="event_application"),
            ColumnSpec(name="event_text"),
            ColumnSpec(name="event_last"),
            ColumnSpec(name="event_count"),
        ],
        "owner": UserId.builtin(),
        "name": "ec_events_of_monhost",
        "single_infos": ["host"],
        "context": {
            "siteopt": {},
            "event_id": {},
            "event_rule_id": {},
            "event_text": {},
            "event_application": {},
            "event_contact": {},
            "event_comment": {},
            "event_count": {},
            "event_phase": {},
            "event_state": {},
            "event_first": {},
            "event_last": {},
            "event_priority": {},
            "event_facility": {},
            "event_sl": {},
            "event_sl_max": {},
            "event_host_in_downtime": {},
        },
        "sort_index": 99,
        "is_show_more": False,
        "packaged": False,
    }
)

EC_EVENTS_OF_HOST = ViewSpec(
    {
        **_EC_VIEW_DEFAULTS,
        "hidden": True,
        "group_painters": [],
        "sorters": [SorterSpec(sorter="event_last", negate=False)],
        "title": _l("Events of host"),
        "description": _l("Currently open events of one specific host"),
        "datasource": "mkeventd_events",
        "layout": "table",
        "painters": [
            ColumnSpec(
                name="event_id",
                link_spec=VisualLinkSpec(type_name="views", name="ec_event"),
            ),
            ColumnSpec(name="event_icons"),
            ColumnSpec(name="event_state"),
            ColumnSpec(name="event_sl"),
            ColumnSpec(name="event_rule_id"),
            ColumnSpec(name="event_application"),
            ColumnSpec(name="event_text"),
            ColumnSpec(name="event_last"),
            ColumnSpec(name="event_count"),
        ],
        "owner": UserId.builtin(),
        "name": "ec_events_of_host",
        "single_infos": ["host"],
        "context": {
            "siteopt": {},
            "event_host": {},
            "event_id": {},
            "event_rule_id": {},
            "event_text": {},
            "event_application": {},
            "event_contact": {},
            "event_comment": {},
            "event_count": {},
            "event_phase": {},
            "event_state": {},
            "event_first": {},
            "event_last": {},
            "event_priority": {},
            "event_facility": {},
            "event_sl": {},
            "event_sl_max": {},
            "event_host_in_downtime": {},
        },
        "sort_index": 99,
        "is_show_more": False,
        "packaged": False,
    }
)

EC_EVENT = ViewSpec(
    {
        **_EC_VIEW_DEFAULTS,
        "browser_reload": 0,
        "hidden": True,
        "group_painters": [],
        "sorters": [],
        "title": _l("Event details"),
        "description": _l("Details about one event"),
        "datasource": "mkeventd_events",
        "layout": "dataset",
        "painters": [
            ColumnSpec(name="event_state"),
            ColumnSpec(name="event_host"),
            ColumnSpec(name="event_ipaddress"),
            ColumnSpec(name="foobar"),
            ColumnSpec(
                name="alias",
                link_spec=VisualLinkSpec(type_name="views", name="hoststatus"),
            ),
            ColumnSpec(name="host_contacts"),
            ColumnSpec(name="host_icons"),
            ColumnSpec(name="event_text"),
            ColumnSpec(name="event_match_groups"),
            ColumnSpec(name="event_comment"),
            ColumnSpec(name="event_owner"),
            ColumnSpec(name="event_first"),
            ColumnSpec(name="event_last"),
            ColumnSpec(name="event_id"),
            ColumnSpec(name="event_icons"),
            ColumnSpec(name="event_count"),
            ColumnSpec(name="event_sl"),
            ColumnSpec(name="event_contact"),
            ColumnSpec(name="event_effective_contact_groups"),
            ColumnSpec(name="event_application"),
            ColumnSpec(name="event_pid"),
            ColumnSpec(name="event_priority"),
            ColumnSpec(name="event_facility"),
            ColumnSpec(name="event_rule_id"),
            ColumnSpec(name="event_phase"),
            ColumnSpec(name="host_services"),
        ],
        "owner": UserId.builtin(),
        "name": "ec_event",
        "single_infos": ["event"],
        "context": {},
        "sort_index": 99,
        "is_show_more": False,
        "packaged": False,
    }
)

EC_HISTORY_RECENT = ViewSpec(
    {
        **_EC_VIEW_DEFAULTS,
        "icon": {
            "icon": DynamicIconName("event_console"),
            "emblem": "time",
        },
        "group_painters": [],
        "sorters": [
            SorterSpec(sorter="history_time", negate=True),
            SorterSpec(sorter="history_line", negate=True),
        ],
        "sort_index": 20,
        "title": _l("Recent event history"),
        "description": _l(
            "Information about events and actions on events during the recent 24 hours."
        ),
        "datasource": "mkeventd_history",
        "layout": "table",
        "painters": [
            ColumnSpec(name="history_time"),
            ColumnSpec(
                name="event_id",
                link_spec=VisualLinkSpec(type_name="views", name="ec_historyentry"),
            ),
            ColumnSpec(name="history_who"),
            ColumnSpec(name="history_what"),
            ColumnSpec(name="event_history_icons"),
            ColumnSpec(name="event_state"),
            ColumnSpec(name="event_phase"),
            ColumnSpec(name="event_sl"),
            ColumnSpec(
                name="event_host",
                link_spec=VisualLinkSpec(type_name="views", name="ec_history_of_host"),
            ),
            ColumnSpec(name="event_rule_id"),
            ColumnSpec(name="event_application"),
            ColumnSpec(name="event_text"),
            ColumnSpec(name="event_last"),
            ColumnSpec(name="event_count"),
        ],
        "is_show_more": True,
        "packaged": False,
        "owner": UserId.builtin(),
        "name": "ec_history_recent",
        "single_infos": [],
        "context": {
            "event_id": {},
            "event_rule_id": {},
            "event_text": {},
            "event_application": {},
            "event_contact": {},
            "event_comment": {},
            "event_host_regex": {},
            "event_ipaddress": {},
            "event_count": {},
            "event_phase": {},
            "event_state": {},
            "event_first": {},
            "event_last": {},
            "event_priority": {},
            "event_facility": {},
            "event_sl": {},
            "event_sl_max": {},
            "event_host_in_downtime": {},
            "history_time": {"history_time_from": "1", "history_time_from_range": "86400"},
            "history_who": {},
            "history_what": {},
            "host_state_type": {},
            "hostregex": {},
            "siteopt": {},
        },
    }
)

EC_HISTORYENTRY = ViewSpec(
    {
        **_EC_VIEW_DEFAULTS,
        "browser_reload": 0,
        "hidden": True,
        "group_painters": [],
        "sorters": [],
        "title": _l("Event history entry"),
        "description": _l("Details about a historical event history entry"),
        "datasource": "mkeventd_history",
        "layout": "dataset",
        "painters": [
            ColumnSpec(name="history_time"),
            ColumnSpec(name="history_line"),
            ColumnSpec(name="history_what"),
            ColumnSpec(name="history_what_explained"),
            ColumnSpec(name="history_who"),
            ColumnSpec(name="history_addinfo"),
            ColumnSpec(name="event_state"),
            ColumnSpec(
                name="event_host",
                link_spec=VisualLinkSpec(type_name="views", name="ec_history_of_host"),
            ),
            ColumnSpec(name="event_ipaddress"),
            ColumnSpec(name="event_text"),
            ColumnSpec(name="event_match_groups"),
            ColumnSpec(name="event_comment"),
            ColumnSpec(name="event_owner"),
            ColumnSpec(name="event_first"),
            ColumnSpec(name="event_last"),
            ColumnSpec(
                name="event_id",
                link_spec=VisualLinkSpec(type_name="views", name="ec_history_of_event"),
            ),
            ColumnSpec(name="event_history_icons"),
            ColumnSpec(name="event_count"),
            ColumnSpec(name="event_sl"),
            ColumnSpec(name="event_contact"),
            ColumnSpec(name="event_effective_contact_groups"),
            ColumnSpec(name="event_application"),
            ColumnSpec(name="event_pid"),
            ColumnSpec(name="event_priority"),
            ColumnSpec(name="event_facility"),
            ColumnSpec(name="event_rule_id"),
            ColumnSpec(name="event_phase"),
        ],
        "owner": UserId.builtin(),
        "name": "ec_historyentry",
        "single_infos": ["history"],
        "context": {},
        "sort_index": 99,
        "is_show_more": False,
        "packaged": False,
    }
)

EC_HISTORY_OF_EVENT = ViewSpec(
    {
        **_EC_VIEW_DEFAULTS,
        "browser_reload": 0,
        "hidden": True,
        "group_painters": [],
        "sorters": [
            SorterSpec(sorter="history_time", negate=True),
            SorterSpec(sorter="history_line", negate=True),
        ],
        "title": _l("History of event"),
        "description": _l("History entries of one specific event"),
        "datasource": "mkeventd_history",
        "layout": "table",
        "num_columns": 1,
        "painters": [
            ColumnSpec(name="history_time"),
            ColumnSpec(
                name="history_line",
                link_spec=VisualLinkSpec(type_name="views", name="ec_historyentry"),
            ),
            ColumnSpec(name="history_what"),
            ColumnSpec(name="history_what_explained"),
            ColumnSpec(name="history_who"),
            ColumnSpec(name="event_state"),
            ColumnSpec(name="event_host"),
            ColumnSpec(name="event_application"),
            ColumnSpec(name="event_text"),
            ColumnSpec(name="event_sl"),
            ColumnSpec(name="event_priority"),
            ColumnSpec(name="event_facility"),
            ColumnSpec(name="event_phase"),
            ColumnSpec(name="event_count"),
        ],
        "owner": UserId.builtin(),
        "name": "ec_history_of_event",
        "single_infos": ["event"],
        "context": {},
        "sort_index": 99,
        "is_show_more": False,
        "packaged": False,
    }
)

EC_HISTORY_OF_HOST = ViewSpec(
    {
        **_EC_VIEW_DEFAULTS,
        "browser_reload": 0,
        "hidden": True,
        "group_painters": [],
        "sorters": [
            SorterSpec(sorter="history_time", negate=True),
            SorterSpec(sorter="history_line", negate=True),
        ],
        "title": _l("Event history of host"),
        "description": _l("History entries of one specific host"),
        "datasource": "mkeventd_history",
        "layout": "table",
        "painters": [
            ColumnSpec(name="history_time"),
            ColumnSpec(
                name="event_id",
                link_spec=VisualLinkSpec(type_name="views", name="ec_history_of_event"),
            ),
            ColumnSpec(
                name="history_line",
                link_spec=VisualLinkSpec(type_name="views", name="ec_historyentry"),
            ),
            ColumnSpec(name="history_what"),
            ColumnSpec(name="history_what_explained"),
            ColumnSpec(name="history_who"),
            ColumnSpec(name="event_state"),
            ColumnSpec(name="event_host"),
            ColumnSpec(name="event_ipaddress"),
            ColumnSpec(name="event_application"),
            ColumnSpec(name="event_text"),
            ColumnSpec(name="event_sl"),
            ColumnSpec(name="event_priority"),
            ColumnSpec(name="event_facility"),
            ColumnSpec(name="event_phase"),
            ColumnSpec(name="event_count"),
        ],
        "owner": UserId.builtin(),
        "name": "ec_history_of_host",
        "single_infos": ["host"],
        "context": {
            "event_host": {},
            "event_id": {},
            "event_rule_id": {},
            "event_text": {},
            "event_application": {},
            "event_contact": {},
            "event_comment": {},
            "event_count": {},
            "event_phase": {},
            "event_state": {},
            "event_first": {},
            "event_last": {},
            "event_priority": {},
            "event_facility": {},
            "event_sl": {},
            "event_sl_max": {},
            "event_host_in_downtime": {},
            "history_time": {},
            "history_who": {},
            "history_what": {},
        },
        "link_from": {},
        "add_context_to_title": True,
        "sort_index": 99,
        "is_show_more": False,
        "packaged": False,
    }
)

EC_EVENT_MOBILE: ViewSpec = {
    **_EC_VIEW_DEFAULTS,
    "browser_reload": 0,
    "column_headers": "pergroup",
    "context": {},
    "datasource": "mkeventd_events",
    "description": _l("Details about one event\n"),
    "group_painters": [],
    "hidden": True,
    "hidebutton": False,
    "icon": DynamicIconName("event"),
    "layout": "mobiledataset",
    "mobile": True,
    "name": "ec_event_mobile",
    "num_columns": 1,
    "painters": [
        ColumnSpec(name="event_state"),
        ColumnSpec(name="event_host"),
        ColumnSpec(name="event_ipaddress"),
        ColumnSpec(
            name="host_address",
            link_spec=VisualLinkSpec(type_name="views", name="hoststatus"),
        ),
        ColumnSpec(name="host_contacts"),
        ColumnSpec(name="host_icons"),
        ColumnSpec(name="event_text"),
        ColumnSpec(name="event_comment"),
        ColumnSpec(name="event_owner"),
        ColumnSpec(name="event_first"),
        ColumnSpec(name="event_last"),
        ColumnSpec(name="event_id"),
        ColumnSpec(name="event_icons"),
        ColumnSpec(name="event_count"),
        ColumnSpec(name="event_sl"),
        ColumnSpec(name="event_contact"),
        ColumnSpec(name="event_effective_contact_groups"),
        ColumnSpec(name="event_application"),
        ColumnSpec(name="event_pid"),
        ColumnSpec(name="event_priority"),
        ColumnSpec(name="event_facility"),
        ColumnSpec(name="event_rule_id"),
        ColumnSpec(name="event_phase"),
        ColumnSpec(name="host_services"),
    ],
    "public": True,
    "single_infos": ["event"],
    "sorters": [],
    "title": _l("Event details"),
    "topic": "events",
    "user_sortable": True,
    "owner": UserId.builtin(),
    "link_from": {},
    "add_context_to_title": True,
    "sort_index": 99,
    "is_show_more": False,
    "packaged": False,
    "main_menu_search_terms": [],
}

EC_EVENTS_MOBILE: ViewSpec = {
    **_EC_VIEW_DEFAULTS,
    "browser_reload": 60,
    "column_headers": "pergroup",
    "context": {
        "event_application": {"event_application": ""},
        "event_comment": {"event_comment": ""},
        "event_contact": {"event_contact": ""},
        "event_count": {"event_count_from": "", "event_count_until": ""},
        "event_facility": {"event_facility": ""},
        "event_first": {
            "event_first_from": "",
            "event_first_from_range": "3600",
            "event_first_until": "",
            "event_first_until_range": "3600",
        },
        "event_host_regex": {"event_host_regex": ""},
        "event_id": {"event_id": ""},
        "event_last": {
            "event_last_from": "",
            "event_last_from_range": "3600",
            "event_last_until": "",
            "event_last_until_range": "3600",
        },
        "event_phase": {
            "event_phase_ack": "on",
            "event_phase_closed": "on",
            "event_phase_counting": "",
            "event_phase_delayed": "",
            "event_phase_open": "on",
        },
        "event_priority": {
            "event_priority_0": "on",
            "event_priority_1": "on",
            "event_priority_2": "on",
            "event_priority_3": "on",
            "event_priority_4": "on",
            "event_priority_5": "on",
            "event_priority_6": "on",
            "event_priority_7": "on",
        },
        "event_rule_id": {"event_rule_id": ""},
        "event_sl": {"event_sl": ""},
        "event_sl_max": {"event_sl_max": ""},
        "event_state": {
            "event_state_0": "on",
            "event_state_1": "on",
            "event_state_2": "on",
            "event_state_3": "on",
        },
        "event_text": {"event_text": ""},
        "hostregex": {"host_regex": ""},
    },
    "datasource": "mkeventd_events",
    "description": _l("Table of all currently open events (handled and unhandled)\n"),
    "group_painters": [],
    "hidden": False,
    "hidebutton": False,
    "icon": DynamicIconName("event"),
    "layout": "mobilelist",
    "mobile": True,
    "name": "ec_events_mobile",
    "num_columns": 1,
    "owner": UserId.builtin(),
    "painters": [
        ColumnSpec(
            name="event_id",
            link_spec=VisualLinkSpec(type_name="views", name="ec_event_mobile"),
        ),
        ColumnSpec(name="event_state"),
        ColumnSpec(name="event_host"),
        ColumnSpec(name="event_application"),
        ColumnSpec(name="event_text"),
        ColumnSpec(name="event_last"),
    ],
    "public": True,
    "single_infos": [],
    "sorters": [SorterSpec(sorter="event_last", negate=False)],
    "title": _l("Events"),
    "topic": "events",
    "user_sortable": True,
    "link_from": {},
    "add_context_to_title": True,
    "sort_index": 99,
    "is_show_more": False,
    "packaged": False,
    "main_menu_search_terms": [],
}
