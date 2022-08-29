#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: Checkmk Enterprise License
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
from typing import Tuple

import pytest

from tests.unit.cmk.gui.conftest import WebTestAppForCMK

from cmk.utils import version
from cmk.utils.livestatus_helpers.testing import MockLiveStatusConnection
from cmk.utils.type_defs import UserId

if not version.is_raw_edition():
    from cmk.gui.cee.plugins.metrics.customgraphs import CustomGraphPage

from cmk.gui.pagetypes import OverridableInstances

GRAPH_ENDPOINT_TEMPLATE = "/NO_SITE/check_mk/api/1.0/domain-types/graph/actions/{name}/invoke"

not_in_cre = pytest.mark.skipif(version.is_raw_edition(), reason="Enpoint not available in CRE")


def endpoint(name: str) -> str:
    return GRAPH_ENDPOINT_TEMPLATE.format(name=name)


@not_in_cre
def test_openapi_graph_custom(
    wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
    with_automation_user: Tuple[str, str],
) -> None:
    mock_livestatus.set_sites(["NO_SITE"])
    username, _ = with_automation_user

    wsgi_app.set_authorization(("Bearer", " ".join(with_automation_user)))

    graph_spec = {
        "owner": username,
        "title": "My Cool Graph",
        "name": "my_cool_graph",
        "topic": CustomGraphPage.default_topic(),
        "context": {},
        "add_context_to_title": False,
    }
    new_page = CustomGraphPage(graph_spec)  # type: ignore
    instances: OverridableInstances[CustomGraphPage] = OverridableInstances()
    instances.add_page(new_page)
    CustomGraphPage.save_user_instances(instances, owner=UserId(username))

    with mock_livestatus():
        resp = wsgi_app.post(
            url=endpoint("get_custom_graph"),
            content_type="application/json",
            headers={"Accept": "application/json"},
            status=200,
            params=json.dumps(
                {
                    "spec": {"name": "my_cool_graph"},
                    "time_range": {"start": "1970-01-01T00:00:00Z", "end": "1970-01-01T00:00:30Z"},
                    "consolidation_function": "max",
                }
            ),
        )
    expected = {
        "curves": [],
        "step": 60,
        "time_range": {"end": "1970-01-01T00:00:30+00:00", "start": "1970-01-01T00:00:00+00:00"},
    }
    assert resp.json == expected


@pytest.mark.usefixtures("with_host")
@not_in_cre
def test_openapi_graph_named(
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
        "GET services\nColumns: perf_data metrics check_command\nFilter: host_name = heute\nFilter: service_description = CPU load\nColumnHeaders: off"
    )
    mock_livestatus.expect_query(
        "GET services\nColumns: rrddata:load1:load1.max:0.0:30.0:60\nFilter: host_name = heute\nFilter: service_description = CPU load\nColumnHeaders: off"
    )
    with mock_livestatus():
        resp = aut_user_auth_wsgi_app.post(
            url=endpoint("get_named_graph"),
            content_type="application/json",
            headers={"Accept": "application/json"},
            status=200,
            params=json.dumps(
                {
                    "spec": {
                        "site": "NO_SITE",
                        "host_name": "heute",
                        "service": "CPU load",
                        "graph_name": "cpu_load",
                    },
                    "time_range": {"start": "1970-01-01T00:00:00Z", "end": "1970-01-01T00:00:30Z"},
                    "consolidation_function": "max",
                }
            ),
        )
    expected = {
        "curves": [
            {
                "color": "#00d1ff",
                "line_type": "area",
                "rrd_data": [None],
                "title": "CPU load average of last minute",
            }
        ],
        "step": 60,
        "time_range": {"end": "1970-01-01T00:01:00+00:00", "start": "1970-01-01T00:00:00+00:00"},
    }
    assert resp.json == expected


@pytest.mark.usefixtures("with_host")
def test_openapi_graph_metric(
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
        "GET services\nColumns: perf_data metrics check_command\nFilter: host_name = heute\nFilter: service_description = CPU load\nColumnHeaders: off"
    )
    mock_livestatus.expect_query(
        "GET services\nColumns: rrddata:load1:load1.max:1.0:2.0:60\nFilter: host_name = heute\nFilter: service_description = CPU load\nColumnHeaders: off"
    )
    with mock_livestatus():
        resp = aut_user_auth_wsgi_app.post(
            url=endpoint("get_metric_graph"),
            content_type="application/json",
            headers={"Accept": "application/json"},
            status=200,
            params=json.dumps(
                {
                    "spec": {
                        "site": "NO_SITE",
                        "host_name": "heute",
                        "service": "CPU load",
                        "metric_name": "load1",
                    },
                    "time_range": {"start": "1970-01-01T00:00:01Z", "end": "1970-01-01T00:00:02Z"},
                    "consolidation_function": "max",
                }
            ),
        )
    expected = {
        "curves": [
            {
                "color": "#00d1ff",
                "line_type": "area",
                "rrd_data": [None],
                "title": "CPU load average of last minute",
            }
        ],
        "step": 60,
        "time_range": {"end": "1970-01-01T00:01:00+00:00", "start": "1970-01-01T00:00:00+00:00"},
    }
    assert resp.json == expected


@not_in_cre
def test_openapi_graph_combined(
    aut_user_auth_wsgi_app: WebTestAppForCMK, mock_livestatus: MockLiveStatusConnection
) -> None:
    with mock_livestatus():
        resp = aut_user_auth_wsgi_app.post(
            url=endpoint("get_combined_graph"),
            content_type="application/json",
            headers={"Accept": "application/json"},
            status=200,
            params=json.dumps(
                {
                    "spec": {
                        "filters": {"host": {"host": "heute"}, "siteopt": {"site": "heute"}},
                        "only_from": ["host"],
                        "graph_name": "cpu_utilization_5_util",
                        "presentation": "lines",
                    },
                    "time_range": {"start": "1970-01-01T00:00:00Z", "end": "1970-01-01T00:00:30Z"},
                    "consolidation_function": "max",
                }
            ),
        )
    expected = {
        "curves": [],
        "step": 60,
        "time_range": {"end": "1970-01-01T00:00:30+00:00", "start": "1970-01-01T00:00:00+00:00"},
    }
    assert resp.json == expected
