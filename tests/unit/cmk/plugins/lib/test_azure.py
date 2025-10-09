#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

from collections.abc import Sequence

import pytest

from cmk.plugins.lib.azure import (
    _get_metrics,
    _get_metrics_number,
    _parse_resource,
    AzureMetric,
    iter_resource_attributes,
    parse_resources,
    Resource,
)

RESOURCES = [
    ["Resource"],
    [
        '{"id": "/subscriptions/1234/resourceGroups/BurningMan/providers/Microsoft.DBforMySQL/servers/checkmk-mysql-server", "name": "checkmk-mysql-server", "type": "Microsoft.DBforMySQL/servers", "sku": {"name": "B_Gen5_1", "tier": "Basic", "family": "Gen5", "capacity": 1}, "location": "westeurope", "tags": {"tag1": "value1", "tag2": "value2"}, "subscription": "2fac104f-cb9c-461d-be57-037039662426", "group": "BurningMan", "provider": "Microsoft.DBforMySQL"}'
    ],
    ["metrics following", "9"],
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
        '{"name": "io_consumption_percent", "aggregation": "average", "value": 88.5, "unit": "percent", "timestamp": "2022-07-19T07:53:00Z", "filter": null, "interval_id": "PT1M", "interval": "0:01:00"}'
    ],
    [
        '{"name": "active_connections", "aggregation": "average", "value": 6.0, "unit": "count", "timestamp": "2022-07-19T07:53:00Z", "filter": null, "interval_id": "PT1M", "interval": "0:01:00"}'
    ],
    [
        '{"name": "connections_failed", "aggregation": "total", "value": 2.0, "unit": "count", "timestamp": "2022-07-19T07:53:00Z", "filter": null, "interval_id": "PT1M", "interval": "0:01:00"}'
    ],
    [
        '{"name": "network_bytes_ingress", "aggregation": "total", "value": 1000.0, "unit": "bytes", "timestamp": "2022-07-19T07:53:00Z", "filter": null, "interval_id": "PT1M", "interval": "0:01:00"}'
    ],
    [
        '{"name": "network_bytes_egress", "aggregation": "total", "value": 1500.0, "unit": "bytes", "timestamp": "2022-07-19T07:53:00Z", "filter": null, "interval_id": "PT1M", "interval": "0:01:00"}'
    ],
]
PARSED_RESOURCES = {
    "checkmk-mysql-server": Resource(
        id="/subscriptions/1234/resourceGroups/BurningMan/providers/Microsoft.DBforMySQL/servers/checkmk-mysql-server",
        name="checkmk-mysql-server",
        type="Microsoft.DBforMySQL/servers",
        group="BurningMan",
        kind=None,
        location="westeurope",
        tags={"tag1": "value1", "tag2": "value2"},
        properties={},
        specific_info={},
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
            "average_io_consumption_percent": AzureMetric(
                name="io_consumption_percent", aggregation="average", value=88.5, unit="percent"
            ),
            "average_active_connections": AzureMetric(
                name="active_connections", aggregation="average", value=6.0, unit="count"
            ),
            "total_connections_failed": AzureMetric(
                name="connections_failed", aggregation="total", value=2.0, unit="count"
            ),
            "total_network_bytes_ingress": AzureMetric(
                name="network_bytes_ingress", aggregation="total", value=1000.0, unit="bytes"
            ),
            "total_network_bytes_egress": AzureMetric(
                name="network_bytes_egress", aggregation="total", value=1500.0, unit="bytes"
            ),
        },
        subscription="2fac104f-cb9c-461d-be57-037039662426",
    )
}

MULTIPLE_RESOURCE_SECTION = {
    "checkmk-mysql-single-server": Resource(
        id="/subscriptions/1234/resourceGroups/BurningMan/providers/Microsoft.DBforMySQL/servers/checkmk-mysql-single-server",
        name="checkmk-mysql-single-server",
        type="Microsoft.DBforMySQL/servers",
        group="BurningMan",
        kind=None,
        location="westeurope",
        tags={"tag1": "value1", "tag2": "value2"},
        properties={},
        specific_info={},
        metrics={
            "average_storage_percent": AzureMetric(
                name="storage_percent", aggregation="average", value=2.95, unit="percent"
            ),
        },
        subscription="2fac104f-cb9c-461d-be57-037039662426",
    ),
    "checkmk-mysql-flexible-server": Resource(
        id="/subscriptions/1234/resourceGroups/BurningMan/providers/Microsoft.DBforMySQL/servers/checkmk-mysql-flexible-server",
        name="checkmk-mysql-flexible-server",
        type="Microsoft.DBforMySQL/flexibleServers",
        group="BurningMan",
        kind=None,
        location="westeurope",
        tags={"tag3": "value3", "tag4": "value4"},
        properties={},
        specific_info={},
        metrics={
            "average_storage_percent": AzureMetric(
                name="storage_percent", aggregation="average", value=2.95, unit="percent"
            ),
        },
        subscription="2fac104f-cb9c-461d-be57-037039662426",
    ),
}

EPOCH = 1757328437.8742359


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
                    '{"id": "/subscriptions/1234/resourceGroups/BurningMan/providers/Microsoft.DBforMySQL/servers/checkmk-mysql-server", "name": "checkmk-mysql-server", "type": "Microsoft.DBforMySQL/servers", "group": "BurningMan"}'
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
                group="BurningMan",
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
                    '{"id": "/subscriptions/1234/resourceGroups/BurningMan/providers/Microsoft.DBforMySQL/servers/checkmk-mysql-server", "name": "checkmk-mysql-server", "type": "Microsoft.DBforMySQL/servers", "group": "BurningMan"}'
                ],
                ["metrics following", "5"],
            ],
            Resource(
                id="/subscriptions/1234/resourceGroups/BurningMan/providers/Microsoft.DBforMySQL/servers/checkmk-mysql-server",
                name="checkmk-mysql-server",
                type="Microsoft.DBforMySQL/servers",
                group="BurningMan",
            ),
            id="resource_with_too_few_rows",
        ),
        pytest.param(
            [
                [
                    '{"id": "/subscriptions/1234/resourceGroups/BurningMan/providers/Microsoft.DBforMySQL/servers/checkmk-mysql-server", "name": "checkmk-mysql-server", "type": "Microsoft.DBforMySQL/servers", "group": "BurningMan"}'
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
                group="BurningMan",
            ),
            id="resource_without_metrics",
        ),
        pytest.param(
            [
                [
                    '{"id": "/subscriptions/1234/resourceGroups/BurningMan/providers/Microsoft.DBforMySQL/servers/checkmk-mysql-server", "name": "checkmk-mysql-server", "type": "Microsoft.DBforMySQL/servers", "group": "BurningMan", "invalid_field"}'
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


@pytest.mark.parametrize(
    "resource,include_keys,expected_result",
    [
        (
            PARSED_RESOURCES["checkmk-mysql-server"],
            ("kind", "group", "type"),
            [
                ("Group", "BurningMan"),
                ("Type", "Microsoft.DBforMySQL/servers"),
                ("Tag1", "value1"),
                ("Tag2", "value2"),
            ],
        ),
    ],
)
def test_iter_resource_attributes(
    resource: Resource, include_keys: tuple[str], expected_result: list[tuple[str, str | None]]
) -> None:
    assert list(iter_resource_attributes(resource, include_keys=include_keys)) == expected_result


@pytest.mark.parametrize(
    "resource,expected_result",
    [
        (
            PARSED_RESOURCES["checkmk-mysql-server"],
            [("Location", "westeurope"), ("Tag1", "value1"), ("Tag2", "value2")],
        ),
    ],
)
def test_iter_resource_attributes_default_keys(
    resource: Resource, expected_result: list[tuple[str, str | None]]
) -> None:
    assert list(iter_resource_attributes(resource)) == expected_result
