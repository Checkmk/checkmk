#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The lookups the Maps SPA's pickers, drawer and state layer read.

Called through the WSGI app, like the SPA does, because the framework's
permission tracker raises in tests for any permission an endpoint checks without
declaring it: each test also pins its endpoint's declaration.
"""

import pytest

from cmk.livestatus_client.testing import MockLiveStatusConnection
from tests.testlib.unit.rest_api_client import ClientRegistry


def _expect_bi_compile(live: MockLiveStatusConnection) -> None:
    # The BI compiler reads each core's start time, to know whether to recompile,
    # and then the host structure it compiles against.
    live.expect_query("GET status\nColumns: program_start")
    live.expect_query("GET status\nColumns: program_start")
    live.expect_query(
        "GET hosts\nColumns: host_name host_tags host_labels host_childs host_parents host_alias "
        "host_filename",
        sites=["NO_SITE"],
    )


_MEMBER_COLUMNS = (
    "name state plugin_output acknowledged scheduled_downtime_depth notifications_enabled "
    "last_state_change"
)


@pytest.mark.usefixtures("request_context")
def test_host_geo(clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection) -> None:
    mock_livestatus.expect_query(
        "GET hosts\nColumns: labels custom_variable_names custom_variable_values\n"
        "Filter: name = heute"
    )
    with mock_livestatus:
        assert clients.Maps.get_host_geo("heute").json["geo"] is None


@pytest.mark.usefixtures("request_context")
def test_perf_metrics(clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection) -> None:
    mock_livestatus.expect_query("GET hosts\nColumns: perf_data\nFilter: name = heute")
    with mock_livestatus:
        assert "perf_data" in clients.Maps.get_perf_metrics("heute").json


@pytest.mark.usefixtures("request_context")
def test_group_members(clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection) -> None:
    mock_livestatus.expect_query(f"GET hosts\nColumns: {_MEMBER_COLUMNS}\nFilter: groups >= linux")
    with mock_livestatus:
        assert clients.Maps.get_group_members("hostgroup", "linux").json["members"] == []


@pytest.mark.usefixtures("request_context")
def test_dyngroup_members(
    clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection
) -> None:
    mock_livestatus.expect_query(f"GET hosts\nColumns: {_MEMBER_COLUMNS}\nFilter: name = heute")
    with mock_livestatus:
        assert "members" in clients.Maps.get_dyngroup_members("Filter: name = heute\n").json


def test_folders(clients: ClientRegistry) -> None:
    assert "" in [folder["path"] for folder in clients.Maps.get_folders().json["folders"]]


def test_sites(clients: ClientRegistry) -> None:
    assert "NO_SITE" in [site["id"] for site in clients.Maps.get_sites().json["sites"]]


def test_metric_info(clients: ClientRegistry) -> None:
    resp = clients.Maps.resolve_metric_info(
        {"perf_data": "load1=0.5;;;0;", "check_command": "check_mk-cpu_loads"}
    )
    assert "metrics" in resp.json


@pytest.mark.usefixtures("allow_redis")
def test_aggregations(clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection) -> None:
    _expect_bi_compile(mock_livestatus)
    with mock_livestatus:
        assert clients.Maps.get_aggregations().json["aggregations"] == []


@pytest.mark.usefixtures("allow_redis")
def test_aggregation_tree_of_an_unknown_aggregation(
    clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection
) -> None:
    _expect_bi_compile(mock_livestatus)
    with mock_livestatus:
        assert clients.Maps.get_aggregation_tree("unknown").json["tree"] is None


@pytest.mark.usefixtures("allow_redis")
def test_aggregation_states_of_an_unknown_aggregation(
    clients: ClientRegistry, mock_livestatus: MockLiveStatusConnection
) -> None:
    _expect_bi_compile(mock_livestatus)
    with mock_livestatus:
        assert clients.Maps.get_aggregation_states(["unknown"]).json["states"] == {}


def test_images(clients: ClientRegistry) -> None:
    assert "bell.svg" in [image["name"] for image in clients.Maps.get_images().json["images"]]


def test_image_usage(clients: ClientRegistry) -> None:
    assert clients.Maps.get_image_usage("bell.svg").json["usage"] == []


def test_authoring_settings(clients: ClientRegistry) -> None:
    assert clients.Maps.get_authoring_settings().json
