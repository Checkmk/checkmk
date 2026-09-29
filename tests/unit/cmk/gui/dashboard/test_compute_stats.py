#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator

import pytest

from cmk.ccc.user import UserId
from cmk.livestatus_client.testing import MockLiveStatusConnection
from tests.testlib.unit.rest_api_client import ClientRegistry, Response
from tests.unit.cmk.gui.helpers.dashboard_api_test_helper import dashboard_widget_token, SavedWidget

_HOSTS = [
    {"state": 0, "scheduled_downtime_depth": 0, "custom_variable_names": [], "host_name": "web01"},
    {"state": 0, "scheduled_downtime_depth": 0, "custom_variable_names": [], "host_name": "web02"},
    {"state": 1, "scheduled_downtime_depth": 1, "custom_variable_names": [], "host_name": "db01"},
    {"state": 2, "scheduled_downtime_depth": 0, "custom_variable_names": [], "host_name": "db02"},
    {"state": 1, "scheduled_downtime_depth": 0, "custom_variable_names": [], "host_name": "db03"},
]

_SERVICES = [
    {
        "state": state,
        "scheduled_downtime_depth": 0,
        "host_scheduled_downtime_depth": 0,
        "host_state": 0,
        "host_has_been_checked": 1,
        "host_custom_variable_names": [],
        "host_name": host_name,
    }
    for host_name, state in [("web01", 0), ("web01", 2), ("db01", 1)]
]

_HOST_STATS_QUERY = (
    "GET hosts\n"
    "Stats: state = 0\n"
    "Stats: scheduled_downtime_depth = 0\n"
    "StatsAnd: 2\n"
    "Stats: scheduled_downtime_depth > 0\n"
    "Stats: state = 2\n"
    "Stats: scheduled_downtime_depth = 0\n"
    "StatsAnd: 2\n"
    "Stats: state = 1\n"
    "Stats: scheduled_downtime_depth = 0\n"
    "StatsAnd: 2\n"
    "Filter: custom_variable_names < _REALNAME"
)

_SERVICE_STATS_QUERY = "\n".join(
    [
        "GET services",
        *(
            f"Stats: {line}"
            for line in [
                "state = 0",
                "scheduled_downtime_depth = 0",
                "host_scheduled_downtime_depth = 0",
                "host_state = 0",
                "host_has_been_checked = 1",
            ]
        ),
        "StatsAnd: 5",
        "Stats: scheduled_downtime_depth > 0",
        "Stats: host_scheduled_downtime_depth > 0",
        "StatsOr: 2",
        "Stats: scheduled_downtime_depth = 0",
        "Stats: host_scheduled_downtime_depth = 0",
        "Stats: host_state != 0",
        "StatsAnd: 3",
        *(
            line
            for state in (1, 3, 2)
            for line in [
                f"Stats: state = {state}",
                "Stats: scheduled_downtime_depth = 0",
                "Stats: host_scheduled_downtime_depth = 0",
                "Stats: host_state = 0",
                "Stats: host_has_been_checked = 1",
                "StatsAnd: 5",
            ]
        ),
        "Filter: host_custom_variable_names < _REALNAME",
    ]
)

_ALL_HOSTS = {
    "title": "All hosts",
    "location": {"type": "views", "name": "searchhost"},
    "include_context": True,
    "include_time_range": False,
    "show_filter_form": True,
}

_NOT_IN_DOWNTIME = {
    "status": "encoded",
    "variables": {"is_host_scheduled_downtime_depth": "0"},
}


def _explicit(
    content: dict[str, object], context: dict[str, object] | None = None
) -> dict[str, object]:
    return {"source": {"type": "explicit", "content": content, "context": context or {}}}


def _compute_hosts(
    clients: ClientRegistry,
    live: MockLiveStatusConnection,
    body: dict[str, object],
    *,
    rows: list[dict[str, object]] | None = None,
    headers: dict[str, str] | None = None,
) -> Response:
    live.set_sites(["NO_SITE"])
    live.add_table("hosts", _HOSTS if rows is None else rows)
    live.expect_query(_HOST_STATS_QUERY)
    with live:
        return clients.DashboardClient.compute_stats(body, headers=headers)


def _compute_services(
    clients: ClientRegistry,
    live: MockLiveStatusConnection,
    body: dict[str, object],
    *,
    query: str = _SERVICE_STATS_QUERY,
) -> Response:
    live.set_sites(["NO_SITE"])
    live.add_table("services", _SERVICES)
    live.expect_query(query)
    with live:
        return clients.DashboardClient.compute_stats(body)


def _counts(response: Response) -> list[int]:
    return [part["count"] for part in response.json["value"]["parts"]]


@pytest.fixture(name="saved_stats_widget")
def fixture_saved_stats_widget(
    clients: ClientRegistry, with_automation_user: tuple[UserId, str]
) -> Iterator[SavedWidget]:
    with dashboard_widget_token(
        clients,
        with_automation_user[0],
        {
            "type": "host_stats",
            "contextual_link": {
                "type": "inherited",
                "location": {"type": "views", "name": "allhosts"},
                "include_context": True,
                "include_time_range": False,
                "show_filter_form": True,
            },
        },
    ) as saved:
        yield saved


def _saved(clients: ClientRegistry, live: MockLiveStatusConnection, saved: SavedWidget) -> Response:
    return _compute_hosts(clients, live, {"source": saved.source}, headers=saved.headers)


def test_a_host_statistics_widget_answers_one_value(
    clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection
) -> None:
    response = _compute_hosts(clients, mock_livestatus, _explicit({"type": "host_stats"}))

    assert response.json == {
        "domainType": "widget-compute",
        "value": {
            "links": [_ALL_HOSTS],
            "parts": [
                {
                    "category": "up",
                    "count": 2,
                    "link_properties": {
                        "links": [
                            {
                                "hoststate": {"status": "encoded", "variables": {"hst0": "on"}},
                                "host_scheduled_downtime_depth": _NOT_IN_DOWNTIME,
                            }
                        ]
                    },
                },
                {
                    "category": "downtime",
                    "count": 1,
                    "link_properties": {
                        "links": [
                            {
                                "host_scheduled_downtime_depth": {
                                    "status": "encoded",
                                    "variables": {"is_host_scheduled_downtime_depth": "1"},
                                }
                            }
                        ]
                    },
                },
                {
                    "category": "unreachable",
                    "count": 1,
                    "link_properties": {
                        "links": [
                            {
                                "hoststate": {"status": "encoded", "variables": {"hst2": "on"}},
                                "host_scheduled_downtime_depth": _NOT_IN_DOWNTIME,
                            }
                        ]
                    },
                },
                {
                    "category": "down",
                    "count": 1,
                    "link_properties": {
                        "links": [
                            {
                                "hoststate": {"status": "encoded", "variables": {"hst1": "on"}},
                                "host_scheduled_downtime_depth": _NOT_IN_DOWNTIME,
                            }
                        ]
                    },
                },
            ],
            "total": {"count": 5, "link_properties": {"links": [{}]}},
        },
    }


def test_both_arms_answer_the_same_counts(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
    saved_stats_widget: SavedWidget,
) -> None:
    explicit = _compute_hosts(clients, mock_livestatus, _explicit({"type": "host_stats"}))

    saved = _saved(clients, mock_livestatus, saved_stats_widget)

    assert _counts(saved) == _counts(explicit)
    assert saved.json["value"]["total"]["count"] == explicit.json["value"]["total"]["count"]


def test_the_saved_arm_answers_empty_links(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
    saved_stats_widget: SavedWidget,
) -> None:
    value = _saved(clients, mock_livestatus, saved_stats_widget).json["value"]

    assert value["links"] == []
    assert [part["link_properties"] for part in value["parts"]] == [{"links": []}] * 4
    assert value["total"]["link_properties"] == {"links": []}


def test_an_empty_result_answers_zero_counts(
    clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection
) -> None:
    response = _compute_hosts(clients, mock_livestatus, _explicit({"type": "host_stats"}), rows=[])

    assert _counts(response) == [0, 0, 0, 0]
    assert response.json["value"]["total"]["count"] == 0


def test_an_explicit_source_computes_the_sent_content(
    clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection
) -> None:
    body = _explicit({"type": "service_stats"}, {"host": {"host": "web01"}})

    response = _compute_services(
        clients, mock_livestatus, body, query=_SERVICE_STATS_QUERY + "\nFilter: host_name = web01"
    )

    assert [part["category"] for part in response.json["value"]["parts"]] == [
        "ok",
        "downtime",
        "host_down",
        "warning",
        "unknown",
        "critical",
    ]
    assert _counts(response) == [1, 0, 0, 0, 0, 1]


def test_inherited_yields_one_link_with_the_native_click_key(
    clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection
) -> None:
    body = _explicit(
        {
            "type": "host_stats",
            "contextual_link": {
                "type": "inherited",
                "location": {"type": "views", "name": "allhosts"},
                "include_context": False,
                "include_time_range": False,
                "show_filter_form": False,
            },
        }
    )

    value = _compute_hosts(clients, mock_livestatus, body).json["value"]

    assert [link["location"] for link in value["links"]] == [{"type": "views", "name": "allhosts"}]
    assert value["parts"][3]["link_properties"] == {
        "links": [
            {
                "hoststate": {"status": "encoded", "variables": {"hst1": "on"}},
                "host_scheduled_downtime_depth": _NOT_IN_DOWNTIME,
            }
        ]
    }


def test_a_widget_without_a_link_field_takes_the_built_in_link(
    clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection
) -> None:
    mock_livestatus.set_sites(["NO_SITE"])
    mock_livestatus.add_table("eventconsoleevents", [{"event_state": 2}])
    mock_livestatus.expect_query(
        "GET eventconsoleevents\n"
        "Stats: event_state = 0\nStats: event_state = 1\nStats: event_state = 3\nStats: event_state = 2"
    )

    with mock_livestatus:
        response = clients.DashboardClient.compute_stats(_explicit({"type": "event_stats"}))

    assert [link["location"] for link in response.json["value"]["links"]] == [
        {"type": "views", "name": "ec_events"}
    ]


def test_a_user_who_sees_only_related_events_gets_the_event_statistics(
    clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection
) -> None:
    clients.UserRole.clone(body={"role_id": "guest", "new_role_id": "related_events_only"})
    clients.UserRole.edit(
        role_id="related_events_only",
        body={"new_permissions": {"mkeventd.seeall": "no", "mkeventd.seeunrelated": "no"}},
    )
    clients.User.create(
        username="related_events_user",
        fullname="related_events_user",
        customer=None,
        auth_option={"auth_type": "password", "password": "supersecretish"},
        roles=["related_events_only"],
    )
    clients.DashboardClient.set_credentials("related_events_user", "supersecretish")
    mock_livestatus.set_sites(["NO_SITE"])
    mock_livestatus.add_table(
        "eventconsoleevents",
        [{"event_state": 2, "event_contact_groups": ["all"], "host_name": "web01"}],
    )
    mock_livestatus.expect_query(
        "GET eventconsoleevents\n"
        "Stats: event_state = 0\nStats: event_state = 1\nStats: event_state = 3\n"
        "Stats: event_state = 2\n"
        "Filter: event_contact_groups != \nFilter: host_name != \nOr: 2"
    )

    with mock_livestatus:
        response = clients.DashboardClient.compute_stats(_explicit({"type": "event_stats"}))

    assert _counts(response) == [0, 0, 0, 1]
