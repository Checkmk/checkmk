#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import CheckPlugin, Metric, Result, State
from cmk.plugins.azure.agent_based import azure_redis
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
                name="allevictedkeys", aggregation="total", value=42, unit="count"
            ),
            "total_allexpiredkeys": AzureMetric(
                name="allexpiredkeys", aggregation="total", value=140, unit="count"
            ),
        },
        subscription="ba9f74ff-6a4c-41e0-ab55-15c7fe79632f",
    ),
}


@pytest.mark.parametrize(
    "section, item, expected_result",
    [
        pytest.param(
            AZURE_REDIS_WITH_METRICS,
            "az-redis-test",
            [
                Result(
                    state=State.OK,
                    summary="Location: germanywestcentral",
                ),
            ],
            id="generic service",
        ),
    ],
)
def test_check_azure_redis(
    section: Section,
    item: str,
    expected_result: Sequence[Result | Metric],
) -> None:
    check_function = azure_redis.check_plugin_azure_redis.check_function
    assert list(check_function(item, section)) == expected_result


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
