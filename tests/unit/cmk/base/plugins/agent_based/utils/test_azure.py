#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping, Sequence, Union

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    IgnoreResultsError,
    Metric,
    Result,
    Service,
    State,
)
from cmk.base.plugins.agent_based.utils.azure import (
    _get_metrics,
    _get_metrics_number,
    _parse_resource,
    AzureMetric,
    check_memory,
    discover_azure_by_metrics,
    parse_resources,
    Resource,
    Section,
)

RESOURCES = [
    ["Resource"],
    [
        '{"id": "/subscriptions/1234/resourceGroups/BurningMan/providers/Microsoft.DBforMySQL/servers/checkmk-mysql-server", "name": "checkmk-mysql-server", "type": "Microsoft.DBforMySQL/servers", "sku": {"name": "B_Gen5_1", "tier": "Basic", "family": "Gen5", "capacity": 1}, "location": "westeurope", "tags": {}, "subscription": "2fac104f-cb9c-461d-be57-037039662426", "group": "BurningMan", "provider": "Microsoft.DBforMySQL"}'
    ],
    ["metrics following", "5"],
    [
        '{"name": "cpu_percent", "aggregation": "average", "value": 0.0, "unit": "percent", "timestamp": "2022-07-19T07:53:00Z", "filter": null, "interval_id": "PT1M", "interval": "0:01:00"}'
    ],
    [
        '{"name": "memory_percent", "aggregation": "average", "value": 24.36, "unit": "percent", "timestamp": "2022-07-19T07:53:00Z", "filter": null, "interval_id": "PT1M", "interval": "0:01:00"}'
    ],
    [
        '{"name": "serverlog_storage_percent", "aggregation": "average", "value": 0.0, "unit": "percent", "timestamp": "2022-07-19T07:53:00Z", "filter": null, "interval_id": "PT1M", "interval": "0:01:00"}'
    ],
    [
        '{"name": "storage_percent", "aggregation": "average", "value": 2.95, "unit": "percent", "timestamp": "2022-07-19T07:53:00Z", "filter": null, "interval_id": "PT1M", "interval": "0:01:00"}'
    ],
    [
        '{"name": "active_connections", "aggregation": "total", "value": 6.0, "unit": "count", "timestamp": "2022-07-19T07:53:00Z", "filter": null, "interval_id": "PT1M", "interval": "0:01:00"}'
    ],
]
PARSED_RESOURCES = {
    "checkmk-mysql-server": Resource(
        id="/subscriptions/1234/resourceGroups/BurningMan/providers/Microsoft.DBforMySQL/servers/checkmk-mysql-server",
        name="checkmk-mysql-server",
        type="Microsoft.DBforMySQL/servers",
        metrics={
            "average_cpu_percent": AzureMetric(
                name="cpu_percent", aggregation="average", value=0.0, unit="percent"
            ),
            "average_memory_percent": AzureMetric(
                name="memory_percent", aggregation="average", value=24.36, unit="percent"
            ),
            "average_serverlog_storage_percent": AzureMetric(
                name="serverlog_storage_percent", aggregation="average", value=0.0, unit="percent"
            ),
            "average_storage_percent": AzureMetric(
                name="storage_percent", aggregation="average", value=2.95, unit="percent"
            ),
            "total_active_connections": AzureMetric(
                name="active_connections", aggregation="total", value=6.0, unit="count"
            ),
        },
    )
}


@pytest.mark.parametrize(
    "row, expected_result",
    [
        (["metrics following", "5"], 5),
        (["invalid row"], 0),
        (["metrics following", "five"], 0),
    ],
)
def test__get_metrics_number(row: Sequence[str], expected_result: int) -> None:
    assert _get_metrics_number(row) == expected_result


def test__get_metrics() -> None:
    metrics_data = [
        ['{"name": "cpu_percent", "aggregation": "average", "value": 0.0, "unit": "percent"}']
    ]
    assert list(_get_metrics(metrics_data)) == [
        (
            "average_cpu_percent",
            AzureMetric(name="cpu_percent", aggregation="average", value=0.0, unit="percent"),
        )
    ]


@pytest.mark.parametrize(
    "resource_data, expected_result",
    [
        pytest.param(
            [
                [
                    '{"id": "/subscriptions/1234/resourceGroups/BurningMan/providers/Microsoft.DBforMySQL/servers/checkmk-mysql-server", "name": "checkmk-mysql-server", "type": "Microsoft.DBforMySQL/servers"}'
                ],
                ["metrics following", "5"],
                [
                    '{"name": "cpu_percent", "aggregation": "average", "value": 0.0, "unit": "percent"}'
                ],
            ],
            Resource(
                id="/subscriptions/1234/resourceGroups/BurningMan/providers/Microsoft.DBforMySQL/servers/checkmk-mysql-server",
                name="checkmk-mysql-server",
                type="Microsoft.DBforMySQL/servers",
                metrics={
                    "average_cpu_percent": AzureMetric(
                        name="cpu_percent", aggregation="average", value=0.0, unit="percent"
                    )
                },
            ),
            id="resource_with_metric",
        ),
        pytest.param(
            [
                [
                    '{"id": "/subscriptions/1234/resourceGroups/BurningMan/providers/Microsoft.DBforMySQL/servers/checkmk-mysql-server", "name": "checkmk-mysql-server", "type": "Microsoft.DBforMySQL/servers"}'
                ],
                ["metrics following", "5"],
            ],
            Resource(
                id="/subscriptions/1234/resourceGroups/BurningMan/providers/Microsoft.DBforMySQL/servers/checkmk-mysql-server",
                name="checkmk-mysql-server",
                type="Microsoft.DBforMySQL/servers",
            ),
            id="resource_with_too_few_rows",
        ),
        pytest.param(
            [
                [
                    '{"id": "/subscriptions/1234/resourceGroups/BurningMan/providers/Microsoft.DBforMySQL/servers/checkmk-mysql-server", "name": "checkmk-mysql-server", "type": "Microsoft.DBforMySQL/servers"}'
                ],
                ["metrics following", "0"],
                [
                    '{"name": "cpu_percent", "aggregation": "average", "value": 0.0, "unit": "percent"}'
                ],
            ],
            Resource(
                id="/subscriptions/1234/resourceGroups/BurningMan/providers/Microsoft.DBforMySQL/servers/checkmk-mysql-server",
                name="checkmk-mysql-server",
                type="Microsoft.DBforMySQL/servers",
            ),
            id="resource_without_metrics",
        ),
        pytest.param(
            [
                [
                    '{"id": "/subscriptions/1234/resourceGroups/BurningMan/providers/Microsoft.DBforMySQL/servers/checkmk-mysql-server", "name": "checkmk-mysql-server", "type": "Microsoft.DBforMySQL/servers", "invalid_field"}'
                ],
                ["metrics following", "0"],
                [
                    '{"name": "cpu_percent", "aggregation": "average", "value": 0.0, "unit": "percent"}'
                ],
            ],
            None,
            id="invalid_resource_json",
        ),
    ],
)
def test__parse_resource(resource_data: Sequence[str], expected_result: Resource | None) -> None:
    assert _parse_resource(resource_data) == expected_result


def test_parse_resources() -> None:
    assert parse_resources(RESOURCES) == PARSED_RESOURCES


def test_discover_azure_by_metrics() -> None:
    discovery_func = discover_azure_by_metrics(
        "average_storage_percent", "total_active_connections"
    )
    assert list(discovery_func(PARSED_RESOURCES)) == [Service(item="checkmk-mysql-server")]


@pytest.mark.parametrize(
    "section, item, params, expected_result",
    [
        (
            PARSED_RESOURCES,
            "checkmk-mysql-server",
            {"levels": (10.0, 30.0)},
            [
                Result(
                    state=State.WARN,
                    summary="Memory utilization: 24.36% (warn/crit at 10.00%/30.00%)",
                ),
                Metric("mem_used_percent", 24.36, levels=(10.0, 30.0)),
            ],
        ),
    ],
)
def test_check_memory(
    section: Section,
    item: str,
    params: Mapping[str, Any],
    expected_result: Sequence[Union[Result, Metric]],
) -> None:
    assert list(check_memory(item, params, section)) == expected_result


@pytest.mark.parametrize(
    "section, item, params",
    [
        pytest.param(PARSED_RESOURCES, "non-existing-mysql-server", {}, id="item_missing"),
        pytest.param(
            {
                "checkmk-mysql-server": Resource(
                    id="/subscriptions/1234/resourceGroups/BurningMan/providers/Microsoft.DBforMySQL/servers/checkmk-mysql-server",
                    name="checkmk-mysql-server",
                    type="Microsoft.DBforMySQL/servers",
                    metrics={
                        "average_cpu_percent": AzureMetric(
                            name="cpu_percent", aggregation="average", value=0.0, unit="percent"
                        )
                    },
                )
            },
            "checkmk-mysql-server",
            {},
            id="metric_missing",
        ),
    ],
)
def test_check_memory_errors(section: Section, item: str, params: Mapping[str, Any]) -> None:
    with pytest.raises(IgnoreResultsError, match="Data not present at the moment"):
        list(check_memory(item, params, section))
