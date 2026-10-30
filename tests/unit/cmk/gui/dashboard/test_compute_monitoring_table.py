#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
import re
from collections.abc import Iterator, Sequence
from http import HTTPStatus
from typing import get_args

import pytest

from cmk.ccc.user import UserId
from cmk.gui.dashboard.api.model.widget_content.monitoring_table import MonitoringTableContent
from cmk.gui.dashboard.dashlet.dashlets.monitoring_table import MonitoringTableDashlet
from cmk.gui.dashboard.monitoring_tables import MONITORING_TABLES
from cmk.gui.dashboard.type_defs import MonitoringTableName
from cmk.livestatus_client.testing import MockLiveStatusConnection
from tests.testlib.unit.gui.web_test_app import SetConfig
from tests.testlib.unit.rest_api_client import ClientRegistry, Response
from tests.unit.cmk.gui.helpers.dashboard_api_test_helper import (
    create_dashboard_payload,
    create_widget,
    dashboard_widget_token,
    SavedWidget,
)

_CONTENT: dict[str, object] = {
    "type": "monitoring_table",
    "table": "hosts",
    "columns": ["state", "name"],
    "sort": ["name:asc"],
    "limit": 100,
    "date_format": "%Y-%m-%d",
    "timestamp_format": "mixed",
}


def _body(context: dict[str, object], **extra: object) -> dict[str, object]:
    return {"source": {"type": "explicit", "content": _CONTENT, "context": context}, **extra}


def _as_pattern(line: str) -> str:
    """The pattern for the mock that matches the line as it is.

    The mock escapes "[" and "+" of a pattern itself, so escaping them here would do it twice."""
    return re.escape(line).replace(r"\[", "[").replace(r"\+", "+")


def _compute_expecting_host_query(
    clients: ClientRegistry,
    live: MockLiveStatusConnection,
    body: dict[str, object],
    *,
    filter_lines: Sequence[str] = (),
) -> Response:
    """Compute the widget, and expect the query for its rows to have exactly the given filter lines.

    The expectation is the assertion on the filters: the mock raises if the query differs from it,
    or if it is never sent. The columns the table queries are not of interest here. The mock reads
    the expectation as a pattern, so the lines of the filters are matched literally."""
    live.set_sites(["NO_SITE"])
    live.expect_query("GET hosts\nStats: state >= 0")
    live.expect_query(
        [
            "GET hosts",
            "Columns: ...",
            *map(_as_pattern, filter_lines),
            "OrderBy: name asc natural",
            "Limit: 100",
        ],
        match_type="ellipsis",
    )
    with live:
        return clients.DashboardClient.compute_widget("compute-monitoring-table", body)


def test_a_dashboard_filter_narrows_the_host_query(
    clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection
) -> None:
    response = _compute_expecting_host_query(
        clients,
        mock_livestatus,
        _body({"hostregex": {"host_regex": "heute"}}),
        filter_lines=["Filter: name ~~ heute"],
    )

    assert response.json["value"]["unapplied_filters"] == []


def test_a_dashboard_tag_filter_narrows_the_host_query_to_the_tag(
    clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection
) -> None:
    # "agent" is a builtin tag group, so the tag configuration of the site has it without a setup.
    response = _compute_expecting_host_query(
        clients,
        mock_livestatus,
        _body(
            {
                "host_tags": {
                    "host_tag_0_grp": "agent",
                    "host_tag_0_op": "is",
                    "host_tag_0_val": "cmk-agent",
                }
            }
        ),
        filter_lines=["Filter: tags = 'agent' 'cmk-agent'"],
    )

    assert response.json["value"]["unapplied_filters"] == []


def test_a_dashboard_filter_the_table_cannot_apply_is_reported(
    clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection
) -> None:
    response = _compute_expecting_host_query(
        clients,
        mock_livestatus,
        _body({"host_active_checks_enabled": {"is_host_active_checks_enabled": "1"}}),
    )

    assert response.json["value"]["unapplied_filters"] == [
        {"id": "host_active_checks_enabled", "title": "Host active checks enabled"}
    ]


def test_a_dashboard_filter_for_another_object_type_is_ignored(
    clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection
) -> None:
    response = _compute_expecting_host_query(
        clients, mock_livestatus, _body({"serviceregex": {"service_regex": "CPU"}})
    )

    assert response.json["value"]["unapplied_filters"] == []


def test_a_site_that_does_not_answer_is_reported(
    clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection
) -> None:
    mock_livestatus.set_sites(["NO_SITE", "remote"])
    mock_livestatus.add_table("hosts", [])
    mock_livestatus.make_site_unreachable("remote")
    mock_livestatus.expect_query(["GET hosts", "Stats: state >= 0"], match_type="loose")
    mock_livestatus.expect_query(["GET hosts"], match_type="loose")

    with mock_livestatus:
        response = clients.DashboardClient.compute_widget("compute-monitoring-table", _body({}))

    assert response.json["value"]["unreachable_sites"] == ["remote"]


_HOST_WITH_GRAPHS: dict[str, object] = {
    "name": "heute",
    "state": 0,
    "has_been_checked": 1,
    "acknowledged": 0,
    "scheduled_downtime_depth": 0,
    "notifications_enabled": 1,
    "comments": [],
    "modified_attributes_list": [],
    "active_checks_enabled": 1,
    "accept_passive_checks": 1,
    "in_notification_period": 1,
    "in_service_period": 1,
    "in_check_period": 1,
    "is_flapping": 0,
    "staleness": 0.0,
    "filename": "/etc/nagios/hosts.cfg",
    "pnpgraph_present": 1,
}


def _compute_host_with_graphs(
    clients: ClientRegistry,
    live: MockLiveStatusConnection,
    body: dict[str, object],
    *,
    headers: dict[str, str] | None = None,
    host: dict[str, object] = _HOST_WITH_GRAPHS,
) -> Response:
    live.set_sites(["NO_SITE"])
    live.add_table("hosts", [host])
    live.expect_query("GET hosts\nStats: state >= 0")
    live.expect_query(["GET hosts", "OrderBy: name asc natural", "Limit: 100"], match_type="loose")
    with live:
        return clients.DashboardClient.compute_widget(
            "compute-monitoring-table", body, headers=headers
        )


@pytest.fixture(name="saved_table_widget")
def fixture_saved_table_widget(
    clients: ClientRegistry, with_automation_user: tuple[UserId, str]
) -> Iterator[SavedWidget]:
    with dashboard_widget_token(clients, with_automation_user[0], _CONTENT) as saved:
        yield saved


def test_a_host_with_graphs_links_to_them_whichever_columns_are_shown(
    clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection
) -> None:
    response = _compute_host_with_graphs(clients, mock_livestatus, _body({}))

    assert [row.get("graphs_link") for row in response.json["value"]["rows"]] == [
        "view.py?view_name=host_graphs&site=NO_SITE&host=heute"
    ]


def test_a_shared_dashboard_links_no_host_to_its_graphs(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
    saved_table_widget: SavedWidget,
) -> None:
    response = _compute_host_with_graphs(
        clients,
        mock_livestatus,
        {"source": saved_table_widget.source},
        headers=saved_table_widget.headers,
    )

    assert [row.get("graphs_link") for row in response.json["value"]["rows"]] == [None]


_SERVICES_CONTENT: dict[str, object] = {
    **_CONTENT,
    "table": "services",
    "columns": ["state", "name"],
    "sort": ["name:asc"],
}


_SERVICE_WITH_GRAPHS: dict[str, object] = {
    "description": "CPU",
    "host_name": "heute",
    "state": 0,
    "has_been_checked": 1,
    "plugin_output": "OK",
    "acknowledged": 0,
    "scheduled_downtime_depth": 0,
    "notifications_enabled": 1,
    "comments": [],
    "modified_attributes_list": [],
    "active_checks_enabled": 1,
    "accept_passive_checks": 1,
    "in_notification_period": 1,
    "in_service_period": 1,
    "in_check_period": 1,
    "in_passive_check_period": 1,
    "is_flapping": 0,
    "staleness": 0.0,
    "last_check": 0,
    "last_state_change": 0,
    "perf_data": "",
    "check_command": "check_cpu",
    "check_type": 0,
    "cached_at": 0,
    "cache_interval": 0,
    "host_state": 0,
    "host_has_been_checked": 1,
    "pnpgraph_present": 1,
}


def _compute_service_with_graphs(
    clients: ClientRegistry,
    live: MockLiveStatusConnection,
    body: dict[str, object],
    *,
    headers: dict[str, str] | None = None,
) -> Response:
    live.set_sites(["NO_SITE"])
    live.add_table("services", [_SERVICE_WITH_GRAPHS])
    live.expect_query("GET services\nStats: state >= 0")
    live.expect_query(
        ["GET services", "OrderBy: description asc natural", "Limit: 100"], match_type="loose"
    )
    with live:
        return clients.DashboardClient.compute_widget(
            "compute-monitoring-table", body, headers=headers
        )


@pytest.fixture(name="saved_services_widget")
def fixture_saved_services_widget(
    clients: ClientRegistry, with_automation_user: tuple[UserId, str]
) -> Iterator[SavedWidget]:
    with dashboard_widget_token(clients, with_automation_user[0], _SERVICES_CONTENT) as saved:
        yield saved


def test_a_service_with_graphs_links_to_them_whichever_columns_are_shown(
    clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection
) -> None:
    response = _compute_service_with_graphs(
        clients,
        mock_livestatus,
        {"source": {"type": "explicit", "content": _SERVICES_CONTENT, "context": {}}},
    )

    assert [row.get("graphs_link") for row in response.json["value"]["rows"]] == [
        "view.py?view_name=service_graphs&site=NO_SITE&host=heute&service=CPU"
    ]


def test_a_shared_dashboard_links_no_service_to_its_graphs(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
    saved_services_widget: SavedWidget,
) -> None:
    response = _compute_service_with_graphs(
        clients,
        mock_livestatus,
        {"source": saved_services_widget.source},
        headers=saved_services_widget.headers,
    )

    assert [row.get("graphs_link") for row in response.json["value"]["rows"]] == [None]


def test_a_services_widget_lists_the_services_of_a_user_who_may_reschedule_them(
    clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection
) -> None:
    # A service row checks whether its viewer may reschedule it, for the offer it carries, which
    # the endpoint has to declare.
    response = _compute_service_with_graphs(
        clients,
        mock_livestatus,
        {"source": {"type": "explicit", "content": _SERVICES_CONTENT, "context": {}}},
    )

    assert [row["name"] for row in response.json["value"]["rows"]] == ["CPU"]


def test_a_dashboard_host_filter_narrows_the_services_query(
    clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection
) -> None:
    content = {**_CONTENT, "table": "services", "columns": ["host_name", "name"], "sort": []}
    mock_livestatus.set_sites(["NO_SITE"])
    mock_livestatus.add_table(
        "services", [{"host_name": "heute", "description": "CPU", "state": 0}]
    )
    mock_livestatus.expect_query("GET services\nStats: state >= 0")
    mock_livestatus.expect_query(
        [
            "GET services",
            "Filter: host_name ~~ no-such-host",
            "OrderBy: host_name asc natural",
            "Limit: 100",
        ],
        match_type="loose",
    )
    mock_livestatus.expect_query(
        ["GET services", "Stats: state >= 0", "Filter: host_name ~~ no-such-host"],
        match_type="loose",
    )
    with mock_livestatus:
        response = clients.DashboardClient.compute_widget(
            "compute-monitoring-table",
            {
                "source": {
                    "type": "explicit",
                    "content": content,
                    "context": {"hostregex": {"host_regex": "no-such-host"}},
                }
            },
        )

    assert response.json["value"]["unapplied_filters"] == []


def test_an_unknown_sort_column_is_400(clients: ClientRegistry) -> None:
    response = clients.DashboardClient.compute_widget(
        "compute-monitoring-table", _body({}, sort=["no_such_column:asc"]), expect_ok=False
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST, response.body


def test_sorting_by_a_column_the_widget_does_not_display_is_400(clients: ClientRegistry) -> None:
    response = clients.DashboardClient.compute_widget(
        "compute-monitoring-table", _body({}, sort=["alias:asc"]), expect_ok=False
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST, response.body


@pytest.mark.parametrize(
    "content",
    [
        pytest.param({**_CONTENT, "columns": ["name", "no_such_column"]}, id="unknown column"),
        pytest.param({**_CONTENT, "columns": ["name", "num_relations"]}, id="relations column"),
        pytest.param({**_CONTENT, "sort": ["alias:asc"]}, id="sort by a hidden column"),
        pytest.param({**_CONTENT, "columns": []}, id="no column"),
        pytest.param({**_CONTENT, "columns": ["name", "name"]}, id="repeated column"),
        pytest.param({**_CONTENT, "limit": 0}, id="limit below one"),
        pytest.param({**_CONTENT, "limit": 5001}, id="limit above maximum"),
        pytest.param({**_CONTENT, "timestamp_format": "age"}, id="unknown timestamp format"),
    ],
)
def test_an_invalid_widget_is_rejected(clients: ClientRegistry, content: dict[str, object]) -> None:
    response = clients.DashboardClient.create_relative_grid_dashboard(
        create_dashboard_payload("table_dashboard", {"table": create_widget(content)}),
        expect_ok=False,
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST, response.body


def test_the_picked_columns_survive_a_reload(clients: ClientRegistry) -> None:
    content = {**_CONTENT, "columns": ["name", "num_services_crit", "labels"]}
    clients.DashboardClient.create_relative_grid_dashboard(
        create_dashboard_payload("table_dashboard", {"table": create_widget(content)})
    )

    response = clients.DashboardClient.get_relative_grid_dashboard("table_dashboard")

    widget = next(iter(response.json["extensions"]["widgets"].values()))
    assert widget["content"] == content


_HOSTS_TABLE = MonitoringTableContent(
    type="monitoring_table",
    table="hosts",
    columns=["name"],
    sort=[],
    limit=10,
    date_format="%d.%m.%Y",
    timestamp_format="abs",
)


def test_a_monitoring_table_survives_the_internal_round_trip() -> None:
    assert MonitoringTableContent.from_internal(_HOSTS_TABLE.to_internal()) == _HOSTS_TABLE


def test_a_monitoring_table_stored_without_display_options_shows_the_page_defaults() -> None:
    config = _HOSTS_TABLE.to_internal()
    del config["date_format"], config["timestamp_format"]

    content = MonitoringTableContent.from_internal(config)

    assert (content.date_format, content.timestamp_format) == ("%Y-%m-%d", "mixed")


@pytest.mark.usefixtures("request_context")
def test_a_stored_hosts_table_takes_host_filters() -> None:
    assert MonitoringTableDashlet(_HOSTS_TABLE.to_internal()).infos() == ["host"]


@pytest.mark.usefixtures("request_context")
def test_a_stored_services_table_takes_host_and_service_filters() -> None:
    services_table = dataclasses.replace(_HOSTS_TABLE, table="services")

    assert MonitoringTableDashlet(services_table.to_internal()).infos() == ["host", "service"]


def test_every_monitoring_table_is_registered() -> None:
    assert set(MONITORING_TABLES) == set(get_args(MonitoringTableName.__value__))


def _log_in_with_admin_permissions_but(
    clients: ClientRegistry, permissions: dict[str, str]
) -> None:
    clients.UserRole.clone(body={"role_id": "admin", "new_role_id": "restricted"})
    clients.UserRole.edit(role_id="restricted", body={"new_permissions": permissions})
    clients.User.create(
        username="restricted_user",
        fullname="restricted_user",
        customer=None,
        auth_option={"auth_type": "password", "password": "supersecretish"},
        roles=["restricted"],
    )
    clients.DashboardClient.set_credentials("restricted_user", "supersecretish")


def _services_body() -> dict[str, object]:
    return {"source": {"type": "explicit", "content": _SERVICES_CONTENT, "context": {}}}


def test_a_hosts_table_offers_the_host_commands_of_the_reader(
    clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection
) -> None:
    response = _compute_host_with_graphs(clients, mock_livestatus, _body({}))

    assert "reschedule" in [action["ident"] for action in response.json["value"]["actions"]]


def test_a_hosts_table_offers_the_setup_links_of_the_reader(
    clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection
) -> None:
    response = _compute_host_with_graphs(clients, mock_livestatus, _body({}))

    assert [link["ident"] for link in response.json["value"]["links"]] == [
        "edit",
        "parameters",
    ]


def test_a_hosts_table_offers_nothing_more_for_the_host_of_a_row(
    clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection
) -> None:
    response = _compute_host_with_graphs(clients, mock_livestatus, _body({}))

    value = response.json["value"]
    assert (value["host_actions"], value["host_links"]) == ([], [])


def test_a_reader_who_may_not_act_is_offered_no_commands(
    clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection
) -> None:
    _log_in_with_admin_permissions_but(clients, {"general.act": "no"})

    response = _compute_host_with_graphs(clients, mock_livestatus, _body({}))

    assert response.json["value"]["actions"] == []


def test_a_reader_who_may_not_edit_rules_is_offered_no_link_to_the_parameters_of_a_host(
    clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection
) -> None:
    _log_in_with_admin_permissions_but(clients, {"wato.rulesets": "no"})

    response = _compute_host_with_graphs(clients, mock_livestatus, _body({}))

    assert [link["ident"] for link in response.json["value"]["links"]] == ["edit"]


def test_a_row_of_a_setup_host_says_the_reader_may_open_it_there(
    clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection
) -> None:
    clients.HostConfig.create(host_name="heute")

    response = _compute_host_with_graphs(
        clients,
        mock_livestatus,
        _body({}),
        host={**_HOST_WITH_GRAPHS, "filename": "/wato/hosts.mk"},
    )

    assert [row.get("setup_access") for row in response.json["value"]["rows"]] == [True]


def test_a_row_of_a_host_outside_setup_says_the_reader_may_not_open_it_there(
    clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection
) -> None:
    response = _compute_host_with_graphs(clients, mock_livestatus, _body({}))

    assert [row.get("setup_access") for row in response.json["value"]["rows"]] == [False]


def test_without_setup_links_no_row_says_whether_the_reader_may_open_it_there(
    clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection, set_config: SetConfig
) -> None:
    with set_config(wato_enabled=False):
        response = _compute_host_with_graphs(clients, mock_livestatus, _body({}))

    assert [row.get("setup_access") for row in response.json["value"]["rows"]] == [None]


def test_a_shared_dashboard_offers_nothing_to_do_with_a_host(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
    saved_table_widget: SavedWidget,
) -> None:
    response = _compute_host_with_graphs(
        clients,
        mock_livestatus,
        {"source": saved_table_widget.source},
        headers=saved_table_widget.headers,
    )

    value = response.json["value"]
    assert (value["actions"], value["links"]) == ([], [])


def test_a_shared_dashboard_says_of_no_host_whether_it_may_be_opened_in_setup(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
    saved_table_widget: SavedWidget,
) -> None:
    response = _compute_host_with_graphs(
        clients,
        mock_livestatus,
        {"source": saved_table_widget.source},
        headers=saved_table_widget.headers,
    )

    assert [row.get("setup_access") for row in response.json["value"]["rows"]] == [None]


def test_a_services_table_offers_the_service_commands_of_the_reader(
    clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection
) -> None:
    response = _compute_service_with_graphs(clients, mock_livestatus, _services_body())

    assert "reschedule" in [action["ident"] for action in response.json["value"]["actions"]]


def test_a_services_table_offers_no_setup_links_for_a_service(
    clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection
) -> None:
    response = _compute_service_with_graphs(clients, mock_livestatus, _services_body())

    assert response.json["value"]["links"] == []


def test_a_services_table_offers_the_host_commands_of_the_reader_for_the_host_of_a_row(
    clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection
) -> None:
    response = _compute_service_with_graphs(clients, mock_livestatus, _services_body())

    assert "reschedule" in [action["ident"] for action in response.json["value"]["host_actions"]]


def test_a_services_table_offers_the_setup_links_of_the_reader_for_the_host_of_a_row(
    clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection
) -> None:
    response = _compute_service_with_graphs(clients, mock_livestatus, _services_body())

    assert [link["ident"] for link in response.json["value"]["host_links"]] == [
        "edit",
        "parameters",
    ]


def test_a_shared_dashboard_offers_nothing_to_do_with_a_service_or_its_host(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
    saved_services_widget: SavedWidget,
) -> None:
    response = _compute_service_with_graphs(
        clients,
        mock_livestatus,
        {"source": saved_services_widget.source},
        headers=saved_services_widget.headers,
    )

    value = response.json["value"]
    assert [
        value["actions"],
        value["links"],
        value["host_actions"],
        value["host_links"],
    ] == [[], [], [], []]
