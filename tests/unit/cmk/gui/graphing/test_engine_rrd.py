#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing_engine import (
    ConsolidationFunction,
    HostName,
    MetricName,
    RRDMetric,
    Service,
    ServiceName,
    SiteID,
    TimeRange,
)
from cmk.gui.config import Config
from cmk.gui.graphing._engine_rrd import (
    EngineRRDFetchData,
    EngineRRDFetchMetricNames,
    HOST_PSEUDO_SERVICE,
    parse_performance_data,
)
from cmk.livestatus_client.testing import MockLiveStatusConnection

_HOST_ROW = {
    "name": "h",
    "perf_data": "x=5",
    "metrics": ["x"],
    "check_command": "check-mk-host-ping",
}
_SERVICE_ROW = {
    "host_name": "h",
    "description": "svc",
    "perf_data": "x=5",
    "metrics": ["x"],
    "check_command": "check_mk-foo",
}


def test_parse_performance_data_merges_rrd_only_metrics() -> None:
    # Legacy reads the livestatus "metrics" column too, so a metric present in RRD but absent from
    # the live perf_data string still shows up (as a synthetic value=1 entry, deduplicated).
    parsed = parse_performance_data("live=5", "check_mk-foo", ["live", "rrd_only"], debug=False)
    by_name = {name: value.value for name, value in parsed.values.items()}
    assert by_name == {"live": 5.0, "rrd_only": 1.0}


def test_fetch_metric_names_of_a_host_reads_the_hosts_table(
    load_config: Config, mock_livestatus: MockLiveStatusConnection
) -> None:
    # Host metrics are addressed by the pseudo-service "_HOST_" and live on the hosts table, where
    # they are filtered by host name alone - the table switch livestatus_lql makes for the legacy
    # fetch. Queried against the services table, a host graph would find no metrics at all.
    mock_livestatus.set_sites(["NO_SITE"])
    mock_livestatus.add_table("hosts", [_HOST_ROW])
    mock_livestatus.expect_query(
        "GET hosts\nColumns: name perf_data metrics check_command\nFilter: name = h\n"
    )

    with mock_livestatus():
        resolved = EngineRRDFetchMetricNames(
            host_name=HostName("h"), service_name=HOST_PSEUDO_SERVICE, debug=False
        )()

    assert resolved == {
        Service(
            site_id=SiteID("NO_SITE"), host_name=HostName("h"), service_name=HOST_PSEUDO_SERVICE
        ): frozenset({MetricName("x")})
    }


def test_fetch_metric_names_of_a_service_reads_the_services_table(
    load_config: Config, mock_livestatus: MockLiveStatusConnection
) -> None:
    mock_livestatus.set_sites(["NO_SITE"])
    mock_livestatus.add_table("services", [_SERVICE_ROW])
    mock_livestatus.expect_query(
        "GET services\nColumns: host_name description perf_data metrics check_command\n"
        "Filter: host_name = h\nFilter: description = svc\nAnd: 2\n"
    )

    with mock_livestatus():
        resolved = EngineRRDFetchMetricNames(
            host_name=HostName("h"), service_name=ServiceName("svc"), debug=False
        )()

    assert resolved == {
        Service(
            site_id=SiteID("NO_SITE"), host_name=HostName("h"), service_name=ServiceName("svc")
        ): frozenset({MetricName("x")})
    }


def test_fetch_data_of_a_host_metric_reads_the_hosts_table(
    load_config: Config, mock_livestatus: MockLiveStatusConnection
) -> None:
    # Both fetch stages of a host metric - the performance data and the RRD series - go to the hosts
    # table as well.
    metric = RRDMetric(
        site_id=SiteID("NO_SITE"),
        host_name=HostName("h"),
        service_name=HOST_PSEUDO_SERVICE,
        metric_name=MetricName("x"),
    )
    mock_livestatus.set_sites(["NO_SITE"])
    mock_livestatus.add_table(
        "hosts", [{**_HOST_ROW, "rrddata:x:x.max:0:30:10": [0, 30, 10, 1.0, 2.0, 3.0]}]
    )
    mock_livestatus.expect_query(
        "GET hosts\nColumns: name perf_data check_command\nFilter: name = h\n"
    )
    mock_livestatus.expect_query(
        "GET hosts\nColumns: name rrddata:x:x.max:0:30:10\nFilter: name = h\n"
    )

    with mock_livestatus():
        [fetched] = EngineRRDFetchData(debug=False)(
            [metric],
            consolidation_function=ConsolidationFunction.MAX,
            time_range=TimeRange(start=0, end=30, step=10),
        )[metric]

    assert fetched.performance_data is not None
    assert fetched.performance_data.value == 5.0
    assert fetched.time_series is not None
    assert list(fetched.time_series.values) == [1.0, 2.0, 3.0]
