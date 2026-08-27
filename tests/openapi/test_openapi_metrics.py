#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

import pytest

from cmk.gui.graphing import GraphConsolidationFunction
from cmk.livestatus_client.testing import MockLiveStatusConnection
from tests.testlib.gui.web_test_app import WebTestAppForCMK
from tests.testlib.rest_api_client import RestApiClient

GRAPH_ENDPOINT_GET = "/NO_SITE/check_mk/api/1.0/domain-types/metric/actions/get/invoke"
COLOR_HEX = "#6fc1f7"


@pytest.mark.usefixtures("with_host")
@pytest.mark.parametrize("consolidation_function", ["min", "max", "average"])
def test_openapi_get_graph_graph(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
    consolidation_function: GraphConsolidationFunction,
) -> None:
    mock_livestatus.set_sites(["NO_SITE"])
    mock_livestatus.add_table(
        "services",
        [
            {
                "check_command": "check_mk-cpu_loads",
                "description": "CPU load",
                "host_name": "heute",
                "metrics": [
                    "load1"
                ],  # please don't add another metric, it might make the test non-deterministic
                "perf_data": "load1=2.22;;;0;8",
            }
        ],
    )
    mock_livestatus.expect_query(
        # hostfield with should_be_monitored=True
        "GET hosts\nColumns: name\nFilter: name = heute"
    )
    mock_livestatus.expect_query(
        "GET services\nColumns: host_name description perf_data metrics check_command\n"
        "Filter: host_name = heute\nFilter: description = CPU load\nAnd: 2\n"
    )
    mock_livestatus.expect_query(
        "GET services\nColumns: host_name description perf_data check_command\n"
        "Filter: host_name = heute\nFilter: description = CPU load\nAnd: 2\n"
    )
    mock_livestatus.expect_query(
        "GET services\nColumns: host_name description "
        f"rrddata:load1:load1.{consolidation_function}:0:30:60 "
        f"rrddata:load15:load15.{consolidation_function}:0:30:60 "
        f"rrddata:load5:load5.{consolidation_function}:0:30:60\n"
        "Filter: host_name = heute\nFilter: description = CPU load\nAnd: 2\n"
    )
    with mock_livestatus():
        resp = aut_user_auth_wsgi_app.post(
            url=GRAPH_ENDPOINT_GET,
            content_type="application/json",
            headers={"Accept": "application/json"},
            status=200,
            params=json.dumps(
                {
                    "site": "NO_SITE",
                    "host_name": "heute",
                    "service_description": "CPU load",
                    "type": "predefined_graph",
                    "graph_id": "cpu_load",
                    "time_range": {"start": "1970-01-01T00:00:00Z", "end": "1970-01-01T00:00:30Z"},
                    "reduce": consolidation_function,
                }
            ),
        )
    expected = {
        "metrics": [
            {
                "color": COLOR_HEX,
                "line_type": "area",
                "data_points": [],
                "title": "CPU load average of last minute",
            }
        ],
        "step": 60,
        "time_range": {"start": "1970-01-01T00:00:00+00:00", "end": "1970-01-01T00:00:30+00:00"},
    }
    assert resp.json == expected


@pytest.mark.usefixtures("with_host")
def test_openapi_get_graph_unknown_graph_id_is_a_bad_request(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.set_sites(["NO_SITE"])
    mock_livestatus.expect_query(
        # hostfield with should_be_monitored=True
        "GET hosts\nColumns: name\nFilter: name = heute"
    )
    with mock_livestatus():
        resp = aut_user_auth_wsgi_app.post(
            url=GRAPH_ENDPOINT_GET,
            content_type="application/json",
            headers={"Accept": "application/json"},
            status=400,
            params=json.dumps(
                {
                    "site": "NO_SITE",
                    "host_name": "heute",
                    "service_description": "CPU load",
                    "type": "predefined_graph",
                    "graph_id": "does_not_exist",
                    "time_range": {"start": "1970-01-01T00:00:00Z", "end": "1970-01-01T00:00:30Z"},
                    "reduce": "max",
                }
            ),
        )

    assert "does_not_exist" in resp.json["detail"]


@pytest.mark.usefixtures("with_host")
@pytest.mark.parametrize("consolidation_function", ["min", "max", "average"])
def test_openapi_get_graph_metric(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
    consolidation_function: GraphConsolidationFunction,
) -> None:
    mock_livestatus.set_sites(["NO_SITE"])
    mock_livestatus.add_table(
        "services",
        [
            {
                "check_command": "check_mk-cpu_loads",
                "description": "CPU load",
                "host_name": "heute",
                "metrics": ["load1"],
                "perf_data": "load1=2.22;;;0;8",
            }
        ],
    )
    mock_livestatus.expect_query(
        # hostfield with should_be_monitored=True
        "GET hosts\nColumns: name\nFilter: name = heute"
    )
    mock_livestatus.expect_query(
        "GET services\nColumns: host_name description perf_data metrics check_command\n"
        "Filter: host_name = heute\nFilter: description = CPU load\nAnd: 2\n"
    )
    mock_livestatus.expect_query(
        "GET services\nColumns: host_name description perf_data check_command\n"
        "Filter: host_name = heute\nFilter: description = CPU load\nAnd: 2\n"
    )
    mock_livestatus.expect_query(
        f"GET services\nColumns: host_name description rrddata:load1:load1.{consolidation_function}:1:2:60\n"
        "Filter: host_name = heute\nFilter: description = CPU load\nAnd: 2\n"
    )
    with mock_livestatus():
        resp = aut_user_auth_wsgi_app.post(
            url=GRAPH_ENDPOINT_GET,
            content_type="application/json",
            headers={"Accept": "application/json"},
            status=200,
            params=json.dumps(
                {
                    "site": "NO_SITE",
                    "host_name": "heute",
                    "service_description": "CPU load",
                    "metric_id": "load1",
                    "type": "single_metric",
                    "time_range": {"start": "1970-01-01T00:00:01Z", "end": "1970-01-01T00:00:02Z"},
                    "reduce": consolidation_function,
                }
            ),
        )
    expected = {
        "metrics": [
            {
                "color": COLOR_HEX,
                "line_type": "area",
                "data_points": [],
                "title": "CPU load average of last minute",
            }
        ],
        "step": 60,
        "time_range": {"start": "1970-01-01T00:00:01+00:00", "end": "1970-01-01T00:00:02+00:00"},
    }
    assert resp.json == expected


@pytest.mark.usefixtures("with_host")
@pytest.mark.parametrize("consolidation_function", ["min", "max", "average"])
def test_openapi_get_graph_metric_without_site(
    api_client: RestApiClient,
    mock_livestatus: MockLiveStatusConnection,
    consolidation_function: GraphConsolidationFunction,
) -> None:
    mock_livestatus.set_sites(["NO_SITE"])
    mock_livestatus.add_table(
        "services",
        [
            {
                "check_command": "check_mk-cpu_loads",
                "description": "CPU load",
                "host_name": "heute",
                "metrics": ["load1"],
                "perf_data": "load1=2.22;;;0;8",
            }
        ],
    )
    mock_livestatus.expect_query(
        # hostfield with should_be_monitored=True
        "GET hosts\nColumns: name\nFilter: name = heute"
    )
    mock_livestatus.expect_query(
        "GET services\nColumns: host_name description perf_data metrics check_command\n"
        "Filter: host_name = heute\nFilter: description = CPU load\nAnd: 2\n"
    )
    mock_livestatus.expect_query(
        "GET services\nColumns: host_name description perf_data check_command\n"
        "Filter: host_name = heute\nFilter: description = CPU load\nAnd: 2\n"
    )
    mock_livestatus.expect_query(
        f"GET services\nColumns: host_name description rrddata:load1:load1.{consolidation_function}:1:2:60\n"
        "Filter: host_name = heute\nFilter: description = CPU load\nAnd: 2\n"
    )
    with mock_livestatus():
        resp = api_client.get_graph(
            host_name="heute",
            service_description="CPU load",
            graph_or_metric_id="load1",
            type_="single_metric",
            time_range={"start": "1970-01-01T00:00:01Z", "end": "1970-01-01T00:00:02Z"},
            reduce=consolidation_function,
        )
    expected = {
        "metrics": [
            {
                "color": COLOR_HEX,
                "line_type": "area",
                "data_points": [],
                "title": "CPU load average of last minute",
            }
        ],
        "step": 60,
        "time_range": {"start": "1970-01-01T00:00:01+00:00", "end": "1970-01-01T00:00:02+00:00"},
    }
    assert resp.json == expected
