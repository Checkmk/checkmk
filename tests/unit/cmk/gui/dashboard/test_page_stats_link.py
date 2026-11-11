#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from http import HTTPStatus
from urllib.parse import parse_qsl, urlencode, urlparse

import pytest

from cmk.ccc.user import UserId
from cmk.livestatus_client.testing import MockLiveStatusConnection
from tests.testlib.unit.gui.web_test_app import WebTestAppForCMK
from tests.testlib.unit.rest_api_client import ClientRegistry
from tests.unit.cmk.gui.helpers.dashboard_api_test_helper import (
    create_dashboard_payload,
    create_widget,
)

_HOSTS = [
    {
        "host_name": host_name,
        "state": state,
        "host_has_been_checked": 1,
        "host_scheduled_downtime_depth": downtime,
        "host_groups": [f"{host_name[:2]}-servers", "all"],
        "custom_variable_names": [],
    }
    for host_name, state, downtime in [
        ("web01", 0, 0),
        ("web02", 0, 0),
        ("db01", 1, 1),
        ("db02", 2, 0),
        ("db03", 1, 0),
    ]
]

_SERVICES = [
    {
        "host_name": host_name,
        "service_description": f"Check {index}",
        "service_has_been_checked": 1,
        "state": state,
        "service_last_hard_state": state,
        "host_custom_variable_names": [],
    }
    for index, (host_name, state) in enumerate([("web01", 0), ("web01", 2), ("db01", 1)])
]

_DASHBOARD = "stats_board"
_WIDGET = "stats"


def _link(
    *filter_ids: str, include_context: bool = False, include_time_range: bool = False
) -> dict[str, object]:
    return {
        "title": "Problems",
        "location": {"type": "views", "name": "allhosts"},
        "filters": [{"filter_id": filter_id} for filter_id in filter_ids],
        "include_context": include_context,
        "include_time_range": include_time_range,
        "show_filter_form": False,
    }


def _custom_link(
    *filter_ids: str, include_context: bool = False, include_time_range: bool = False
) -> dict[str, object]:
    return {
        "type": "custom",
        "links": [
            _link(
                *filter_ids,
                include_context=include_context,
                include_time_range=include_time_range,
            )
        ],
    }


_LAST_FOUR_HOURS = {"from": "now-14400s", "to": "now"}


def _save_stats_widget(clients: ClientRegistry, widget_type: str, link: dict[str, object]) -> None:
    clients.DashboardClient.create_relative_grid_dashboard(
        create_dashboard_payload(
            _DASHBOARD, {_WIDGET: create_widget({"type": widget_type, "contextual_link": link})}
        )
    )


def _url(owner: UserId, part: str, *, context: object = None, **extra: str) -> str:
    query = urlencode(
        {
            "dashboard_name": _DASHBOARD,
            "dashboard_owner": owner,
            "widget_id": _WIDGET,
            "part": part,
            "link_index": "0",
            "context": json.dumps(context or {}),
        }
        | extra
    )
    return f"/NO_SITE/check_mk/dashboard_stats_link.py?{query}"


def _follow(
    app: WebTestAppForCMK,
    live: MockLiveStatusConnection,
    url: str,
    *,
    table: tuple[str, list[dict[str, object]]] = ("hosts", _HOSTS),
    object_query: str | None = None,
) -> dict[str, str]:
    """The variables of the URL the page redirects to."""
    if object_query is None:
        # Without an object query, the click must not reach Livestatus at all.
        response = app.get(url, status=HTTPStatus.FOUND)
    else:
        live.set_sites(["NO_SITE"])
        live.add_table(*table)
        live.expect_query(object_query, match_type="loose")
        with live():
            response = app.get(url, status=HTTPStatus.FOUND)
    location = urlparse(response.location)
    assert location.path == "view.py", response.location
    return dict(parse_qsl(location.query))


def test_a_click_opens_the_link_with_the_deferred_filters_valued_from_the_hosts_of_its_part(
    clients: ClientRegistry,
    with_automation_user: tuple[UserId, str],
    logged_in_admin_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    _save_stats_widget(clients, "host_stats", _custom_link("sites", "hostgroups"))

    # The downtime part counts db01 alone.
    variables = _follow(
        logged_in_admin_wsgi_app,
        mock_livestatus,
        _url(with_automation_user[0], "downtime"),
        object_query="GET hosts\nColumns: host_groups\nStats: state >= 0",
    )

    assert variables == {
        "view_name": "allhosts",
        "sites": "NO_SITE",
        "hostgroups": "all|db-servers",
        "filled_in": "filter",
        "_show_filter_form": "0",
    }


def test_a_click_on_the_total_values_the_deferred_filters_from_all_hosts(
    clients: ClientRegistry,
    with_automation_user: tuple[UserId, str],
    logged_in_admin_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    _save_stats_widget(clients, "host_stats", _custom_link("hostgroups"))

    variables = _follow(
        logged_in_admin_wsgi_app,
        mock_livestatus,
        _url(with_automation_user[0], "total"),
        object_query="GET hosts\nColumns: host_groups\nStats: state >= 0",
    )

    assert variables["hostgroups"] == "all|db-servers|we-servers"


def test_a_click_queries_the_hosts_of_its_part_within_the_widget_filters(
    clients: ClientRegistry,
    with_automation_user: tuple[UserId, str],
    logged_in_admin_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    _save_stats_widget(clients, "host_stats", _custom_link("sites"))

    _follow(
        logged_in_admin_wsgi_app,
        mock_livestatus,
        _url(with_automation_user[0], "downtime", context={"host": {"host": "db01"}}),
        # The part's filter adds to the widget's.
        object_query=(
            "GET hosts\nStats: state >= 0\nFilter: host_name = db01\n"
            "Filter: host_scheduled_downtime_depth != 0"
        ),
    )


def test_a_click_carries_the_widget_filters_and_names_the_dashboard_it_leaves(
    clients: ClientRegistry,
    with_automation_user: tuple[UserId, str],
    logged_in_admin_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    _save_stats_widget(clients, "host_stats", _custom_link("sites", include_context=True))

    variables = _follow(
        logged_in_admin_wsgi_app,
        mock_livestatus,
        _url(
            with_automation_user[0],
            "downtime",
            context={"host": {"host": "db01"}},
            _drilled_from="Overview",
        ),
        object_query="GET hosts\nStats: state >= 0",
    )

    assert variables["host"] == "db01"
    assert variables["_drilled_from"] == "Overview"


def test_a_click_queries_no_objects_without_a_deferred_filter(
    clients: ClientRegistry,
    with_automation_user: tuple[UserId, str],
    logged_in_admin_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    _save_stats_widget(clients, "host_stats", _custom_link("hoststate"))

    variables = _follow(
        logged_in_admin_wsgi_app, mock_livestatus, _url(with_automation_user[0], "down")
    )

    assert variables["hst1"] == "on"


def test_a_click_carries_the_time_range_its_link_includes(
    clients: ClientRegistry,
    with_automation_user: tuple[UserId, str],
    logged_in_admin_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    _save_stats_widget(clients, "host_stats", _custom_link("hoststate", include_time_range=True))

    variables = _follow(
        logged_in_admin_wsgi_app,
        mock_livestatus,
        _url(with_automation_user[0], "down", **_LAST_FOUR_HOURS),
    )

    assert {name: variables.get(name) for name in ("from", "to")} == _LAST_FOUR_HOURS


def test_a_click_leaves_out_the_time_range_its_link_leaves_out(
    clients: ClientRegistry,
    with_automation_user: tuple[UserId, str],
    logged_in_admin_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    _save_stats_widget(clients, "host_stats", _custom_link("hoststate"))

    variables = _follow(
        logged_in_admin_wsgi_app,
        mock_livestatus,
        _url(with_automation_user[0], "down", **_LAST_FOUR_HOURS),
    )

    assert "from" not in variables
    assert "to" not in variables


@pytest.mark.usefixtures("suppress_license_expiry_header", "patch_theme", "suppress_license_banner")
def test_a_click_with_half_a_time_range_is_rejected(
    clients: ClientRegistry,
    with_automation_user: tuple[UserId, str],
    logged_in_admin_wsgi_app: WebTestAppForCMK,
) -> None:
    _save_stats_widget(clients, "host_stats", _custom_link("hoststate", include_time_range=True))

    logged_in_admin_wsgi_app.get(
        _url(with_automation_user[0], "down", **{"from": "now-14400s"}),
        status=HTTPStatus.BAD_REQUEST,
    )


def test_a_click_queries_no_objects_for_another_links_deferred_filter(
    clients: ClientRegistry,
    with_automation_user: tuple[UserId, str],
    logged_in_admin_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    _save_stats_widget(
        clients, "host_stats", {"type": "custom", "links": [_link("hoststate"), _link("sites")]}
    )

    variables = _follow(
        logged_in_admin_wsgi_app, mock_livestatus, _url(with_automation_user[0], "down")
    )

    assert variables["hst1"] == "on"


def test_a_click_on_the_service_total_values_the_hard_states_of_all_services(
    clients: ClientRegistry,
    with_automation_user: tuple[UserId, str],
    logged_in_admin_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    _save_stats_widget(clients, "service_stats", _custom_link("svchardstate"))

    variables = _follow(
        logged_in_admin_wsgi_app,
        mock_livestatus,
        _url(with_automation_user[0], "total"),
        table=("services", _SERVICES),
        object_query=(
            "GET services\nColumns: service_description service_has_been_checked "
            "service_last_hard_state\nStats: state >= 0"
        ),
    )

    assert {name: variables.get(name) for name in ("hdst0", "hdst1", "hdst2")} == {
        "hdst0": "on",
        "hdst1": "on",
        "hdst2": "on",
    }


@pytest.mark.usefixtures("suppress_license_expiry_header", "patch_theme", "suppress_license_banner")
@pytest.mark.parametrize(
    "part, extra, error",
    [
        pytest.param("ok", {}, "The widget has no part &#x27;ok&#x27;.", id="unknown part"),
        pytest.param(
            "down",
            {"dashboard_name": "no_such_board"},
            "does not exist or you do not have permission",
            id="unknown dashboard",
        ),
        pytest.param("down", {"widget_id": "no_such_widget"}, "has no widget", id="unknown widget"),
    ],
)
def test_a_click_on_no_part_of_a_known_widget_tells_why(
    clients: ClientRegistry,
    with_automation_user: tuple[UserId, str],
    logged_in_admin_wsgi_app: WebTestAppForCMK,
    part: str,
    extra: dict[str, str],
    error: str,
) -> None:
    _save_stats_widget(clients, "host_stats", _custom_link("sites"))

    response = logged_in_admin_wsgi_app.get(
        _url(with_automation_user[0], part, **extra), status=HTTPStatus.BAD_REQUEST
    )

    assert error in response.text
