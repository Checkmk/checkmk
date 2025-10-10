#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"

from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any
from unittest import mock
from unittest.mock import Mock

import pytest
import time_machine

from cmk.agent_based.v2 import CheckPlugin, Metric, Result, State
from cmk.plugins.azure_v2.agent_based import azure_redis
from cmk.plugins.lib.azure import AzureMetric, Resource, Section

AZURE_REDIS_WITH_METRICS = {
    "az-redis-test": Resource(
        id=(
            "/subscriptions/ba9f74ff-6a4c-41e0-ab55-15c7fe79632f/resourceGroups/test-rg/"
            "providers/Microsoft.Cache/Redis/az-redis-test"
        ),
        name="az-redis-test",
        type="Microsoft.Cache/Redis",
        group="test-rg",
        kind=None,
        location="germanywestcentral",
        tags={},
        properties={},
        specific_info={},
        metrics={
            "maximum_allconnectedclients": AzureMetric(
                name="allconnectedclients",
                aggregation="maximum",
                value=3,
                unit="count",
            ),
            "maximum_allConnectionsCreatedPerSecond": AzureMetric(
                name="allConnectionsCreatedPerSecond",
                aggregation="maximum",
                value=2,
                unit="countpersecond",
            ),
            "maximum_allConnectionsClosedPerSecond": AzureMetric(
                name="allConnectionsClosedPerSecond",
                aggregation="maximum",
                value=2,
                unit="countpersecond",
            ),
            "maximum_allpercentprocessortime": AzureMetric(
                name="allpercentprocessortime",
                aggregation="maximum",
                value=25,
                unit="percent",
            ),
            "total_allcachehits": AzureMetric(
                name="allcachehits",
                aggregation="total",
                value=385,
                unit="count",
            ),
            "total_allcachemisses": AzureMetric(
                name="allcachemisses",
                aggregation="total",
                value=99,
                unit="count",
            ),
            "total_cachemissrate": AzureMetric(
                name="cachemissrate",
                aggregation="total",
                value=20.454545454545457,
                unit="percent",
            ),
            "total_allgetcommands": AzureMetric(
                name="allgetcommands",
                aggregation="total",
                value=484,
                unit="count",
            ),
            "total_allusedmemorypercentage": AzureMetric(
                name="allusedmemorypercentage",
                aggregation="total",
                value=29,
                unit="percent",
            ),
            "total_allusedmemoryRss": AzureMetric(
                name="allusedmemoryRss",
                aggregation="total",
                value=60170240,
                unit="bytes",
            ),
            "total_allevictedkeys": AzureMetric(
                name="allevictedkeys",
                aggregation="total",
                value=42,
                unit="count",
            ),
            "total_allexpiredkeys": AzureMetric(
                name="allexpiredkeys",
                aggregation="total",
                value=140,
                unit="count",
            ),
            "average_LatencyP99": AzureMetric(
                name="LatencyP99",
                aggregation="average",
                value=19765,
                unit="count",
            ),
            "average_cacheLatency": AzureMetric(
                name="cacheLatency",
                aggregation="average",
                value=11469.8,
                unit="count",
            ),
            "minimum_GeoReplicationHealthy": AzureMetric(
                name="GeoReplicationHealthy",
                aggregation="minimum",
                value=1,
                unit="count",
            ),
            "average_GeoReplicationConnectivityLag": AzureMetric(
                name="GeoReplicationConnectivityLag",
                aggregation="average",
                value=2.5,
                unit="seconds",
            ),
            "maximum_allcacheRead": AzureMetric(
                name="allcacheRead",
                aggregation="maximum",
                value=40706,
                unit="bytespersecond",
            ),
            "maximum_allcacheWrite": AzureMetric(
                name="allcacheWrite",
                aggregation="maximum",
                value=31375,
                unit="bytespersecond",
            ),
            "maximum_serverLoad": AzureMetric(
                name="serverLoad",
                aggregation="maximum",
                value=26,
                unit="percent",
            ),
        },
        subscription="ba9f74ff-6a4c-41e0-ab55-15c7fe79632f",
    ),
}

EPOCH = 1757328437.8742359


def resource_fixture_but(**kwargs):
    """
    Return a copy of AZURE_REDIS_WITH_METRICS, but with some metric values
    overridden.
    """
    resources = deepcopy(AZURE_REDIS_WITH_METRICS)
    for k, v in kwargs.items():
        metric = resources["az-redis-test"].metrics[k]
        assert isinstance(resources["az-redis-test"].metrics, dict)  # Hack, mypy
        resources["az-redis-test"].metrics[k] = metric._replace(value=v)
    return resources


@pytest.mark.parametrize(
    "section, params, check_plugin, expected_result",
    [
        pytest.param(
            AZURE_REDIS_WITH_METRICS,
            {},
            azure_redis.check_plugin_azure_redis_connections,
            [
                Result(state=State.OK, summary="Connected clients: 3"),
                Metric("azure_redis_clients_connected", 3.0),
                Result(state=State.OK, summary="Created: 2/s"),
                Metric("azure_redis_created_connection_rate", 2.0),
                Result(state=State.OK, summary="Closed: 2/s"),
                Metric("azure_redis_closed_connection_rate", 2.0),
            ],
            id="redis connections",
        ),
        pytest.param(
            AZURE_REDIS_WITH_METRICS,
            {},
            azure_redis.check_plugin_azure_redis_cpu_utilization,
            [
                Result(state=State.OK, summary="Total CPU: 25.00%"),
                Metric("util", 25.0),
            ],
            id="redis CPU utilization",
        ),
        pytest.param(
            AZURE_REDIS_WITH_METRICS,
            {
                "cpu_utilization": ("fixed", (24.0, 30.0)),
            },
            azure_redis.check_plugin_azure_redis_cpu_utilization,
            [
                Result(state=State.WARN, summary="Total CPU: 25.00% (warn/crit at 24.00%/30.00%)"),
                Metric("util", 25.0, levels=(24.0, 30.0)),
            ],
            id="redis CPU utilization with explicit levels",
        ),
        pytest.param(
            AZURE_REDIS_WITH_METRICS,
            {
                "cache_hit_ratio": ("fixed", (85.0, 80.0)),
            },
            azure_redis.check_plugin_azure_redis_cache_effectiveness,
            [
                Result(
                    state=State.CRIT, summary="Hit ratio: 79.55% (warn/crit below 85.00%/80.00%)"
                ),
                Metric("azure_redis_cache_hit_ratio", 79.54545454545455),
                Result(state=State.OK, summary="Cache hits: 385"),
                Metric("azure_redis_cache_hits", 385.0),
                Result(state=State.OK, summary="Cache misses: 99"),
                Metric("azure_redis_cache_misses", 99.0),
                Result(state=State.OK, notice="Gets: 484"),
                Metric("azure_redis_gets", 484.0),
            ],
            id="redis Cache effectiveness",
        ),
        pytest.param(
            AZURE_REDIS_WITH_METRICS,
            {
                "memory_util": ("fixed", (20.0, 30.0)),
                "evicted_keys": ("fixed", (35, 40)),
            },
            azure_redis.check_plugin_azure_redis_memory,
            [
                Result(
                    state=State.WARN,
                    summary="Memory utilization: 29.00% (warn/crit at 20.00%/30.00%)",
                ),
                Metric("azure_redis_memory_utilization", 29.0, levels=(20.0, 30.0)),
                Result(state=State.OK, notice="Used memory RSS: 57.4 MiB"),
                Metric("azure_redis_used_memory_rss", 60170240.0),
                Result(state=State.CRIT, summary="Evicted keys: 42 (warn/crit at 35/40)"),
                Metric("azure_redis_evicted_keys", 42.0, levels=(35, 40)),
                Result(state=State.OK, summary="Expired keys: 140"),
                Metric("azure_redis_expired_keys", 140.0),
            ],
            id="redis memory",
        ),
        pytest.param(
            AZURE_REDIS_WITH_METRICS,
            {
                "serverside_upper": ("fixed", (0.019, 0.05)),
                "internode_upper": ("fixed", (0.009, 0.01)),
            },
            azure_redis.check_plugin_azure_redis_latency,
            [
                Result(
                    state=State.WARN,
                    summary="Server-side: 20 milliseconds (warn/crit at 19 milliseconds/50 milliseconds)",
                ),
                Metric("azure_redis_latency_serverside", 0.019765, levels=(0.019, 0.05)),
                Result(
                    state=State.CRIT,
                    summary="Cache internode: 11 milliseconds (warn/crit at 9 milliseconds/10 milliseconds)",
                ),
                Metric("azure_redis_latency_internode", 0.011469799999999999, levels=(0.009, 0.01)),
            ],
            id="redis latency",
        ),
        pytest.param(
            resource_fixture_but(average_cacheLatency=760403.8),
            azure_redis.check_plugin_azure_redis_latency.check_default_parameters,
            azure_redis.check_plugin_azure_redis_latency,
            [
                Result(state=State.OK, summary="Server-side: 20 milliseconds"),
                Metric("azure_redis_latency_serverside", 0.019765),
                Result(
                    state=State.WARN,
                    summary="Cache internode: 760 milliseconds (warn/crit at 500 milliseconds/1 second)",
                ),
                Metric("azure_redis_latency_internode", 0.7604038000000001, levels=(0.5, 1.0)),
            ],
            id="redis latency, default threshold (warn)",
        ),
        pytest.param(
            AZURE_REDIS_WITH_METRICS,
            {
                "replication_connectivity_lag_upper": ("fixed", (0.3, 1.0)),
            },
            azure_redis.check_plugin_azure_redis_replication,
            [
                Result(state=State.OK, summary="Healthy"),
                Result(
                    state=State.CRIT,
                    summary="Connectivity lag: 2 seconds (warn/crit at 300 milliseconds/1 second)",
                ),
                Metric("azure_redis_replication_connectivity_lag", 2.5, levels=(0.3, 1.0)),
            ],
            id="redis replication",
        ),
        pytest.param(
            resource_fixture_but(
                minimum_GeoReplicationHealthy=0,
                average_GeoReplicationConnectivityLag=20.0,
            ),
            {
                "replication_connectivity_lag_upper": ("fixed", (0.3, 1.0)),
                "replication_unhealthy_status": State.WARN,
            },
            azure_redis.check_plugin_azure_redis_replication,
            [
                Result(state=State.WARN, summary="Unhealthy"),
                Result(
                    state=State.CRIT,
                    summary="Connectivity lag: 20 seconds (warn/crit at 300 milliseconds/1 second)",
                ),
                Metric("azure_redis_replication_connectivity_lag", 20.0, levels=(0.3, 1.0)),
            ],
            id="redis replication with unhealthy geo link",
        ),
        pytest.param(
            AZURE_REDIS_WITH_METRICS,
            {
                "cache_read_upper": ("fixed", (38_000, 60_000)),
                "cache_write_upper": ("fixed", (33_000, 38_000)),
            },
            azure_redis.check_plugin_azure_redis_throughput,
            [
                Result(
                    state=State.WARN, summary="Read: 40.7 kB/s (warn/crit at 38.0 kB/s/60.0 kB/s)"
                ),
                Metric("azure_redis_throughput_cache_read", 40706.0, levels=(38000.0, 60000.0)),
                Result(state=State.OK, summary="Write: 31.4 kB/s"),
                Metric("azure_redis_throughput_cache_write", 31375.0, levels=(33000.0, 38000.0)),
            ],
            id="redis throughput",
        ),
        pytest.param(
            AZURE_REDIS_WITH_METRICS,
            {},
            azure_redis.check_plugin_azure_redis_server_load,
            [
                Result(state=State.OK, summary="Server load: 26.00%"),
                Metric("azure_redis_server_load", 26.0),
            ],
            id="redis server load (no params)",
        ),
        pytest.param(
            resource_fixture_but(maximum_serverLoad=87.0),
            azure_redis.check_plugin_azure_redis_server_load.check_default_parameters,
            azure_redis.check_plugin_azure_redis_server_load,
            [
                Result(
                    state=State.WARN, summary="Server load: 87.00% (warn/crit at 85.00%/90.00%)"
                ),
                Metric("azure_redis_server_load", 87.0, levels=(85.0, 90.0)),
            ],
            id="redis server load (no params, default warn threshold)",
        ),
    ],
)
def test_check_azure_redis_check_functions(
    section: Section,
    check_plugin: CheckPlugin,
    params: Mapping[str, Any],
    expected_result: Sequence[Result | Metric],
) -> None:
    check_function = check_plugin.check_function
    assert list(check_function(params, section)) == expected_result


@mock.patch(
    "cmk.plugins.lib.azure.get_value_store",
    return_value={"azure_redis_server_load_average": (EPOCH - 300, EPOCH, 99)},
)
@time_machine.travel(EPOCH + 300)
def test_check_azure_v2_redis_server_load_average(_get_value_store: Mock) -> None:
    check_function = azure_redis.check_plugin_azure_redis_server_load.check_function
    params = {
        "average_mins": 5,
    }
    assert list(check_function(params, AZURE_REDIS_WITH_METRICS)) == [
        Metric("azure_redis_server_load", 26.0),
        Result(state=State.OK, summary="Server load: 62.50%"),
        Metric("azure_redis_server_load_average", 62.5),
    ]


@mock.patch(
    "cmk.plugins.lib.azure.get_value_store",
    return_value={"azure_redis_server_load_sustained_threshold": EPOCH - 45.0},
)
@time_machine.travel(EPOCH)
def test_check_azure_v2_redis_server_load_sustained(_get_value_store: Mock) -> None:
    check_function = azure_redis.check_plugin_azure_redis_server_load.check_function
    params = {
        "for_time": {
            "threshold_for_time": 25,
            "limit_secs_for_time": ("fixed", (30.0, 60.0)),
        },
    }
    assert list(check_function(params, AZURE_REDIS_WITH_METRICS)) == [
        Result(
            state=State.WARN,
            summary="Server under high load for: 45 seconds (warn/crit at 30 seconds/1 minute 0 seconds)",
        ),
        Result(state=State.OK, summary="Server load: 26.00%"),
        Metric("azure_redis_server_load", 26.0),
    ]


@mock.patch(
    "cmk.plugins.lib.azure.get_value_store",
    return_value={"util_average": (EPOCH - 300, EPOCH, 99)},
)
@time_machine.travel(EPOCH + 300)
def test_check_azure_redis_cpu_util_average(_get_value_store: Mock) -> None:
    check_function = azure_redis.check_plugin_azure_redis_cpu_utilization.check_function
    params = {
        "average_mins": 5,
    }
    assert list(check_function(params, AZURE_REDIS_WITH_METRICS)) == [
        Metric("util", 25.0),
        Result(state=State.OK, summary="Total CPU: 62.00%"),
        Metric("util_average", 62.0),
    ]


@mock.patch(
    "cmk.plugins.lib.azure.get_value_store",
    return_value={"util_sustained_threshold": EPOCH - 45.0},
)
@time_machine.travel(EPOCH)
def test_check_azure_redis_cpu_util_sustained(_get_value_store: Mock) -> None:
    check_function = azure_redis.check_plugin_azure_redis_cpu_utilization.check_function
    params = {
        "for_time": {
            "threshold_for_time": 25,
            "limit_secs_for_time": ("fixed", (30.0, 60.0)),
        },
    }
    assert list(check_function(params, AZURE_REDIS_WITH_METRICS)) == [
        Result(
            state=State.WARN,
            summary="CPU utilization high for: 45 seconds (warn/crit at 30 seconds/1 minute 0 seconds)",
        ),
        Result(state=State.OK, summary="Total CPU: 25.00%"),
        Metric("util", 25.0),
    ]
