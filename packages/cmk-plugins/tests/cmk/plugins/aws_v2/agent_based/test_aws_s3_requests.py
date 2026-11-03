#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Callable, Mapping

import pytest

from cmk.agent_based.v2 import (
    CheckResult,
    DiscoveryResult,
    IgnoreResultsError,
    Metric,
    Result,
    Service,
    State,
)
from cmk.plugins.aws_v2.agent_based.aws_s3_requests import (
    check_aws_s3_http_errors,
    check_aws_s3_latency,
    check_aws_s3_requests,
    check_aws_s3_select_object,
    check_aws_s3_traffic_stats,
    discover_aws_s3_requests,
    discover_aws_s3_requests_http_errors,
    discover_aws_s3_requests_latency,
    discover_aws_s3_requests_select_object,
    discover_aws_s3_requests_traffic_stats,
    parse_aws_s3_requests,
    Section,
)

_DISCOVERY_FUNCTIONS = [
    discover_aws_s3_requests,
    discover_aws_s3_requests_http_errors,
    discover_aws_s3_requests_latency,
    discover_aws_s3_requests_traffic_stats,
    discover_aws_s3_requests_select_object,
]

_CHECK_FUNCTIONS: list[Callable[[Section], CheckResult]] = [
    lambda section: check_aws_s3_requests({}, section),
    lambda section: check_aws_s3_http_errors({}, section),
    lambda section: check_aws_s3_latency({}, section),
    check_aws_s3_traffic_stats,
    check_aws_s3_select_object,
]


def _section(values: Mapping[str, float]) -> Section:
    rows = [
        {
            "Id": f"id_0_{name}",
            "Label": "my-bucket",
            "Timestamps": ["2026-11-03 10:00:00+00:00"],
            "Values": [[value, None]],
            "StatusCode": "Complete",
        }
        for name, value in values.items()
    ]
    return parse_aws_s3_requests([[json.dumps(rows)]])


_FULL_SECTION = {
    "AllRequests": 10.0,
    "GetRequests": 5.0,
    "PutRequests": 2.0,
    "DeleteRequests": 1.0,
    "HeadRequests": 1.0,
    "PostRequests": 1.0,
    "SelectRequests": 0.0,
    "ListRequests": 0.0,
    "4xxErrors": 1.0,
    "5xxErrors": 0.0,
    "FirstByteLatency": 20.0,
    "TotalRequestLatency": 30.0,
    "BytesDownloaded": 100.0,
    "BytesUploaded": 200.0,
    "SelectBytesScanned": 300.0,
    "SelectBytesReturned": 400.0,
}


def test_parse_takes_the_metrics_of_the_bucket_on_the_bucket_host() -> None:
    assert _section({"AllRequests": 10.0, "4xxErrors": 1.0}) == {
        "AllRequests": 10.0,
        "4xxErrors": 1.0,
    }


@pytest.mark.parametrize("discover", _DISCOVERY_FUNCTIONS)
def test_discovery_creates_one_service_without_item(
    discover: Callable[[Section], DiscoveryResult],
) -> None:
    assert list(discover(_section(_FULL_SECTION))) == [Service()]


@pytest.mark.parametrize("discover", _DISCOVERY_FUNCTIONS)
def test_discovery_creates_no_service_without_request_metrics(
    discover: Callable[[Section], DiscoveryResult],
) -> None:
    assert not list(discover(_section({})))


@pytest.mark.parametrize("check", _CHECK_FUNCTIONS)
def test_check_goes_stale_without_data(check: Callable[[Section], CheckResult]) -> None:
    with pytest.raises(IgnoreResultsError):
        list(check(_section({})))


def test_check_requests_reports_the_request_types() -> None:
    results = list(
        check_aws_s3_requests({"get_requests_perc": (40.0, 60.0)}, _section(_FULL_SECTION))
    )

    assert results[0] == Result(state=State.OK, summary="Total: 10.000/s")
    assert results[1:5] == [
        Result(state=State.OK, summary="Get: 5.000/s"),
        Metric("get_requests", 5.0),
        Result(
            state=State.WARN, summary="Get of total requests: 50.00% (warn/crit at 40.00%/60.00%)"
        ),
        Metric("get_requests_perc", 50.0, levels=(40.0, 60.0)),
    ]
