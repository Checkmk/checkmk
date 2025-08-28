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
