#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from http import HTTPStatus

from cmk.ccc.user import UserId
from cmk.gui.dashboard.api.compute_graph_links import GRAPH_LINK_SERVICE_LIMIT
from cmk.livestatus_client.testing import MockLiveStatusConnection
from tests.testlib.unit.rest_api_client import ClientRegistry, Response
from tests.unit.cmk.gui.helpers.dashboard_api_test_helper import (
    dashboard_widget_token,
    explicit_source,
)

_GRAPH: dict[str, object] = {
    "type": "performance_graph",
    "timerange": "dashboard",
    "graph_render_options": {},
    "source": "uptime",
}

_INHERITED: dict[str, object] = {
    "type": "inherited",
    "location": {"type": "views", "name": "allhosts"},
    "include_context": True,
    "include_time_range": True,
    "show_filter_form": False,
}

_UPTIME: dict[str, object] = {
    "site_id": "NO_SITE",
    "host_name": "heute",
    "service_description": "Uptime",
}


_SAME_STATE: dict[str, object] = {
    "type": "custom",
    "links": [
        {
            "title": "Same state",
            "location": {"type": "views", "name": "searchsvc"},
            "filters": [{"filter_id": "svcstate"}],
            "include_context": False,
            "include_time_range": False,
            "show_filter_form": False,
        }
    ],
}

_STATE_OK = {"svcstate": {"status": "encoded", "variables": {"st0": "on"}}}


def _body(link: dict[str, object], services: list[dict[str, object]]) -> dict[str, object]:
    return {"source": explicit_source({**_GRAPH, "contextual_link": link}), "services": services}


def _compute(
    clients: ClientRegistry,
    live: MockLiveStatusConnection,
    body: dict[str, object],
    *,
    query: str | None = None,
    rows: list[dict[str, object]] | None = None,
) -> Response:
    if query is None:
        # Without a custom link's filters to value, nothing asks livestatus.
        return clients.DashboardClient.compute_widget("compute-graph-links", body)
    live.set_sites(["NO_SITE"])
    live.add_table("services", rows or [])
    live.expect_query(query, match_type="ellipsis")
    with live:
        return clients.DashboardClient.compute_widget("compute-graph-links", body)


def test_an_inherited_graph_answers_its_target(
    clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection
) -> None:
    value = _compute(clients, mock_livestatus, _body(_INHERITED, [_UPTIME])).json["value"]

    assert [link["location"] for link in value["links"]] == [{"type": "views", "name": "allhosts"}]


def test_an_inherited_link_carries_the_site_the_host_and_the_service(
    clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection
) -> None:
    (service,) = _compute(clients, mock_livestatus, _body(_INHERITED, [_UPTIME])).json["value"][
        "services"
    ]

    assert service["link_properties"] == {
        "links": [
            {
                "siteopt": {"status": "encoded", "variables": {"site": "NO_SITE"}},
                "host": {"status": "encoded", "variables": {"host": "heute"}},
                "service": {"status": "encoded", "variables": {"service": "Uptime"}},
            }
        ]
    }


def test_a_service_of_an_unknown_site_carries_no_site(
    clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection
) -> None:
    (service,) = _compute(
        clients, mock_livestatus, _body(_INHERITED, [{**_UPTIME, "site_id": None}])
    ).json["value"]["services"]

    (link,) = service["link_properties"]["links"]
    assert sorted(link) == ["host", "service"]


def test_a_graph_linking_nowhere_answers_no_link(
    clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection
) -> None:
    value = _compute(clients, mock_livestatus, _body({"type": "none"}, [_UPTIME])).json["value"]

    assert (value["links"], value["services"][0]["link_properties"]) == ([], {"links": []})


def test_a_link_to_a_page_the_viewer_cannot_open_is_left_out(
    clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection
) -> None:
    missing = {**_INHERITED, "location": {"type": "dashboards", "name": "no_such_dashboard"}}

    value = _compute(clients, mock_livestatus, _body(missing, [_UPTIME])).json["value"]

    assert value["links"] == []


def _compute_same_state(
    clients: ClientRegistry, live: MockLiveStatusConnection, service: dict[str, object]
) -> dict[str, object]:
    """The link properties of a custom link carrying the state of the service."""
    (computed,) = _compute(
        clients,
        live,
        _body(_SAME_STATE, [service]),
        query=(
            "GET services\n"
            "Columns: host_name service_description service_has_been_checked service_state\n"
            "Filter: host_name = heute\nFilter: service_description = Uptime\n"
        ),
        rows=[
            {
                "host_name": "heute",
                "service_description": "Uptime",
                "service_state": 0,
                "service_has_been_checked": 1,
            }
        ],
    ).json["value"]["services"]
    link_properties: dict[str, object] = computed["link_properties"]
    return link_properties


def test_a_custom_link_carries_the_filters_from_the_row_of_each_service(
    clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection
) -> None:
    assert _compute_same_state(clients, mock_livestatus, _UPTIME) == {"links": [_STATE_OK]}


def test_a_custom_link_of_a_service_of_an_unknown_site_reads_the_row_of_any_site(
    clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection
) -> None:
    link_properties = _compute_same_state(clients, mock_livestatus, {**_UPTIME, "site_id": None})

    assert link_properties == {"links": [_STATE_OK]}


def test_another_widget_type_is_rejected(clients: ClientRegistry) -> None:
    body = {
        "source": explicit_source({"type": "static_text", "text": "no graph"}),
        "services": [],
    }
    response = clients.DashboardClient.compute_widget("compute-graph-links", body, expect_ok=False)

    assert response.status_code == HTTPStatus.BAD_REQUEST


def test_more_services_than_a_graph_draws_lines_for_are_rejected(clients: ClientRegistry) -> None:
    body = _body(_INHERITED, [_UPTIME] * (GRAPH_LINK_SERVICE_LIMIT + 1))

    response = clients.DashboardClient.compute_widget("compute-graph-links", body, expect_ok=False)

    assert response.status_code == HTTPStatus.BAD_REQUEST


def test_a_shared_dashboard_may_not_ask_for_links(
    clients: ClientRegistry, with_automation_user: tuple[UserId, str]
) -> None:
    content = {**_GRAPH, "contextual_link": _INHERITED}
    with dashboard_widget_token(clients, with_automation_user[0], content) as saved:
        response = clients.DashboardClient.compute_widget(
            "compute-graph-links",
            {"source": saved.source, "services": [_UPTIME]},
            headers=saved.headers,
            expect_ok=False,
        )

    assert response.status_code == HTTPStatus.UNAUTHORIZED
