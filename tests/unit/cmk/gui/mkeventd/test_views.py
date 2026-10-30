#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from collections.abc import Sequence
from dataclasses import replace
from functools import cmp_to_key, partial
from html import unescape
from urllib.parse import parse_qsl, urlsplit

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.ccc.user import UserId
from cmk.gui.config import Config
from cmk.gui.data_source import row_id
from cmk.gui.http import request
from cmk.gui.logged_in import LoggedInUser, user, UserDefaultConfig
from cmk.gui.mkeventd.views import (
    cmp_simple_state,
    CommandECArchiveEvent,
    CommandECArchiveEventsOfHost,
    CommandECChangeState,
    CommandECCustomAction,
    CommandECUpdateEvent,
    DataSourceECEventHistory,
    DataSourceECEvents,
    make_event_application_painter,
    make_event_comment_painter,
    make_event_contact_groups_painter,
    make_event_contact_painter,
    make_event_count_painter,
    make_event_effective_contact_groups_painter,
    make_event_facility_painter,
    make_event_first_painter,
    make_event_history_icons_painter,
    make_event_host_in_downtime_painter,
    make_event_host_painter,
    make_event_icons_painter,
    make_event_id_painter,
    make_event_ipaddress_painter,
    make_event_last_painter,
    make_event_match_groups_painter,
    make_event_owner_painter,
    make_event_phase_painter,
    make_event_pid_painter,
    make_event_priority_painter,
    make_event_rule_id_painter,
    make_event_sl_painter,
    make_event_state_painter,
    make_event_text_painter,
    make_history_addinfo_painter,
    make_history_line_painter,
    make_history_time_painter,
    make_history_what_explained_painter,
    make_history_what_painter,
    make_history_who_painter,
    make_host_servicelevel_painter,
    make_svc_servicelevel_painter,
    SorterServicelevel,
)
from cmk.gui.painter import Cell, InternalPainter, PainterContext
from cmk.gui.type_defs import ColumnSpec, Row, Rows, VisualLinkSpec
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.valuespec import DropdownChoice
from cmk.gui.view_utils import CellSpec
from cmk.gui.views.command import Command, CommandActionResult, CommandSpec
from cmk.gui.views.command.base import CommandConfirmDialogOptions
from cmk.gui.views.sorter import Sorter, sorter_registry
from cmk.livestatus_client import Command as LivestatusCommand
from cmk.livestatus_client import (
    ECAction,
    ECChangeState,
    ECDelete,
    ECDeleteEventsOfHost,
    ECUpdate,
)
from cmk.livestatus_client.testing import MockLiveStatusConnection
from cmk.web.utils.html import HTML
from cmk.web.utils.request_cache import RequestCache
from tests.testlib.unit.gui.global_settings import logged_in
from tests.unit.cmk.gui.helpers.painter_context_test_helper import make_painter_context
from tests.unit.cmk.gui.helpers.setup_mode_test_helper import set_request_vars

_PERMISSIONS = UserPermissions({}, {}, {}, [])
_NOBODY = LoggedInUser(
    None,
    _PERMISSIONS,
    defaults=UserDefaultConfig(users={}, default_language="en", default_show_mode="default"),
)


def _paint(
    painter: InternalPainter,
    row: Row,
    *,
    acting_user: LoggedInUser = _NOBODY,
    context: PainterContext | None = None,
    link_spec: VisualLinkSpec | None = None,
) -> CellSpec:
    context = context or make_painter_context(_PERMISSIONS)
    cell = Cell(
        ColumnSpec(name=painter.ident, link_spec=link_spec),
        None,
        {painter.ident: painter},
        context,
        None,
    )
    return painter.render(row, cell, acting_user, context)


def _link_target(content: object) -> tuple[str, dict[str, str]]:
    match = re.search(r'href="([^"]*)"', str(content))
    assert match is not None, f"no link in {content!r}"
    url = urlsplit(unescape(match.group(1)))
    return url.path, dict(parse_qsl(url.query))


# The contact group create_and_destroy_user() puts the user of the with_user fixture into
_GROUP_OF_USER = "all"


def _event(**columns: object) -> dict[str, object]:
    return {
        "event_id": 1,
        "event_host": "10.0.0.1",
        "event_contact_groups": [],
        "host_name": "myhost",
        "host_alias": "My host",
        "host_contact_groups": [_GROUP_OF_USER],
        "host_has_been_checked": 1,
        "host_state": 1,
    } | columns


def _query(
    mock_livestatus: MockLiveStatusConnection,
    user_id: UserId,
    permissions: tuple[str, ...],
    events: list[dict[str, object]],
    datasource: DataSourceECEvents | DataSourceECEventHistory | None = None,
) -> Rows:
    datasource = datasource or DataSourceECEvents()
    table = datasource.table
    mock_livestatus.set_sites(["NO_SITE"])
    mock_livestatus.add_table(table.table_name, events)
    mock_livestatus.expect_query(f"GET {table.table_name}", match_type="loose")
    with mock_livestatus(), logged_in(user_id, *permissions):
        result = table.query(
            datasource, [], ["event_id", "host_alias", "host_name"], {}, "", None, None, []
        )
    assert isinstance(result, list)
    return result


@pytest.mark.usefixtures("request_context")
def test_no_events_give_no_rows(
    mock_livestatus: MockLiveStatusConnection, with_user: tuple[UserId, str]
) -> None:
    assert _query(mock_livestatus, with_user[0], ("mkeventd.seeall",), []) == []


@pytest.mark.usefixtures("request_context")
def test_a_contact_of_the_host_sees_its_details(
    mock_livestatus: MockLiveStatusConnection, with_user: tuple[UserId, str]
) -> None:
    rows = _query(mock_livestatus, with_user[0], (), [_event(host_contact_groups=[_GROUP_OF_USER])])

    assert rows[0]["host_alias"] == "My host"


@pytest.mark.usefixtures("request_context")
def test_a_user_who_may_see_all_events_sees_all_host_details(
    mock_livestatus: MockLiveStatusConnection, with_user: tuple[UserId, str]
) -> None:
    rows = _query(
        mock_livestatus,
        with_user[0],
        ("mkeventd.seeall",),
        [_event(host_contact_groups=["admins"])],
    )

    assert rows[0]["host_alias"] == "My host"


@pytest.mark.usefixtures("request_context")
def test_a_user_who_is_no_contact_of_the_host_sees_the_event_without_host_details(
    mock_livestatus: MockLiveStatusConnection, with_user: tuple[UserId, str]
) -> None:
    rows = _query(
        mock_livestatus,
        with_user[0],
        (),
        [_event(host_contact_groups=["admins"], event_contact_groups=[_GROUP_OF_USER])],
    )

    assert {
        column: rows[0][column] for column in ("host_alias", "host_contact_groups", "host_state")
    } == {"host_alias": "", "host_contact_groups": [], "host_state": 0}


@pytest.mark.usefixtures("request_context")
def test_an_event_unrelated_to_a_monitored_host_is_named_after_its_event_host(
    mock_livestatus: MockLiveStatusConnection, with_user: tuple[UserId, str]
) -> None:
    rows = _query(mock_livestatus, with_user[0], ("mkeventd.seeall",), [_event(host_name="")])

    assert (rows[0]["host_name"], rows[0]["event_is_unrelated"]) == ("10.0.0.1", True)


@pytest.mark.parametrize(
    "datasource",
    [
        pytest.param(DataSourceECEvents(), id="events"),
        pytest.param(DataSourceECEventHistory(), id="history"),
    ],
)
@pytest.mark.usefixtures("request_context")
def test_events_unrelated_to_monitored_hosts_are_hidden_without_permission(
    mock_livestatus: MockLiveStatusConnection,
    with_user: tuple[UserId, str],
    datasource: DataSourceECEvents | DataSourceECEventHistory,
) -> None:
    rows = _query(mock_livestatus, with_user[0], (), [_event(host_name="")], datasource)

    assert rows == []


@pytest.mark.usefixtures("request_context")
def test_events_unrelated_to_monitored_hosts_are_shown_with_permission(
    mock_livestatus: MockLiveStatusConnection, with_user: tuple[UserId, str]
) -> None:
    rows = _query(mock_livestatus, with_user[0], ("mkeventd.seeunrelated",), [_event(host_name="")])

    assert [row["event_id"] for row in rows] == [1]


@pytest.mark.usefixtures("request_context")
def test_unrelated_events_with_contact_groups_from_their_rule_are_shown(
    mock_livestatus: MockLiveStatusConnection, with_user: tuple[UserId, str]
) -> None:
    rows = _query(
        mock_livestatus,
        with_user[0],
        (),
        [_event(host_name="", event_contact_groups=[_GROUP_OF_USER])],
    )

    assert [row["event_id"] for row in rows] == [1]


# Trivial painters, but views fetch only the columns a painter declares, so this checks that
# each one renders the column it declares. A mismatch would only crash in a running site.
@pytest.mark.parametrize(
    "painter, value, expected",
    [
        pytest.param(make_event_id_painter(), 42, ("number", "42"), id="event id"),
        pytest.param(make_event_count_painter(), 3, ("number", "3"), id="count"),
        pytest.param(make_event_comment_painter(), "known", ("", "known"), id="comment"),
        pytest.param(make_event_ipaddress_painter(), "10.0.0.1", ("", "10.0.0.1"), id="ip address"),
        pytest.param(make_event_owner_painter(), "harry", ("", "harry"), id="owner"),
        pytest.param(make_event_contact_painter(), "sally", ("", "sally"), id="contact"),
        pytest.param(make_event_application_painter(), "sshd", ("", "sshd"), id="application"),
        pytest.param(make_event_pid_painter(), 4711, ("", "4711"), id="pid"),
        pytest.param(make_history_line_painter(), 7, ("number", "7"), id="history line"),
        pytest.param(make_history_who_painter(), "harry", ("", "harry"), id="history who"),
        pytest.param(make_history_addinfo_painter(), "more", ("", "more"), id="history info"),
    ],
)
def test_a_plain_event_column_is_shown_as_it_is(
    painter: InternalPainter, value: object, expected: CellSpec
) -> None:
    assert _paint(painter, dict.fromkeys(painter.columns, value)) == expected


@pytest.mark.parametrize(
    "painter, what",
    [
        pytest.param(make_svc_servicelevel_painter(), "service", id="service"),
        pytest.param(make_host_servicelevel_painter(), "host", id="host"),
    ],
)
def test_the_service_level_of_a_monitored_object_is_shown_by_name(
    painter: InternalPainter, what: str
) -> None:
    row = {f"{what}_custom_variable_names": ["EC_SL"], f"{what}_custom_variable_values": ["20"]}

    assert _paint(painter, row) == ("EC_SL", "Gold")


def test_the_event_text_is_escaped() -> None:
    _css, content = _paint(make_event_text_painter(), {"event_text": "<script>"})

    assert str(content) == "&lt;script&gt;"


def test_the_event_text_breaks_lines_at_the_line_separator() -> None:
    _css, content = _paint(make_event_text_painter(), {"event_text": "first\x01second"})

    assert str(content) == "first<br>second"


def test_match_groups_are_shown_one_after_another() -> None:
    assert _paint(make_event_match_groups_painter(), {"event_match_groups": ["a", "b"]}) == (
        "matchgroups",
        HTML.without_escaping("<span>a</span><span>b</span>"),
    )


def test_no_match_groups_show_nothing() -> None:
    assert _paint(make_event_match_groups_painter(), {"event_match_groups": []}) == (
        "",
        HTML.empty(),
    )


@pytest.mark.parametrize(
    "painter, column",
    [
        pytest.param(make_event_first_painter(), "event_first", id="first"),
        pytest.param(make_event_last_painter(), "event_last", id="last"),
        pytest.param(make_history_time_painter(), "history_time", id="history time"),
    ],
)
def test_event_times_follow_the_timestamp_format_option(
    painter: InternalPainter, column: str
) -> None:
    context = make_painter_context(_PERMISSIONS)
    context.request.set_var("po_ts_format", "epoch")

    assert _paint(painter, {column: 1_700_000_000}, context=context) == ("", "1700000000")


@pytest.mark.parametrize(
    "service_level, expected",
    [
        pytest.param(20, "Gold", id="configured"),
        pytest.param(42, "42", id="unknown"),
    ],
)
def test_the_service_level_of_an_event_is_shown_by_name_if_known(
    service_level: int, expected: str
) -> None:
    assert _paint(make_event_sl_painter(), {"event_sl": service_level}) == ("", expected)


@pytest.mark.usefixtures("request_context")
def test_the_host_of_an_event_links_to_its_events_by_default() -> None:
    _css, content = _paint(
        make_event_host_painter(), {"event_host": "10.0.0.1", "host_name": "myhost"}
    )

    assert _link_target(content) == (
        "view.py",
        {"view_name": "ec_events_of_host", "host": "myhost", "event_host": "10.0.0.1"},
    )


@pytest.mark.usefixtures("request_context")
def test_the_host_of_an_event_links_to_the_configured_view() -> None:
    _css, content = _paint(
        make_event_host_painter(),
        {"event_host": "10.0.0.1", "host_name": "myhost"},
        link_spec=VisualLinkSpec(type_name="views", name="ec_history_of_host"),
    )

    assert _link_target(content) == (
        "view.py",
        {"view_name": "ec_history_of_host", "host": "myhost", "event_host": "10.0.0.1"},
    )


@pytest.mark.usefixtures("request_context")
def test_the_host_of_an_event_links_to_the_configured_dashboard() -> None:
    _css, content = _paint(
        make_event_host_painter(),
        {"event_host": "10.0.0.1", "host_name": "myhost"},
        link_spec=VisualLinkSpec(type_name="dashboards", name="host_overview"),
    )

    assert _link_target(content) == (
        "dashboard.py",
        {"name": "host_overview", "host": "myhost", "event_host": "10.0.0.1"},
    )


def test_an_event_created_during_a_host_downtime_is_flagged() -> None:
    assert _paint(make_event_host_in_downtime_painter(), {"event_host_in_downtime": 1}) == (
        "badflag",
        HTML.without_escaping("<span>yes</span>"),
    )


def test_the_syslog_priority_is_shown_by_name() -> None:
    assert _paint(make_event_priority_painter(), {"event_priority": 2}) == ("", "crit")


def test_the_syslog_facility_is_shown_by_name() -> None:
    assert _paint(make_event_facility_painter(), {"event_facility": 1}) == ("", "user")


@pytest.mark.usefixtures("request_context")
def test_the_rule_of_an_event_links_to_its_editor_for_users_who_may_edit_rules(
    with_user: tuple[UserId, str],
) -> None:
    with logged_in(with_user[0], "mkeventd.edit"):
        _css, content = _paint(
            make_event_rule_id_painter(), {"event_rule_id": "my_rule"}, acting_user=user
        )

    assert _link_target(content) == (
        "wato.py",
        {"mode": "mkeventd_edit_rule", "rule_id": "my_rule"},
    )


@pytest.mark.usefixtures("request_context")
def test_the_rule_of_an_event_is_plain_text_for_users_who_may_not_edit_rules(
    with_user: tuple[UserId, str],
) -> None:
    with logged_in(with_user[0]):
        cell_spec = _paint(
            make_event_rule_id_painter(), {"event_rule_id": "my_rule"}, acting_user=user
        )

    assert cell_spec == ("", "my_rule")


def test_the_event_state_is_shown_by_its_short_name_and_colored() -> None:
    assert _paint(make_event_state_painter(), {"event_state": 1}) == (
        "state svcstate state1",
        HTML.without_escaping('<span class="state_rounded_fill">WARN</span>'),
    )


@pytest.mark.parametrize(
    "phase, expected",
    [
        pytest.param("open", "open", id="known"),
        pytest.param("bogus", "", id="unknown"),
    ],
)
def test_the_event_phase_is_shown_by_name_if_known(phase: str, expected: str) -> None:
    assert _paint(make_event_phase_painter(), {"event_phase": phase}) == ("", expected)


@pytest.mark.parametrize(
    "contact_groups, expected",
    [
        pytest.param(None, "", id="not fetched"),
        pytest.param([], "<i>none</i>", id="none"),
        pytest.param(["admins", "all"], "admins, all", id="some"),
    ],
)
def test_the_contact_groups_of_the_rule_are_listed(
    contact_groups: list[str] | None, expected: str
) -> None:
    assert _paint(
        make_event_contact_groups_painter(), {"event_contact_groups": contact_groups}
    ) == (
        "",
        expected,
    )


def _effective_contact_groups(
    precedence: str, host_groups: list[str] | None, rule_groups: list[str] | None
) -> CellSpec:
    return _paint(
        make_event_effective_contact_groups_painter(),
        {
            "event_contact_groups_precedence": precedence,
            "host_contact_groups": host_groups,
            "event_contact_groups": rule_groups,
        },
    )


@pytest.mark.parametrize(
    "precedence, expected",
    [
        pytest.param("host", "admins", id="host"),
        pytest.param("rule", "ops", id="rule"),
    ],
)
def test_the_effective_contact_groups_follow_the_precedence(precedence: str, expected: str) -> None:
    assert _effective_contact_groups(precedence, ["admins"], ["ops"]) == ("", expected)


def test_the_effective_contact_groups_are_sorted() -> None:
    assert _effective_contact_groups("host", ["ops", "admins"], None) == ("", "admins, ops")


def test_no_effective_contact_groups_are_marked_as_none() -> None:
    assert _effective_contact_groups("host", [], None) == (
        "",
        HTML.without_escaping("<i>none</i>"),
    )


def test_effective_contact_groups_which_were_not_fetched_show_nothing() -> None:
    assert _effective_contact_groups("rule", None, None) == ("", "")


def test_the_history_action_is_explained_on_hover() -> None:
    _css, content = _paint(make_history_what_painter(), {"history_what": "DELETE"})

    assert str(content) == '<span title="Event deleted manually by user">DELETE</span>'


def test_the_history_action_is_explained() -> None:
    assert _paint(make_history_what_explained_painter(), {"history_what": "DELETE"}) == (
        "",
        "Event deleted manually by user",
    )


def _history_icons(row: Row) -> CellSpec:
    return _paint(
        make_event_history_icons_painter(),
        {"event_phase": "open", "event_host_in_downtime": 0} | row,
    )


@pytest.mark.parametrize(
    "phase, title",
    [
        pytest.param("ack", "This event has been acknowledged.", id="acknowledged"),
        pytest.param("counting", "This event has not reached the target count yet.", id="counting"),
        pytest.param(
            "delayed",
            "The action of this event is still delayed in the hope of a cancelling event.",
            id="delayed",
        ),
    ],
)
@pytest.mark.usefixtures("request_context", "patch_theme")
def test_a_pending_event_phase_is_shown_as_icon(phase: str, title: str) -> None:
    _css, content = _history_icons({"event_phase": phase})

    assert title in str(content)


@pytest.mark.usefixtures("request_context", "patch_theme")
def test_an_event_created_during_a_host_downtime_gets_an_icon() -> None:
    _css, content = _history_icons({"event_host_in_downtime": 1})

    assert "Host in downtime during event creation" in str(content)


@pytest.mark.usefixtures("request_context", "patch_theme")
def test_an_open_event_outside_of_a_downtime_has_no_icons() -> None:
    assert _history_icons({}) == ("", "")


def _event_icons(acting_user: LoggedInUser) -> str:
    _css, content = _paint(
        make_event_icons_painter(),
        {
            "site": "local",
            "host_name": "myhost",
            "event_id": 1,
            "event_phase": "open",
            "event_host_in_downtime": 0,
        },
        acting_user=acting_user,
        context=replace(make_painter_context(_PERMISSIONS), request=request),
    )
    return str(content)


@pytest.mark.usefixtures("request_context", "patch_theme")
def test_an_open_event_offers_no_archiving_without_permission(
    with_user: tuple[UserId, str],
) -> None:
    with logged_in(with_user[0]):
        icons = _event_icons(user)

    assert "Archive this event" not in icons


@pytest.mark.usefixtures("request_context", "patch_theme")
def test_an_open_event_in_a_view_is_archived_by_its_row(
    with_user: tuple[UserId, str],
) -> None:
    set_request_vars(view_name="ec_events")

    with logged_in(with_user[0], "mkeventd.delete", "general.see_user_views", "view.ec_events"):
        icons = _event_icons(user)

    _path, variables = _link_target(icons)
    assert variables["_row_id"] == row_id(
        "mkeventd_events", {"site": "local", "host_name": "myhost", "event_id": 1}
    )


@pytest.mark.usefixtures("request_context", "patch_theme")
def test_an_open_event_in_a_dashboard_widget_is_archived_from_the_widget(
    with_user: tuple[UserId, str],
) -> None:
    set_request_vars(__view_datasource="mkeventd_events")

    with logged_in(with_user[0], "mkeventd.delete"):
        icons = _event_icons(user)

    path, _variables = _link_target(icons)
    assert path == "widget_iframe_view.py"


@pytest.mark.usefixtures("request_context", "patch_theme")
def test_a_history_entry_offers_no_archiving(with_user: tuple[UserId, str]) -> None:
    with logged_in(with_user[0], "mkeventd.delete"):
        _css, content = _paint(
            make_event_history_icons_painter(),
            {"event_phase": "open", "event_host_in_downtime": 0},
            acting_user=user,
        )

    assert "Archive this event" not in str(content)


_EVENT_ROWS: Rows = [
    {"site": "local", "host_name": "myhost", "event_id": 1},
    {"site": "local", "host_name": "myhost", "event_id": 2},
]


def _act(
    user_id: UserId, permissions: tuple[str, ...], command: Command, rows: Rows
) -> CommandActionResult:
    with logged_in(user_id, *permissions):
        return command.action("HOST", rows[0]["host_name"], rows[0], 0, rows)


def _acted(
    user_id: UserId, permissions: tuple[str, ...], command: Command, rows: Rows
) -> tuple[LivestatusCommand | Sequence[CommandSpec], CommandConfirmDialogOptions]:
    if (result := _act(user_id, permissions, command, rows)) is None:
        raise AssertionError(f"{command.ident} ignored its button")
    return result


def _render(command: Command, user_id: UserId, *permissions: str) -> str:
    with logged_in(user_id, *permissions), output_funnel.plugged():
        command.render("event")
        return "".join(output_funnel.drain())


@pytest.mark.parametrize(
    "command",
    [
        pytest.param(CommandECUpdateEvent, id="update"),
        pytest.param(CommandECChangeState, id="change state"),
        pytest.param(CommandECCustomAction, id="custom action"),
        pytest.param(CommandECArchiveEvent, id="archive"),
        pytest.param(CommandECArchiveEventsOfHost, id="archive of host"),
    ],
)
@pytest.mark.usefixtures("request_context")
def test_an_ec_command_does_nothing_unless_its_button_was_pressed(
    with_user: tuple[UserId, str], command: Command
) -> None:
    assert _act(with_user[0], (), command, _EVENT_ROWS) is None


@pytest.mark.usefixtures("request_context")
def test_updating_events_sets_comment_contact_and_acknowledgement(
    with_user: tuple[UserId, str],
) -> None:
    set_request_vars(
        _mkeventd_update="1",
        _mkeventd_comment=" known issue ",
        _mkeventd_contact=" harry ",
        _mkeventd_acknowledge="on",
    )

    command, _dialog = _acted(
        with_user[0],
        ("mkeventd.update_comment", "mkeventd.update_contact"),
        CommandECUpdateEvent,
        _EVENT_ROWS,
    )

    assert command == ECUpdate((1, 2), True, with_user[0], "known issue", "harry")


@pytest.mark.usefixtures("request_context")
def test_updating_events_replaces_the_separators_of_the_core_command(
    with_user: tuple[UserId, str],
) -> None:
    set_request_vars(_mkeventd_update="1", _mkeventd_comment="a;b", _mkeventd_contact="c:d")

    command, _dialog = _acted(
        with_user[0],
        ("mkeventd.update_comment", "mkeventd.update_contact"),
        CommandECUpdateEvent,
        _EVENT_ROWS,
    )

    assert command == ECUpdate((1, 2), None, with_user[0], "a,b", "c,d")


@pytest.mark.usefixtures("request_context")
def test_updating_events_keeps_comment_and_contact_without_permission(
    with_user: tuple[UserId, str],
) -> None:
    set_request_vars(_mkeventd_update="1", _mkeventd_comment="known", _mkeventd_contact="harry")

    command, _dialog = _acted(with_user[0], (), CommandECUpdateEvent, _EVENT_ROWS)

    assert command == ECUpdate((1, 2), None, with_user[0], "", "")


@pytest.mark.parametrize(
    "variables, title",
    [
        pytest.param({"_mkeventd_acknowledge": "on"}, "Update & acknowledge event?", id="ack"),
        pytest.param({}, "Update event?", id="no ack"),
    ],
)
@pytest.mark.usefixtures("request_context")
def test_the_update_confirmation_mentions_an_acknowledgement(
    with_user: tuple[UserId, str], variables: dict[str, str], title: str
) -> None:
    set_request_vars(_mkeventd_update="1", **variables)

    _command, dialog = _acted(with_user[0], (), CommandECUpdateEvent, _EVENT_ROWS)

    assert dialog.confirm_title == title


@pytest.mark.parametrize(
    "rows, affected",
    [
        pytest.param(_EVENT_ROWS[:1], "Affected event: 1", id="one"),
        pytest.param(_EVENT_ROWS, "Affected events: 2", id="many"),
    ],
)
@pytest.mark.usefixtures("request_context")
def test_the_confirmation_counts_the_affected_events(
    with_user: tuple[UserId, str], rows: Rows, affected: str
) -> None:
    set_request_vars(_delete_event="1")

    _command, dialog = _acted(with_user[0], (), CommandECArchiveEvent, rows)

    assert str(dialog.affected) == affected


@pytest.mark.parametrize(
    "permission, field",
    [
        pytest.param("mkeventd.update_comment", "_mkeventd_comment", id="comment"),
        pytest.param("mkeventd.update_contact", "_mkeventd_contact", id="contact"),
    ],
)
@pytest.mark.usefixtures("request_context", "patch_theme")
def test_the_update_form_offers_a_field_with_its_permission(
    with_user: tuple[UserId, str], permission: str, field: str
) -> None:
    assert f'name="{field}"' in _render(CommandECUpdateEvent, with_user[0], permission)


@pytest.mark.usefixtures("request_context", "patch_theme")
def test_the_update_form_offers_neither_comment_nor_contact_without_permission(
    with_user: tuple[UserId, str],
) -> None:
    rendered = _render(CommandECUpdateEvent, with_user[0])

    assert re.findall(r'name="(_mkeventd_comment|_mkeventd_contact)"', rendered) == []


@pytest.mark.parametrize(
    "command, submit_button",
    [
        pytest.param(CommandECUpdateEvent, "_mkeventd_update", id="update"),
        pytest.param(CommandECChangeState, "_mkeventd_changestate", id="change state"),
        pytest.param(CommandECCustomAction, "_action_@NOTIFY", id="custom action"),
        pytest.param(CommandECArchiveEvent, "_delete_event", id="archive"),
        pytest.param(
            CommandECArchiveEventsOfHost, "_archive_events_of_hosts", id="archive of host"
        ),
    ],
)
@pytest.mark.usefixtures("request_context", "patch_theme")
def test_an_ec_command_form_offers_the_button_its_action_reacts_to(
    with_user: tuple[UserId, str], command: Command, submit_button: str
) -> None:
    assert f'name="{submit_button}"' in _render(command, with_user[0])


@pytest.mark.usefixtures("request_context")
def test_changing_the_state_sets_the_selected_state(with_user: tuple[UserId, str]) -> None:
    set_request_vars(_mkeventd_changestate="1", _mkeventd_state=DropdownChoice.option_id(1))

    command, _dialog = _acted(with_user[0], (), CommandECChangeState, _EVENT_ROWS)

    assert command == ECChangeState((1, 2), with_user[0], 1)


@pytest.mark.usefixtures("request_context")
def test_the_state_change_confirmation_names_the_new_state(
    with_user: tuple[UserId, str],
) -> None:
    set_request_vars(_mkeventd_changestate="1", _mkeventd_state=DropdownChoice.option_id(1))

    _command, dialog = _acted(with_user[0], (), CommandECChangeState, _EVENT_ROWS)

    assert "New state: WARN" in str(dialog.additions)


@pytest.mark.usefixtures("request_context")
def test_a_custom_action_executes_the_pressed_action(with_user: tuple[UserId, str]) -> None:
    set_request_vars(**{"_action_@NOTIFY": "Send monitoring notification"})

    command, _dialog = _acted(with_user[0], (), CommandECCustomAction, _EVENT_ROWS)

    assert command == ECAction((1, 2), "@NOTIFY", with_user[0])


@pytest.mark.usefixtures("request_context")
def test_the_custom_action_confirmation_names_the_action(
    with_user: tuple[UserId, str],
) -> None:
    set_request_vars(**{"_action_@NOTIFY": "Send monitoring notification"})

    _command, dialog = _acted(with_user[0], (), CommandECCustomAction, _EVENT_ROWS)

    assert dialog.confirm_title == "Execute custom action 'Send monitoring notification'?"


@pytest.mark.usefixtures("request_context")
def test_archiving_archives_all_selected_events(with_user: tuple[UserId, str]) -> None:
    set_request_vars(_delete_event="1")

    command, _dialog = _acted(with_user[0], (), CommandECArchiveEvent, _EVENT_ROWS)

    assert command == ECDelete((1, 2), with_user[0])


@pytest.mark.usefixtures("request_context")
def test_archiving_the_events_of_a_host_archives_by_host_name(
    with_user: tuple[UserId, str],
) -> None:
    set_request_vars(_archive_events_of_hosts="1")

    commands, _dialog = _acted(
        with_user[0], (), CommandECArchiveEventsOfHost, [{"site": "local", "host_name": "myhost"}]
    )

    assert commands == [ECDeleteEventsOfHost(HostName("myhost"), with_user[0])]


def _service_rows(*host_names: str) -> Rows:
    return [
        {"site": "local", "host_name": host_name, "service_description": f"Service {nr}"}
        for nr, host_name in enumerate(host_names)
    ]


@pytest.mark.usefixtures("request_context")
def test_the_confirmation_of_archiving_the_events_of_a_host_names_the_host(
    with_user: tuple[UserId, str],
) -> None:
    set_request_vars(_archive_events_of_hosts="1")

    _commands, dialog = _acted(
        with_user[0], (), CommandECArchiveEventsOfHost, _service_rows("myhost", "myhost")
    )

    assert "All events of the host 'myhost' will be removed" in unescape(str(dialog.additions))


@pytest.mark.usefixtures("request_context")
def test_the_confirmation_of_archiving_the_events_of_several_hosts_counts_them(
    with_user: tuple[UserId, str],
) -> None:
    set_request_vars(_archive_events_of_hosts="1")

    _commands, dialog = _acted(
        with_user[0], (), CommandECArchiveEventsOfHost, _service_rows("a", "b", "a")
    )

    assert "All events of the 2 hosts of the selected services will be removed" in str(
        dialog.additions
    )


@pytest.mark.usefixtures("request_context")
def test_the_confirmation_of_archiving_the_events_of_a_host_counts_nothing(
    with_user: tuple[UserId, str],
) -> None:
    set_request_vars(_archive_events_of_hosts="1")

    _commands, dialog = _acted(
        with_user[0], (), CommandECArchiveEventsOfHost, [{"site": "local", "host_name": "myhost"}]
    )

    assert dialog.affected == HTML.empty()


@pytest.mark.usefixtures("request_context", "with_admin_login")
def test_an_ec_command_is_sent_to_the_core_of_the_site(
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.set_sites(["NO_SITE"])
    mock_livestatus.expect_query("COMMAND [...] EC_DELETE;1,2;harry", match_type="ellipsis")

    with mock_livestatus():
        CommandECArchiveEvent.executor(ECDelete((1, 2), UserId("harry")), SiteId("NO_SITE"))


def _sorted_states(rows: Rows) -> list[object]:
    return [
        row.get("event_state")
        for row in sorted(rows, key=cmp_to_key(partial(cmp_simple_state, "event_state")))
    ]


def test_an_unknown_event_state_sorts_between_warn_and_crit() -> None:
    assert _sorted_states([{"event_state": state} for state in (3, 2, 1, 0)]) == [0, 1, 3, 2]


def test_events_without_a_state_sort_first() -> None:
    assert _sorted_states([{"event_state": 0}, {}]) == [None, 0]


def _sorted_by(sorter: Sorter, rows: Rows) -> Rows:
    config = Config()
    return sorted(
        rows,
        key=cmp_to_key(
            partial(
                sorter.cmp,
                parameters=None,
                config=config,
                request=request,
                request_cache=RequestCache(config),
            )
        ),
    )


def test_the_service_level_sorter_orders_by_number() -> None:
    rows: Rows = [{"custom_variables": {"EC_SL": level}} for level in ("10", "5", "100")]

    ordered = _sorted_by(SorterServicelevel, rows)

    assert [row["custom_variables"]["EC_SL"] for row in ordered] == ["5", "10", "100"]


def test_the_service_level_sorter_puts_objects_without_service_level_first() -> None:
    rows: Rows = [{"custom_variables": {"EC_SL": "0"}}, {"custom_variables": {}}]

    ordered = _sorted_by(SorterServicelevel, rows)

    assert [row["custom_variables"].get("EC_SL") for row in ordered] == [None, "0"]


@pytest.mark.parametrize(
    "sorter_name, what",
    [
        pytest.param("svc_servicelevel", "service", id="service"),
        pytest.param("host_servicelevel", "host", id="host"),
    ],
)
def test_the_sorters_named_after_the_service_level_columns_sort_by_number(
    sorter_name: str, what: str
) -> None:
    rows: Rows = [
        {f"{what}_custom_variable_names": ["EC_SL"], f"{what}_custom_variable_values": [level]}
        for level in ("10", "5", "100")
    ]

    ordered = _sorted_by(sorter_registry[sorter_name], rows)

    assert [row[f"{what}_custom_variable_values"][0] for row in ordered] == ["5", "10", "100"]
