#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from collections.abc import Sequence
from http import HTTPStatus
from typing import get_args

import pytest

from cmk.gui.dashboard.api.model.widget_content.monitoring_table import MonitoringTableContent
from cmk.gui.dashboard.dashlet.dashlets.monitoring_table import MonitoringTableDashlet
from cmk.gui.dashboard.monitoring_tables import MONITORING_TABLES
from cmk.gui.dashboard.type_defs import MonitoringTableName
from cmk.livestatus_client.testing import MockLiveStatusConnection
from tests.testlib.unit.rest_api_client import ClientRegistry, Response
from tests.unit.cmk.gui.helpers.dashboard_api_test_helper import (
    create_dashboard_payload,
    create_widget,
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


def test_every_monitoring_table_is_registered() -> None:
    assert set(MONITORING_TABLES) == set(get_args(MonitoringTableName.__value__))
