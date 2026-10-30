#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

import pytest

from cmk.graphing.v1 import translations
from cmk.graphing_engine import (
    ConsolidationFunction,
    HostName,
    MetricName,
    PerformanceDataRow,
    RRDFetchData,
    RRDMetric,
    Service,
    ServiceName,
    SiteID,
    TimeRange,
    TimeSeries,
)
from cmk.gui.graphing import (
    EvaluationOptions,
    HOST_PSEUDO_SERVICE,
    rrd_fetch_data,
    RRDFetchMetricNames,
    RRDFetchTimeSeries,
)
from cmk.gui.graphing._source import RRDFetchMetricNameMapping, RRDFetchPerformanceData
from cmk.livestatus_client.testing import MockLiveStatusConnection

_LOGGER = logging.getLogger(__name__)
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


@pytest.mark.usefixtures("load_config")
def test_fetch_metric_names_of_a_host_reads_the_hosts_table(
    mock_livestatus: MockLiveStatusConnection,
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
        resolved = RRDFetchMetricNames(
            host_name=HostName("h"), service_name=HOST_PSEUDO_SERVICE, debug=False
        )()

    assert resolved == {
        Service(
            site_id=SiteID("NO_SITE"), host_name=HostName("h"), service_name=HOST_PSEUDO_SERVICE
        ): frozenset({MetricName("x")})
    }


@pytest.mark.usefixtures("load_config")
def test_fetch_metric_names_of_a_service_reads_the_services_table(
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.set_sites(["NO_SITE"])
    mock_livestatus.add_table("services", [_SERVICE_ROW])
    mock_livestatus.expect_query(
        "GET services\nColumns: host_name description perf_data metrics check_command\n"
        "Filter: host_name = h\nFilter: description = svc\nAnd: 2\n"
    )

    with mock_livestatus():
        resolved = RRDFetchMetricNames(
            host_name=HostName("h"), service_name=ServiceName("svc"), debug=False
        )()

    assert resolved == {
        Service(
            site_id=SiteID("NO_SITE"), host_name=HostName("h"), service_name=ServiceName("svc")
        ): frozenset({MetricName("x")})
    }


@pytest.mark.usefixtures("load_config")
def test_fetch_metric_name_mapping_pairs_a_services_perfdata_names(
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    # The sibling fetcher only reports the canonical names, which cannot say which raw perf-data
    # column each came from. This one carries the pairing out of livestatus intact.
    translation = translations.Translation(
        name="translation_cpu_utilization",
        check_commands=[translations.PassiveCheck("cpu_utilization")],
        translations={"wait": translations.RenameTo("io_wait")},
    )
    mock_livestatus.set_sites(["NO_SITE"])
    mock_livestatus.add_table(
        "services",
        [
            {
                **_SERVICE_ROW,
                "perf_data": "wait=5",
                "metrics": ["wait"],
                "check_command": "check_mk-cpu_utilization",
            }
        ],
    )
    mock_livestatus.expect_query(
        "GET services\nColumns: host_name description perf_data metrics check_command\n"
        "Filter: host_name = h\nFilter: description = svc\nAnd: 2\n"
    )

    with mock_livestatus():
        mapping = RRDFetchMetricNameMapping(
            host_name=HostName("h"),
            service_name=ServiceName("svc"),
            debug=False,
            registered_translations=[translation],
        )()

    assert mapping == {
        Service(
            site_id=SiteID("NO_SITE"), host_name=HostName("h"), service_name=ServiceName("svc")
        ): {"wait": "io_wait"}
    }


@pytest.mark.usefixtures("load_config")
def test_fetch_data_of_a_host_metric_reads_the_hosts_table(
    mock_livestatus: MockLiveStatusConnection,
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
        [fetched] = RRDFetchData(
            consolidation_function=ConsolidationFunction.MAX,
            registered_translations=(),
            performance_data_source=RRDFetchPerformanceData(),
            time_series_source=RRDFetchTimeSeries(),
            now=0.0,
            debug=False,
            logger=_LOGGER,
        )(
            [metric],
            time_range=TimeRange(start=0, end=30, step=10),
        )[metric]

    assert fetched.performance_data is not None
    assert fetched.performance_data.value == 5.0
    assert fetched.time_series is not None
    assert list(fetched.time_series.values) == [1.0, 2.0, 3.0]


_A_WEEK_BEFORE_NOW = int(time.time()) - 7 * 24 * 60 * 60
_HALF_HOUR_A_WEEK_BEFORE_NOW = TimeRange(
    start=_A_WEEK_BEFORE_NOW - 30 * 60, end=_A_WEEK_BEFORE_NOW, step=60
)
_EDGE_METRIC = RRDMetric(
    site_id=SiteID("mysite"),
    host_name=HostName("h"),
    service_name=ServiceName("svc"),
    metric_name=MetricName("x"),
)


def _edge_performance_data(
    services: Sequence[Service],
    *,
    only_site: SiteID | None,  # noqa: ARG001
) -> Sequence[PerformanceDataRow]:
    return [
        PerformanceDataRow(
            service=service, site_id=SiteID("mysite"), perf_data="x=5", check_command="foo"
        )
        for service in services
    ]


@dataclass
class _RecordingRRD:
    asked_ranges: list[TimeRange] = field(default_factory=list)

    def __call__(
        self,
        rrd_metrics: Sequence[RRDMetric],  # noqa: ARG002
        *,
        consolidation_function: ConsolidationFunction,  # noqa: ARG002
        time_range: TimeRange,
        only_site: SiteID | None,  # noqa: ARG002
    ) -> Mapping[RRDMetric, TimeSeries]:
        self.asked_ranges.append(time_range)
        return {}


def test_a_request_for_edge_neighbours_reads_beyond_the_range() -> None:
    rrd = _RecordingRRD()
    rrd_fetch_data(
        EvaluationOptions(
            time_range=_HALF_HOUR_A_WEEK_BEFORE_NOW,
            consolidation_function=ConsolidationFunction.MAX,
            destination=None,
            include_edge_neighbours=True,
        ),
        _edge_performance_data,
        rrd,
        debug=False,
    )([_EDGE_METRIC], time_range=_HALF_HOUR_A_WEEK_BEFORE_NOW)
    assert rrd.asked_ranges[0].start < _HALF_HOUR_A_WEEK_BEFORE_NOW.start
