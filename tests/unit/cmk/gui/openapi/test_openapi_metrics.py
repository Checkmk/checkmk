#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

import pytest

from cmk.utils.livestatus_helpers.testing import MockLiveStatusConnection
from tests.testlib.unit.rest_api_client import RestApiClient
from tests.unit.cmk.web_test_app import WebTestAppForCMK

GRAPH_ENDPOINT_GET = "/NO_SITE/check_mk/api/1.0/domain-types/metric/actions/get/invoke"
COLOR_HEX = "#87cefa"


@pytest.mark.usefixtures("with_host")
def test_openapi_get_graph_graph(
    aut_user_auth_wsgi_app: WebTestAppForCMK, mock_livestatus: MockLiveStatusConnection
) -> None:
    mock_livestatus.set_sites(["NO_SITE"])
    mock_livestatus.add_table(
        "services",
        [
            {
                "check_command": "check_mk-cpu_loads",
                "service_description": "CPU load",
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
        "GET services\nColumns: perf_data metrics check_command\nFilter: host_name = heute\nFilter: service_description = CPU load\nColumnHeaders: off"
    )
    mock_livestatus.expect_query(
        "GET services\nColumns: rrddata:load1:load1.average:0:30:60\nFilter: host_name = heute\nFilter: service_description = CPU load\nColumnHeaders: off"
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
                }
            ),
        )
    expected = {
        "metrics": [
            {
                "color": COLOR_HEX,
                "line_type": "stack",
                "data_points": [None],
                "title": "CPU load average of last minute",
            }
        ],
        "step": 60,
        "time_range": {"end": "1970-01-01T00:01:00+00:00", "start": "1970-01-01T00:00:00+00:00"},
    }
    assert resp.json == expected


@pytest.mark.usefixtures("with_host")
def test_openapi_get_graph_metric(
    aut_user_auth_wsgi_app: WebTestAppForCMK, mock_livestatus: MockLiveStatusConnection
) -> None:
    mock_livestatus.set_sites(["NO_SITE"])
    mock_livestatus.add_table(
        "services",
        [
            {
                "check_command": "check_mk-cpu_loads",
                "service_description": "CPU load",
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
        "GET services\nColumns: perf_data metrics check_command\nFilter: host_name = heute\nFilter: service_description = CPU load\nColumnHeaders: off"
    )
    mock_livestatus.expect_query(
        "GET services\nColumns: rrddata:load1:load1.average:1:2:60\nFilter: host_name = heute\nFilter: service_description = CPU load\nColumnHeaders: off"
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
                }
            ),
        )
    expected = {
        "metrics": [
            {
                "color": COLOR_HEX,
                "line_type": "area",
                "data_points": [None],
                "title": "CPU load average of last minute",
            }
        ],
        "step": 60,
        "time_range": {"end": "1970-01-01T00:01:00+00:00", "start": "1970-01-01T00:00:00+00:00"},
    }
    assert resp.json == expected


@pytest.mark.usefixtures("with_host")
def test_openapi_get_graph_metric_without_site(
    api_client: RestApiClient, mock_livestatus: MockLiveStatusConnection
) -> None:
    mock_livestatus.set_sites(["NO_SITE"])
    mock_livestatus.add_table(
        "services",
        [
            {
                "check_command": "check_mk-cpu_loads",
                "service_description": "CPU load",
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
        "GET services\nColumns: perf_data metrics check_command\nFilter: host_name = heute\nFilter: service_description = CPU load\nColumnHeaders: off"
    )
    mock_livestatus.expect_query(
        "GET services\nColumns: rrddata:load1:load1.average:1:2:60\nFilter: host_name = heute\nFilter: service_description = CPU load\nColumnHeaders: off"
    )
    with mock_livestatus():
        resp = api_client.get_graph(
            host_name="heute",
            service_description="CPU load",
            graph_or_metric_id="load1",
            type_="single_metric",
            time_range={"start": "1970-01-01T00:00:01Z", "end": "1970-01-01T00:00:02Z"},
        )
    expected = {
        "metrics": [
            {
                "color": COLOR_HEX,
                "line_type": "area",
                "data_points": [None],
                "title": "CPU load average of last minute",
            }
        ],
        "step": 60,
        "time_range": {"end": "1970-01-01T00:01:00+00:00", "start": "1970-01-01T00:00:00+00:00"},
    }
    assert resp.json == expected
