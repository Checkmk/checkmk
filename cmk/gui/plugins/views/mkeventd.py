#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import urllib.parse
from typing import Callable, Optional, TypeVar, Union

from livestatus import SiteId

from cmk.utils.defines import short_service_state_name

import cmk.gui.mkeventd as mkeventd
import cmk.gui.sites as sites
import cmk.gui.utils.escaping as escaping
from cmk.gui.config import active_config, builtin_role_ids
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _, _l, ungettext
from cmk.gui.logged_in import user
from cmk.gui.permissions import Permission, permission_registry
from cmk.gui.plugins.dashboard.utils import DashletConfig
from cmk.gui.plugins.views.utils import (
    ABCDataSource,
    cmp_num_split,
    cmp_simple_number,
    cmp_simple_string,
    Command,
    command_registry,
    CommandActionResult,
    CommandSpec,
    data_source_registry,
    declare_1to1_sorter,
    get_permitted_views,
    multisite_builtin_views,
    paint_age,
    paint_nagiosflag,
    Painter,
    painter_registry,
    row_id,
    RowTableLivestatus,
)
from cmk.gui.type_defs import HTTPVariables, Row, SingleInfos, ViewSpec
from cmk.gui.utils.html import HTML
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import makeactionuri, urlencode_vars
from cmk.gui.valuespec import MonitoringState

#   .--Datasources---------------------------------------------------------.
#   |       ____        _                                                  |
#   |      |  _ \  __ _| |_ __ _ ___  ___  _   _ _ __ ___ ___  ___         |
#   |      | | | |/ _` | __/ _` / __|/ _ \| | | | '__/ __/ _ \/ __|        |
#   |      | |_| | (_| | || (_| \__ \ (_) | |_| | | | (_|  __/\__ \        |
#   |      |____/ \__,_|\__\__,_|___/\___/ \__,_|_|  \___\___||___/        |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class RowTableEC(RowTableLivestatus):
    def query(self, view, columns, headers, only_sites, limit, all_active_filters):
        for c in ["event_contact_groups", "host_contact_groups", "event_host"]:
            if c not in columns:
                columns.append(c)

        row_data = super().query(view, columns, headers, only_sites, limit, all_active_filters)

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
# To realize this, whe filter all data from the host_* columns from the response.
# See Gitbug #2462 for some more information.
#
# This should be handled in the core, but the core does not know anything about
# the "mkeventd.seeall" permissions. So it is simply not possible to do this on
# core level at the moment.
def _ec_filter_host_information_of_not_permitted_hosts(rows):
    if user.may("mkeventd.seeall"):
        return  # Don't remove anything. The user may see everything

    user_groups = set(user.contact_groups)

    def is_contact(row):
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


permission_registry.register(
    Permission(
        section=mkeventd.PermissionSectionEventConsole,
        name="seeall",
        title=_("See all events"),
        description=_(
            "If a user lacks this permission then he/she can see only those events that "
            "originate from a host that he/she is a contact for."
        ),
        defaults=builtin_role_ids,
    )
)

permission_registry.register(
    Permission(
        section=mkeventd.PermissionSectionEventConsole,
        name="seeunrelated",
        title=_("See events not related to a known host"),
        description=_(
            "If that user does not have the permission <i>See all events</i> then this permission "
            "controls wether he/she can see events that are not related to a host in the monitoring "
            "and that do not have been assigned specific contact groups to via the event rule."
        ),
        defaults=builtin_role_ids,
    )
)

permission_registry.register(
    Permission(
        section=mkeventd.PermissionSectionEventConsole,
        name="see_in_tactical_overview",
        title=_("See events in the sidebar element 'Overview'"),
        description=_(
            "Whether or not the user is permitted to see the number of open events in the "
            "sidebar element 'Overview'."
        ),
        defaults=builtin_role_ids,
    )
)


@data_source_registry.register
class DataSourceECEvents(ABCDataSource):
    @property
    def ident(self) -> str:
        return "mkeventd_events"

    @property
    def title(self) -> str:
        return _("Event Console: Current events")

    @property
    def table(self):
        return RowTableEC("eventconsoleevents")

    @property
    def infos(self) -> SingleInfos:
        return ["event", "host"]

    @property
    def keys(self):
        return []

    @property
    def id_keys(self):
        return ["site", "host_name", "event_id"]

    @property
    def auth_domain(self):
        return "ec"

    @property
    def time_filters(self):
        return ["event_first"]


@data_source_registry.register
class DataSourceECEventHistory(ABCDataSource):
    @property
    def ident(self) -> str:
        return "mkeventd_history"

    @property
    def title(self) -> str:
        return _("Event Console: Event history")

    @property
    def table(self):
        return RowTableEC("eventconsolehistory")

    @property
    def infos(self) -> SingleInfos:
        return ["history", "event", "host"]

    @property
    def keys(self):
        return []

    @property
    def id_keys(self):
        return ["site", "host_name", "event_id", "history_line"]

    @property
    def auth_domain(self):
        return "ec"

    @property
    def time_filters(self):
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


@painter_registry.register
class PainterEventId(Painter):
    @property
    def ident(self) -> str:
        return "event_id"

    def title(self, cell):
        return _("ID of the event")

    def short_title(self, cell):
        return _("ID")

    @property
    def columns(self):
        return ["event_id"]

    def render(self, row, cell):
        return ("number", str(row["event_id"]))


@painter_registry.register
class PainterEventCount(Painter):
    @property
    def ident(self) -> str:
        return "event_count"

    def title(self, cell):
        return _("Count (number of recent occurrances)")

    def short_title(self, cell):
        return _("Cnt.")

    @property
    def columns(self):
        return ["event_count"]

    def render(self, row, cell):
        return ("number", str(row["event_count"]))


@painter_registry.register
class PainterEventText(Painter):
    @property
    def ident(self) -> str:
        return "event_text"

    def title(self, cell):
        return _("Text/Message of the event")

    def short_title(self, cell):
        return _("Message")

    @property
    def columns(self):
        return ["event_text"]

    def render(self, row, cell):
        return "", HTML(escaping.escape_attribute(row["event_text"]).replace("\x01", "<br>"))


@painter_registry.register
class PainterEventMatchGroups(Painter):
    @property
    def ident(self) -> str:
        return "event_match_groups"

    def title(self, cell):
        return _("Match groups")

    def short_title(self, cell):
        return _("Match")

    @property
    def columns(self):
        return ["event_match_groups"]

    def render(self, row, cell):
        groups = row["event_match_groups"]
        if groups:
            code = HTML("")
            for text in groups:
                code += HTMLWriter.render_span(text)
            return "matchgroups", code
        return "", HTML("")


@painter_registry.register
class PainterEventFirst(Painter):
    @property
    def ident(self) -> str:
        return "event_first"

    def title(self, cell):
        return _("Time of first occurrence of this serial")

    def short_title(self, cell):
        return _("First")

    @property
    def columns(self):
        return ["event_first"]

    @property
    def painter_options(self):
        return ["ts_format", "ts_date"]

    def render(self, row, cell):
        return paint_age(row["event_first"], True, True)


@painter_registry.register
class PainterEventLast(Painter):
    @property
    def ident(self) -> str:
        return "event_last"

    def title(self, cell):
        return _("Time of last occurrance")

    def short_title(self, cell):
        return _("Last")

    @property
    def columns(self):
        return ["event_last"]

    @property
    def painter_options(self):
        return ["ts_format", "ts_date"]

    def render(self, row, cell):
        return paint_age(row["event_last"], True, True)


@painter_registry.register
class PainterEventComment(Painter):
    @property
    def ident(self) -> str:
        return "event_comment"

    def title(self, cell):
        return _("Comment to the event")

    def short_title(self, cell):
        return _("Comment")

    @property
    def columns(self):
        return ["event_comment"]

    def render(self, row, cell):
        return ("", row["event_comment"])


@painter_registry.register
class PainterEventSl(Painter):
    @property
    def ident(self) -> str:
        return "event_sl"

    def title(self, cell):
        return _("Service-level")

    def short_title(self, cell):
        return _("Level")

    @property
    def columns(self):
        return ["event_sl"]

    def render(self, row, cell):
        sl_txt = dict(active_config.mkeventd_service_levels).get(
            row["event_sl"], str(row["event_sl"])
        )
        return "", sl_txt


@painter_registry.register
class PainterEventHost(Painter):
    @property
    def ident(self) -> str:
        return "event_host"

    def title(self, cell):
        return _("Hostname")

    def short_title(self, cell):
        return _("Host")

    @property
    def columns(self):
        return ["event_host", "host_name"]

    def render(self, row, cell):
        if row["host_name"]:
            return "", row["host_name"]
        return "", row["event_host"]


@painter_registry.register
class PainterEventIpaddress(Painter):
    @property
    def ident(self) -> str:
        return "event_ipaddress"

    def title(self, cell):
        return _("Original IP address")

    def short_title(self, cell):
        return _("Orig. IP")

    @property
    def columns(self):
        return ["event_ipaddress"]

    def render(self, row, cell):
        return ("", row["event_ipaddress"])


@painter_registry.register
class PainterEventHostInDowntime(Painter):
    @property
    def ident(self) -> str:
        return "event_host_in_downtime"

    def title(self, cell):
        return _("Host in downtime during event creation")

    def short_title(self, cell):
        return _("Dt.")

    @property
    def columns(self):
        return ["event_host_in_downtime"]

    def render(self, row, cell):
        return paint_nagiosflag(row, "event_host_in_downtime", True)


@painter_registry.register
class PainterEventOwner(Painter):
    @property
    def ident(self) -> str:
        return "event_owner"

    def title(self, cell):
        return _("Owner of event")

    def short_title(self, cell):
        return _("Owner")

    @property
    def columns(self):
        return ["event_owner"]

    def render(self, row, cell):
        return ("", row["event_owner"])


@painter_registry.register
class PainterEventContact(Painter):
    @property
    def ident(self) -> str:
        return "event_contact"

    def title(self, cell):
        return _("Contact person")

    def short_title(self, cell):
        return _("Contact")

    @property
    def columns(self):
        return ["event_contact"]

    def render(self, row, cell):
        return ("", row["event_contact"])


@painter_registry.register
class PainterEventApplication(Painter):
    @property
    def ident(self) -> str:
        return "event_application"

    def title(self, cell):
        return _("Application / Syslog-Tag")

    def short_title(self, cell):
        return _("Application")

    @property
    def columns(self):
        return ["event_application"]

    def render(self, row, cell):
        return ("", row["event_application"])


@painter_registry.register
class PainterEventPid(Painter):
    @property
    def ident(self) -> str:
        return "event_pid"

    def title(self, cell):
        return _("Process ID")

    def short_title(self, cell):
        return _("PID")

    @property
    def columns(self):
        return ["event_pid"]

    def render(self, row, cell):
        return ("", "%s" % row["event_pid"])


# TODO: Rethink the typing of syslog_facilites/syslog_priorities.
T = TypeVar("T")


def _deref(x: Union[T, Callable[[], T]]) -> T:
    return x() if callable(x) else x


@painter_registry.register
class PainterEventPriority(Painter):
    @property
    def ident(self) -> str:
        return "event_priority"

    def title(self, cell):
        return _("Syslog-Priority")

    def short_title(self, cell):
        return _("Prio")

    @property
    def columns(self):
        return ["event_priority"]

    def render(self, row, cell):
        return ("", dict(_deref(mkeventd.syslog_priorities))[row["event_priority"]])


@painter_registry.register
class PainterEventFacility(Painter):
    @property
    def ident(self) -> str:
        return "event_facility"

    def title(self, cell):
        return _("Syslog-Facility")

    def short_title(self, cell):
        return _("Facility")

    @property
    def columns(self):
        return ["event_facility"]

    def render(self, row, cell):
        return ("", dict(_deref(mkeventd.syslog_facilities))[row["event_facility"]])


@painter_registry.register
class PainterEventRuleId(Painter):
    @property
    def ident(self) -> str:
        return "event_rule_id"

    def title(self, cell):
        return _("Rule-ID")

    def short_title(self, cell):
        return _("Rule")

    @property
    def columns(self):
        return ["event_rule_id"]

    def render(self, row, cell):
        rule_id = row["event_rule_id"]
        if user.may("mkeventd.edit"):
            urlvars = urlencode_vars([("mode", "mkeventd_edit_rule"), ("rule_id", rule_id)])
            return "", HTMLWriter.render_a(rule_id, "wato.py?%s" % urlvars)
        return "", rule_id


@painter_registry.register
class PainterEventState(Painter):
    @property
    def ident(self) -> str:
        return "event_state"

    def title(self, cell):
        return _("State (severity) of event")

    def short_title(self, cell):
        return _("State")

    @property
    def columns(self):
        return ["event_state"]

    def render(self, row, cell):
        state = row["event_state"]
        name = short_service_state_name(state, "")
        return "state svcstate state%s" % state, HTMLWriter.render_span(
            name, class_=["state_rounded_fill"]
        )


@painter_registry.register
class PainterEventPhase(Painter):
    @property
    def ident(self) -> str:
        return "event_phase"

    def title(self, cell):
        return _("Phase of event (open, counting, etc.)")

    def short_title(self, cell):
        return _("Phase")

    @property
    def columns(self):
        return ["event_phase"]

    def render(self, row, cell):
        return ("", mkeventd.phase_names.get(row["event_phase"], ""))


def paint_event_icons(row, history=False):
    htmlcode = render_event_phase_icons(row)

    if not history:
        htmlcode += render_delete_event_icons(row)

    if row["event_host_in_downtime"]:
        htmlcode += html.render_icon("downtime", _("Host in downtime during event creation"))

    if htmlcode:
        return "icons", htmlcode
    return "", ""


def render_event_phase_icons(row):
    phase = row["event_phase"]

    if phase == "ack":
        title = _("This event has been acknowledged.")
    elif phase == "counting":
        title = _("This event has not reached the target count yet.")
    elif phase == "delayed":
        title = _("The action of this event is still delayed in the hope of a cancelling event.")
    else:
        return ""

    return html.render_icon(phase, title=title)


def render_delete_event_icons(row):
    if not user.may("mkeventd.delete"):
        return ""
    urlvars: HTTPVariables = []

    # Found no cleaner way to get the view. Sorry.
    # TODO: This needs to be cleaned up with the new view implementation.
    filename: Optional[str] = None
    if _is_rendered_from_view_dashlet():
        ident = request.get_integer_input_mandatory("id")

        import cmk.gui.dashboard as dashboard

        dashlet_config: DashletConfig = dashboard.get_dashlet(
            request.get_str_input_mandatory("name"), ident
        )
        if dashlet_config.get("type") == "linked_view":
            view: Union[DashletConfig, ViewSpec] = get_permitted_views()[dashlet_config["name"]]
        else:
            view = dashlet_config

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
        ("_row_id", row_id(view, row)),
        ("_delete_event", _("Archive Event")),
        ("_show_result", "0"),
    ]
    url = makeactionuri(
        request, transactions, urlvars, filename=filename, delvars=["selection", "show_checkboxes"]
    )
    return html.render_icon_button(url, _("Archive this event"), "archive_event")


def _is_rendered_from_view_dashlet() -> bool:
    return html.request.has_var("name") and html.request.has_var("id")


@painter_registry.register
class PainterEventIcons(Painter):
    @property
    def ident(self) -> str:
        return "event_icons"

    def title(self, cell):
        return _("Event icons")

    def short_title(self, cell):
        return _("Icons")

    @property
    def columns(self):
        return ["event_phase", "event_host_in_downtime"]

    @property
    def printable(self):
        return False

    def render(self, row, cell):
        return paint_event_icons(row)


@painter_registry.register
class PainterEventHistoryIcons(Painter):
    @property
    def ident(self) -> str:
        return "event_history_icons"

    def title(self, cell):
        return _("Event history icons")

    def short_title(self, cell):
        return _("Icons")

    @property
    def columns(self):
        return ["event_phase", "event_host_in_downtime"]

    @property
    def printable(self):
        return False

    def render(self, row, cell):
        return paint_event_icons(row, history=True)


@painter_registry.register
class PainterEventContactGroups(Painter):
    @property
    def ident(self) -> str:
        return "event_contact_groups"

    def title(self, cell):
        return _("Contact groups defined in rule")

    def short_title(self, cell):
        return _("Rule contact groups")

    @property
    def columns(self):
        return ["event_contact_groups"]

    def render(self, row, cell):
        cgs = row.get("event_contact_groups")
        if cgs is None:
            return "", ""
        if cgs:
            return "", ", ".join(cgs)
        return "", "<i>" + _("none") + "</i>"


@painter_registry.register
class PainterEventEffectiveContactGroups(Painter):
    @property
    def ident(self) -> str:
        return "event_effective_contact_groups"

    def title(self, cell):
        return _("Contact groups effective (host or rule contact groups)")

    def short_title(self, cell):
        return _("Contact groups")

    @property
    def columns(self):
        return [
            "event_contact_groups",
            "event_contact_groups_precedence",
            "host_contact_groups",
        ]

    def render(self, row, cell):
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


@painter_registry.register
class PainterHistoryLine(Painter):
    @property
    def ident(self) -> str:
        return "history_line"

    def title(self, cell):
        return _("Line number in log file")

    def short_title(self, cell):
        return _("Line")

    @property
    def columns(self):
        return ["history_line"]

    def render(self, row, cell):
        return ("number", "%s" % row["history_line"])


@painter_registry.register
class PainterHistoryTime(Painter):
    @property
    def ident(self) -> str:
        return "history_time"

    def title(self, cell):
        return _("Time of entry in logfile")

    def short_title(self, cell):
        return _("Time")

    @property
    def columns(self):
        return ["history_time"]

    @property
    def painter_options(self):
        return ["ts_format", "ts_date"]

    def render(self, row, cell):
        return paint_age(row["history_time"], True, True)


@painter_registry.register
class PainterHistoryWhat(Painter):
    @property
    def ident(self) -> str:
        return "history_what"

    def title(self, cell):
        return _("Type of event action")

    def short_title(self, cell):
        return _("Action")

    @property
    def columns(self):
        return ["history_what"]

    def render(self, row, cell):
        what = row["history_what"]
        return "", HTMLWriter.render_span(what, title=str(mkeventd.action_whats[what]))


@painter_registry.register
class PainterHistoryWhatExplained(Painter):
    @property
    def ident(self) -> str:
        return "history_what_explained"

    def title(self, cell):
        return _("Explanation for event action")

    @property
    def columns(self):
        return ["history_what"]

    def render(self, row, cell):
        return ("", mkeventd.action_whats[row["history_what"]])


@painter_registry.register
class PainterHistoryWho(Painter):
    @property
    def ident(self) -> str:
        return "history_who"

    def title(self, cell):
        return _("User who performed action")

    def short_title(self, cell):
        return _("Who")

    @property
    def columns(self):
        return ["history_who"]

    def render(self, row, cell):
        return ("", row["history_who"])


@painter_registry.register
class PainterHistoryAddinfo(Painter):
    @property
    def ident(self) -> str:
        return "history_addinfo"

    def title(self, cell):
        return _("Additional information")

    def short_title(self, cell):
        return _("Info")

    @property
    def columns(self):
        return ["history_addinfo"]

    def render(self, row, cell):
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

PermissionECUpdateEvent = permission_registry.register(
    Permission(
        section=mkeventd.PermissionSectionEventConsole,
        name="update",
        title=_l("Update an event"),
        description=_l("Needed for acknowledging and changing the comment and contact of an event"),
        defaults=["user", "admin"],
    )
)

# Sub-Permissions for Changing Comment, Contact and Acknowledgement
permission_registry.register(
    Permission(
        section=mkeventd.PermissionSectionEventConsole,
        name="update_comment",
        title=_l("Update an event: change comment"),
        description=_l("Needed for changing a comment when updating an event"),
        defaults=["user", "admin"],
    )
)

# Sub-Permissions for Changing Comment, Contact and Acknowledgement
permission_registry.register(
    Permission(
        section=mkeventd.PermissionSectionEventConsole,
        name="update_contact",
        title=_l("Update an event: change contact"),
        description=_l("Needed for changing a contact when updating an event"),
        defaults=["user", "admin"],
    )
)


class ECCommand(Command):
    @property
    def tables(self):
        return ["event"]

    def executor(self, command: CommandSpec, site: Optional[SiteId]) -> None:
        # We only get CommandSpecWithoutSite here. Can be cleaned up once we have a dedicated
        # object type for the command
        assert isinstance(command, str)
        mkeventd.execute_command(command, site=site)


@command_registry.register
class CommandECUpdateEvent(ECCommand):
    @property
    def ident(self) -> str:
        return "ec_update_event"

    @property
    def title(self) -> str:
        return _("Update & acknowledge")

    @property
    def permission(self):
        return PermissionECUpdateEvent

    def user_dialog_suffix(self, title: str, len_action_rows: int, cmdtag: str) -> str:
        return title + _(" the following %d Event Console %s") % (
            len_action_rows,
            ungettext("event", "events", len_action_rows),
        )

    def render(self, what):
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
        html.button("_mkeventd_update", _("Update"))

    def _action(
        self, cmdtag: str, spec: str, row: Row, row_index: int, num_rows: int
    ) -> CommandActionResult:
        if request.var("_mkeventd_update"):
            if user.may("mkeventd.update_comment"):
                comment = (
                    request.get_str_input_mandatory("_mkeventd_comment").strip().replace(";", ",")
                )
            else:
                comment = ""
            if user.may("mkeventd.update_contact"):
                contact = (
                    request.get_str_input_mandatory("_mkeventd_contact").strip().replace(":", ",")
                )
            else:
                contact = ""
            ack = html.get_checkbox("_mkeventd_acknowledge")
            return (
                "UPDATE;%s;%s;%s;%s;%s"
                % (
                    row["event_id"],
                    user.id,
                    ack and 1 or 0,
                    comment,
                    contact,
                ),
                _("update"),
            )
        return None


PermissionECChangeEventState = permission_registry.register(
    Permission(
        section=mkeventd.PermissionSectionEventConsole,
        name="changestate",
        title=_l("Change event state"),
        description=_l(
            "This permission allows to change the state classification of an event "
            "(e.g. from CRIT to WARN)."
        ),
        defaults=["user", "admin"],
    )
)


@command_registry.register
class CommandECChangeState(ECCommand):
    @property
    def ident(self) -> str:
        return "ec_change_state"

    @property
    def title(self) -> str:
        return _("Change state")

    @property
    def permission(self):
        return PermissionECChangeEventState

    def user_dialog_suffix(self, title: str, len_action_rows: int, cmdtag: str) -> str:
        return title + _(" of the following %d Event Console %s") % (
            len_action_rows,
            ungettext("event", "events", len_action_rows),
        )

    def render(self, what):
        html.button("_mkeventd_changestate", _("Change Event state to:"))
        html.nbsp()
        MonitoringState().render_input("_mkeventd_state", 2)

    def _action(
        self, cmdtag: str, spec: str, row: Row, row_index: int, num_rows: int
    ) -> CommandActionResult:
        if request.var("_mkeventd_changestate"):
            state = MonitoringState().from_html_vars("_mkeventd_state")
            return "CHANGESTATE;%s;%s;%s" % (row["event_id"], user.id, state), _("change the state")
        return None


PermissionECCustomActions = permission_registry.register(
    Permission(
        section=mkeventd.PermissionSectionEventConsole,
        name="actions",
        title=_l("Perform custom action"),
        description=_l(
            "This permission is needed for performing the configured actions "
            "(execution of scripts and sending emails)."
        ),
        defaults=["user", "admin"],
    )
)


@command_registry.register
class CommandECCustomAction(ECCommand):
    @property
    def ident(self) -> str:
        return "ec_custom_actions"

    @property
    def title(self) -> str:
        return _("Custom action")

    @property
    def permission(self):
        return PermissionECCustomActions

    def user_dialog_suffix(self, title: str, len_action_rows: int, cmdtag: str) -> str:
        return title + _(" for the following %d Event Console  %s") % (
            len_action_rows,
            ungettext("event", "events", len_action_rows),
        )

    def render(self, what):
        for action_id, title in mkeventd.action_choices(omit_hidden=True):
            html.button("_action_" + action_id, title)
            html.br()

    def _action(
        self, cmdtag: str, spec: str, row: Row, row_index: int, num_rows: int
    ) -> CommandActionResult:
        for action_id, title in mkeventd.action_choices(omit_hidden=True):
            if request.var("_action_" + action_id):
                title = _('execute the action "%s"') % title
                return "ACTION;%s;%s;%s" % (row["event_id"], user.id, action_id), title
        return None


PermissionECArchiveEvent = permission_registry.register(
    Permission(
        section=mkeventd.PermissionSectionEventConsole,
        name="delete",
        title=_l("Archive an event"),
        description=_l("Finally archive an event without any further action"),
        defaults=["user", "admin"],
    )
)


@command_registry.register
class CommandECArchiveEvent(ECCommand):
    @property
    def ident(self) -> str:
        return "ec_archive_event"

    @property
    def title(self) -> str:
        return _("Archive event")

    @property
    def permission(self):
        return PermissionECArchiveEvent

    def user_dialog_suffix(self, title: str, len_action_rows: int, cmdtag: str) -> str:
        return title + _(" the following %d Event Console %s") % (
            len_action_rows,
            ungettext("event", "events", len_action_rows),
        )

    def render(self, what):
        html.button("_delete_event", _("Archive Event"))

    def _action(
        self, cmdtag: str, spec: str, row: Row, row_index: int, num_rows: int
    ) -> CommandActionResult:
        if request.var("_delete_event"):
            command = "DELETE;%s;%s" % (row["event_id"], user.id)
            title = _("<b>archive</b>")
            return command, title
        return None


PermissionECArchiveEventsOfHost = permission_registry.register(
    Permission(
        section=mkeventd.PermissionSectionEventConsole,
        name="archive_events_of_hosts",
        title=_l("Archive events of hosts"),
        description=_l("Archive all open events of all hosts shown in host views"),
        defaults=["user", "admin"],
    )
)


@command_registry.register
class CommandECArchiveEventsOfHost(ECCommand):
    @property
    def ident(self) -> str:
        return "ec_archive_events_of_host"

    @property
    def title(self) -> str:
        return _("Archive events of hosts")

    @property
    def permission(self):
        return PermissionECArchiveEventsOfHost

    @property
    def tables(self):
        return ["service"]

    def render(self, what):
        html.help(
            _(
                "Note: With this command you can archive all events of one host. "
                'Needs a rule "Check event state in Event Console" to be '
                "configured."
            )
        )
        html.button("_archive_events_of_hosts", _("Archive events"), cssclass="hot")

    def _action(
        self, cmdtag: str, spec: str, row: Row, row_index: int, num_rows: int
    ) -> CommandActionResult:
        if request.var("_archive_events_of_hosts"):
            if cmdtag == "HOST":
                tag: Optional[str] = "host"
            elif cmdtag == "SVC":
                tag = "service"
            else:
                tag = None

            commands = []
            if tag and row.get("%s_check_command" % tag, "").startswith("check_mk_active-mkevents"):
                data = sites.live().query(
                    "GET eventconsoleevents\n"
                    + "Columns: event_id\n"
                    + "Filter: host_name = %s" % row["host_name"]
                )
                events = ",".join([entry[0] for entry in data])
                commands = ["DELETE;%s;%s" % (events, user.id)]

            return commands, "<b>archive all events</b> of"
        return None


# .
#   .--Sorters-------------------------------------------------------------.
#   |                  ____             _                                  |
#   |                 / ___|  ___  _ __| |_ ___ _ __ ___                   |
#   |                 \___ \ / _ \| '__| __/ _ \ '__/ __|                  |
#   |                  ___) | (_) | |  | ||  __/ |  \__ \                  |
#   |                 |____/ \___/|_|   \__\___|_|  |___/                  |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def cmp_simple_state(column, ra, rb):
    a = ra.get(column, -1)
    b = rb.get(column, -1)
    if a == 3:
        a = 1.5
    if b == 3:
        b = 1.5
    return (a > b) - (a < b)


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

# .
#   .--Views---------------------------------------------------------------.
#   |                    __     ___                                        |
#   |                    \ \   / (_) _____      _____                      |
#   |                     \ \ / /| |/ _ \ \ /\ / / __|                     |
#   |                      \ V / | |  __/\ V  V /\__ \                     |
#   |                       \_/  |_|\___| \_/\_/ |___/                     |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def mkeventd_view(d):
    x = {
        "topic": "events",
        "browser_reload": 60,
        "column_headers": "pergroup",
        "icon": "event_console",
        "mobile": False,
        "hidden": False,
        "mustsearch": False,
        "group_painters": [],
        "num_columns": 1,
        "hidebutton": False,
        "play_sounds": False,
        "public": True,
        "sorters": [],
        "user_sortable": "on",
        "show_filters": [],
        "hard_filters": [],
        "hide_filters": [],
        "hard_filtervars": [],
    }
    x.update(d)
    return x


# Table of all open events
multisite_builtin_views["ec_events"] = mkeventd_view(
    {
        "sort_index": 10,
        "title": _("Events"),
        "description": _("Table of all currently open events (handled and unhandled)"),
        "datasource": "mkeventd_events",
        "layout": "table",
        "painters": [
            ("event_id", "ec_event", None),
            ("event_icons", None, None),
            ("event_state", None, None),
            ("event_sl", None, None),
            ("event_host", "ec_events_of_host", None),
            ("event_rule_id", None, None),
            ("event_application", None, None),
            ("event_text", None, None),
            ("event_last", None, None),
            ("event_count", None, None),
        ],
        "show_filters": [
            "event_id",
            "event_rule_id",
            "event_text",
            "event_application",
            "event_contact",
            "event_comment",
            "event_host_regex",
            "event_ipaddress",
            "event_count",
            "event_phase",
            "event_state",
            "event_first",
            "event_last",
            "event_priority",
            "event_facility",
            "event_sl",
            "event_sl_max",
            "event_host_in_downtime",
            "hostregex",
            "siteopt",
        ],
        "hard_filtervars": [
            ("event_phase_open", "on"),
            ("event_phase_ack", "on"),
            ("event_phase_counting", ""),
            ("event_phase_delayed", ""),
        ],
        "sorters": [("event_last", False)],
        "is_show_more": True,
    }
)

multisite_builtin_views["ec_events_of_monhost"] = mkeventd_view(
    {
        "title": _("Events of monitored host"),
        "description": _("Currently open events of a host that is monitored"),
        "datasource": "mkeventd_events",
        "layout": "table",
        "hidden": True,
        "painters": [
            ("event_id", "ec_event", None),
            ("event_icons", None, None),
            ("event_state", None, None),
            ("event_sl", None, None),
            ("event_rule_id", None, None),
            ("event_application", None, None),
            ("event_text", None, None),
            ("event_last", None, None),
            ("event_count", None, None),
        ],
        "show_filters": [
            "event_id",
            "event_rule_id",
            "event_text",
            "event_application",
            "event_contact",
            "event_comment",
            "event_count",
            "event_phase",
            "event_state",
            "event_first",
            "event_last",
            "event_priority",
            "event_facility",
            "event_sl",
            "event_sl_max",
            "event_host_in_downtime",
        ],
        "hide_filters": [
            "siteopt",
            "host",
        ],
        "sorters": [("event_last", False)],
    }
)
multisite_builtin_views["ec_events_of_host"] = mkeventd_view(
    {
        "title": _("Events of host"),
        "description": _("Currently open events of one specific host"),
        "datasource": "mkeventd_events",
        "layout": "table",
        "hidden": True,
        "painters": [
            ("event_id", "ec_event", None),
            ("event_icons", None, None),
            ("event_state", None, None),
            ("event_sl", None, None),
            ("event_rule_id", None, None),
            ("event_application", None, None),
            ("event_text", None, None),
            ("event_last", None, None),
            ("event_count", None, None),
        ],
        "show_filters": [
            "event_id",
            "event_rule_id",
            "event_text",
            "event_application",
            "event_contact",
            "event_comment",
            "event_count",
            "event_phase",
            "event_state",
            "event_first",
            "event_last",
            "event_priority",
            "event_facility",
            "event_sl",
            "event_sl_max",
            "event_host_in_downtime",
        ],
        "hide_filters": [
            "siteopt",
            "event_host",
        ],
        "sorters": [("event_last", False)],
    }
)

multisite_builtin_views["ec_event"] = mkeventd_view(
    {
        "title": _("Event details"),
        "description": _("Details about one event"),
        "datasource": "mkeventd_events",
        "layout": "dataset",
        "hidden": True,
        "browser_reload": 0,
        "hide_filters": [
            "event_id",
        ],
        "painters": [
            ("event_state", None, None),
            ("event_host", None, None),
            ("event_ipaddress", None, None),
            ("foobar", None, None),
            ("alias", "hoststatus", None),
            ("host_contacts", None, None),
            ("host_icons", None, None),
            ("event_text", None, None),
            ("event_match_groups", None, None),
            ("event_comment", None, None),
            ("event_owner", None, None),
            ("event_first", None, None),
            ("event_last", None, None),
            ("event_id", None, None),
            ("event_icons", None, None),
            ("event_count", None, None),
            ("event_sl", None, None),
            ("event_contact", None, None),
            ("event_effective_contact_groups", None, None),
            ("event_application", None, None),
            ("event_pid", None, None),
            ("event_priority", None, None),
            ("event_facility", None, None),
            ("event_rule_id", None, None),
            ("event_phase", None, None),
            ("host_services", None, None),
        ],
    }
)

multisite_builtin_views["ec_history_recent"] = mkeventd_view(
    {
        "sort_index": 20,
        "title": _("Recent event history"),
        "description": _(
            "Information about events and actions on events during the recent 24 hours."
        ),
        "icon": {"icon": "event_console", "emblem": "time"},
        "datasource": "mkeventd_history",
        "layout": "table",
        "painters": [
            ("history_time", None, None),
            ("event_id", "ec_historyentry", None),
            ("history_who", None, None),
            ("history_what", None, None),
            ("event_history_icons", None, None),
            ("event_state", None, None),
            ("event_phase", None, None),
            ("event_sl", None, None),
            ("event_host", "ec_history_of_host", None),
            ("event_rule_id", None, None),
            ("event_application", None, None),
            ("event_text", None, None),
            ("event_last", None, None),
            ("event_count", None, None),
        ],
        "show_filters": [
            "event_id",
            "event_rule_id",
            "event_text",
            "event_application",
            "event_contact",
            "event_comment",
            "event_host_regex",
            "event_ipaddress",
            "event_count",
            "event_phase",
            "event_state",
            "event_first",
            "event_last",
            "event_priority",
            "event_facility",
            "event_sl",
            "event_sl_max",
            "event_host_in_downtime",
            "history_time",
            "history_who",
            "history_what",
            "host_state_type",
            "hostregex",
            "siteopt",
        ],
        "hard_filtervars": [
            ("history_time_from", "1"),
            ("history_time_from_range", "86400"),
        ],
        "sorters": [
            ("history_time", True),
            ("history_line", True),
        ],
        "is_show_more": True,
    }
)

multisite_builtin_views["ec_historyentry"] = mkeventd_view(
    {
        "title": _("Event history entry"),
        "description": _("Details about a historical event history entry"),
        "datasource": "mkeventd_history",
        "layout": "dataset",
        "hidden": True,
        "browser_reload": 0,
        "hide_filters": [
            "event_id",
            "history_line",
        ],
        "painters": [
            ("history_time", None, None),
            ("history_line", None, None),
            ("history_what", None, None),
            ("history_what_explained", None, None),
            ("history_who", None, None),
            ("history_addinfo", None, None),
            ("event_state", None, None),
            ("event_host", "ec_history_of_host", None),
            ("event_ipaddress", None, None),
            ("event_text", None, None),
            ("event_match_groups", None, None),
            ("event_comment", None, None),
            ("event_owner", None, None),
            ("event_first", None, None),
            ("event_last", None, None),
            ("event_id", "ec_history_of_event", None),
            ("event_history_icons", None, None),
            ("event_count", None, None),
            ("event_sl", None, None),
            ("event_contact", None, None),
            ("event_effective_contact_groups", None, None),
            ("event_application", None, None),
            ("event_pid", None, None),
            ("event_priority", None, None),
            ("event_facility", None, None),
            ("event_rule_id", None, None),
            ("event_phase", None, None),
        ],
    }
)

multisite_builtin_views["ec_history_of_event"] = mkeventd_view(
    {
        "title": _("History of Event"),
        "description": _("History entries of one specific event"),
        "datasource": "mkeventd_history",
        "layout": "table",
        "columns": 1,
        "hidden": True,
        "browser_reload": 0,
        "hide_filters": [
            "event_id",
        ],
        "painters": [
            ("history_time", None, None),
            ("history_line", "ec_historyentry", None),
            ("history_what", None, None),
            ("history_what_explained", None, None),
            ("history_who", None, None),
            ("event_state", None, None),
            ("event_host", None, None),
            ("event_application", None, None),
            ("event_text", None, None),
            ("event_sl", None, None),
            ("event_priority", None, None),
            ("event_facility", None, None),
            ("event_phase", None, None),
            ("event_count", None, None),
        ],
        "sorters": [
            ("history_time", True),
            ("history_line", True),
        ],
    }
)

multisite_builtin_views["ec_history_of_host"] = mkeventd_view(
    {
        "title": _("Event history of host"),
        "description": _("History entries of one specific host"),
        "datasource": "mkeventd_history",
        "layout": "table",
        "columns": 1,
        "hidden": True,
        "browser_reload": 0,
        "hide_filters": [
            "event_host",
        ],
        "show_filters": [
            "event_id",
            "event_rule_id",
            "event_text",
            "event_application",
            "event_contact",
            "event_comment",
            "event_count",
            "event_phase",
            "event_state",
            "event_first",
            "event_last",
            "event_priority",
            "event_facility",
            "event_sl",
            "event_sl_max",
            "event_host_in_downtime",
            "history_time",
            "history_who",
            "history_what",
        ],
        "painters": [
            ("history_time", None, None),
            ("event_id", "ec_history_of_event", None),
            ("history_line", "ec_historyentry", None),
            ("history_what", None, None),
            ("history_what_explained", None, None),
            ("history_who", None, None),
            ("event_state", None, None),
            ("event_host", None, None),
            ("event_ipaddress", None, None),
            ("event_application", None, None),
            ("event_text", None, None),
            ("event_sl", None, None),
            ("event_priority", None, None),
            ("event_facility", None, None),
            ("event_phase", None, None),
            ("event_count", None, None),
        ],
        "sorters": [
            ("history_time", True),
            ("history_line", True),
        ],
    }
)

multisite_builtin_views["ec_event_mobile"] = {
    "browser_reload": 0,
    "column_headers": "pergroup",
    "context": {},
    "datasource": "mkeventd_events",
    "description": "Details about one event\n",
    "group_painters": [],
    "hidden": True,
    "hidebutton": False,
    "icon": "event",
    "layout": "mobiledataset",
    "mobile": True,
    "name": "ec_event_mobile",
    "num_columns": 1,
    "painters": [
        ("event_state", None, None),
        ("event_host", None, None),
        ("event_ipaddress", None, None),
        ("host_address", "hoststatus", None),
        ("host_contacts", None, None),
        ("host_icons", None, None),
        ("event_text", None, None),
        ("event_comment", None, None),
        ("event_owner", None, None),
        ("event_first", None, None),
        ("event_last", None, None),
        ("event_id", None, None),
        ("event_icons", None, None),
        ("event_count", None, None),
        ("event_sl", None, None),
        ("event_contact", None, None),
        ("event_effective_contact_groups", None, None),
        ("event_application", None, None),
        ("event_pid", None, None),
        ("event_priority", None, None),
        ("event_facility", None, None),
        ("event_rule_id", None, None),
        ("event_phase", None, None),
        ("host_services", None, None),
    ],
    "public": True,
    "single_infos": ["event"],
    "sorters": [],
    "title": "Event details",
    "topic": "events",
    "user_sortable": True,
}

multisite_builtin_views["ec_events_mobile"] = {
    "browser_reload": 60,
    "column_headers": "pergroup",
    "context": {
        "event_application": {"event_application": ""},
        "event_comment": {"event_comment": ""},
        "event_contact": {"event_contact": ""},
        "event_count": {"event_count_from": "", "event_count_to": ""},
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
    "description": "Table of all currently open events (handled and unhandled)\n",
    "group_painters": [],
    "hidden": False,
    "hidebutton": False,
    "icon": "event",
    "layout": "mobilelist",
    "mobile": True,
    "name": "ec_events_mobile",
    "num_columns": 1,
    "owner": "cmkadmin",
    "painters": [
        ("event_id", "ec_event_mobile", None),
        ("event_state", None, None),
        ("event_host", None, None),
        ("event_application", None, None),
        ("event_text", None, None),
        ("event_last", None, None),
    ],
    "public": True,
    "single_infos": [],
    "sorters": [("event_last", False)],
    "title": "Events",
    "topic": "events",
    "user_sortable": True,
}
