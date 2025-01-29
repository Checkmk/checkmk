#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import (
    CheckResult,
    DiscoveryResult,
    IgnoreResultsError,
    Metric,
    render,
    Result,
    Service,
    ServiceLabel,
    State,
)
from cmk.plugins.lib.azure import (
    _get_metrics,
    _get_metrics_number,
    _parse_resource,
    AzureMetric,
    check_connections,
    check_cpu,
    check_memory,
    check_network,
    check_storage,
    create_check_metrics_function_single,
    create_discover_by_metrics_function,
    create_discover_by_metrics_function_single,
    iter_resource_attributes,
    MetricData,
    parse_resources,
    Resource,
    Section,
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
    "resource_types,section,expected_discovery",
    [
        pytest.param(
            None,
            PARSED_RESOURCES,
            [
                Service(
                    item="checkmk-mysql-server",
                    labels=[
                        ServiceLabel("cmk/azure/tag/tag1", "value1"),
                        ServiceLabel("cmk/azure/tag/tag2", "value2"),
                    ],
                )
            ],
            id="single resource, no resource type",
        ),
        pytest.param(
            None,
            MULTIPLE_RESOURCE_SECTION,
            [
                Service(
                    item="checkmk-mysql-single-server",
                    labels=[
                        ServiceLabel("cmk/azure/tag/tag1", "value1"),
                        ServiceLabel("cmk/azure/tag/tag2", "value2"),
                    ],
                ),
                Service(
                    item="checkmk-mysql-flexible-server",
                    labels=[
                        ServiceLabel("cmk/azure/tag/tag3", "value3"),
                        ServiceLabel("cmk/azure/tag/tag4", "value4"),
                    ],
                ),
            ],
            id="multiple resources, no resource type",
        ),
        pytest.param(
            ["Microsoft.DBforMySQL/servers"],
            PARSED_RESOURCES,
            [
                Service(
                    item="checkmk-mysql-server",
                    labels=[
                        ServiceLabel("cmk/azure/tag/tag1", "value1"),
                        ServiceLabel("cmk/azure/tag/tag2", "value2"),
                    ],
                ),
            ],
            id="single resource, matching resource type",
        ),
        pytest.param(
            ["Microsoft.DBforMySQL/flexibleServers"],
            PARSED_RESOURCES,
            [],
            id="single resource, non-matching resource type",
        ),
        pytest.param(
            ["Microsoft.DBforMySQL/servers"],
            MULTIPLE_RESOURCE_SECTION,
            [
                Service(
                    item="checkmk-mysql-single-server",
                    labels=[
                        ServiceLabel("cmk/azure/tag/tag1", "value1"),
                        ServiceLabel("cmk/azure/tag/tag2", "value2"),
                    ],
                )
            ],
            id="multiple resources, one matching resource type",
        ),
        pytest.param(
            ["Microsoft.DBforMySQL/servers", "Microsoft.DBforMySQL/flexibleServers"],
            MULTIPLE_RESOURCE_SECTION,
            [
                Service(
                    item="checkmk-mysql-single-server",
                    labels=[
                        ServiceLabel("cmk/azure/tag/tag1", "value1"),
                        ServiceLabel("cmk/azure/tag/tag2", "value2"),
                    ],
                ),
                Service(
                    item="checkmk-mysql-flexible-server",
                    labels=[
                        ServiceLabel("cmk/azure/tag/tag3", "value3"),
                        ServiceLabel("cmk/azure/tag/tag4", "value4"),
                    ],
                ),
            ],
            id="multiple resources, multiple matching resource type",
        ),
    ],
)
def test_create_discover_by_metrics_function(
    resource_types: Sequence[str] | None, section: Section, expected_discovery: DiscoveryResult
) -> None:
    discovery_func = create_discover_by_metrics_function(
        "average_storage_percent",
        "average_active_connections",
        resource_types=resource_types,
    )
    assert list(discovery_func(section)) == expected_discovery


@pytest.mark.parametrize(
    "resource_types,section,expected_discovery",
    [
        pytest.param(
            None,
            PARSED_RESOURCES,
            [
                Service(
                    labels=[
                        ServiceLabel("cmk/azure/tag/tag1", "value1"),
                        ServiceLabel("cmk/azure/tag/tag2", "value2"),
                    ]
                )
            ],
            id="single resource, no resource type",
        ),
        pytest.param(
            ["Microsoft.DBforMySQL/servers"],
            PARSED_RESOURCES,
            [
                Service(
                    labels=[
                        ServiceLabel("cmk/azure/tag/tag1", "value1"),
                        ServiceLabel("cmk/azure/tag/tag2", "value2"),
                    ]
                )
            ],
            id="single resource, matching resource type",
        ),
        pytest.param(
            ["Microsoft.DBforMySQL/flexibleServers"],
            PARSED_RESOURCES,
            [],
            id="single resource, non-matching resource type",
        ),
        pytest.param(
            ["Microsoft.DBforMySQL/servers", "Microsoft.DBforMySQL/flexibleServers"],
            MULTIPLE_RESOURCE_SECTION,
            [],
            id="multiple resources, matching resource types",
        ),
    ],
)
def test_create_discover_by_metrics_function_single(
    resource_types: Sequence[str] | None, section: Section, expected_discovery: DiscoveryResult
) -> None:
    discovery_func = create_discover_by_metrics_function_single(
        "average_storage_percent",
        "average_active_connections",
        resource_types=resource_types,
    )
    assert list(discovery_func(section)) == expected_discovery


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
    expected_result: Sequence[Result | Metric],
) -> None:
    assert list(check_memory()(item, params, section)) == expected_result


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
                    group="westeurope",
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
        list(check_memory()(item, params, section))


@pytest.mark.parametrize(
    "section, item, params, expected_result",
    [
        (
            PARSED_RESOURCES,
            "checkmk-mysql-server",
            {"levels": (0.0, 0.0)},
            [
                Result(state=State.CRIT, summary="CPU utilization: 0% (warn/crit at 0%/0%)"),
                Metric("util", 0.0, levels=(0.0, 0.0)),
            ],
        ),
    ],
)
def test_check_cpu(
    section: Section,
    item: str,
    params: Mapping[str, Any],
    expected_result: Sequence[Result | Metric],
) -> None:
    assert list(check_cpu()(item, params, section)) == expected_result


@pytest.mark.parametrize(
    "section, item, params, expected_result",
    [
        (
            PARSED_RESOURCES,
            "checkmk-mysql-server",
            {"active_connections": (5, 10), "failed_connections": (1, 2)},
            [
                Result(state=State.WARN, summary="Active connections: 6 (warn/crit at 5/10)"),
                Metric("active_connections", 6.0, levels=(5.0, 10.0)),
                Result(state=State.CRIT, summary="Failed connections: 2 (warn/crit at 1/2)"),
                Metric("failed_connections", 2.0, levels=(1.0, 2.0)),
            ],
        ),
    ],
)
def test_check_connections(
    section: Section,
    item: str,
    params: Mapping[str, Any],
    expected_result: Sequence[Result | Metric],
) -> None:
    assert list(check_connections()(item, params, section)) == expected_result


@pytest.mark.parametrize(
    "section, item, params, expected_result",
    [
        (
            PARSED_RESOURCES,
            "checkmk-mysql-server",
            {"ingress_levels": (5000, 10000), "egress_levels": (1000, 2000)},
            [
                Result(state=State.OK, summary="Network in: 1000 B"),
                Metric("ingress", 1000.0, levels=(5000.0, 10000.0)),
                Result(
                    state=State.WARN, summary="Network out: 1.46 KiB (warn/crit at 1000 B/1.95 KiB)"
                ),
                Metric("egress", 1500.0, levels=(1000.0, 2000.0)),
            ],
        ),
    ],
)
def test_check_network(
    section: Section,
    item: str,
    params: Mapping[str, Any],
    expected_result: Sequence[Result | Metric],
) -> None:
    assert list(check_network()(item, params, section)) == expected_result


@pytest.mark.parametrize(
    "section, item, params, expected_result",
    [
        (
            PARSED_RESOURCES,
            "checkmk-mysql-server",
            {
                "io_consumption": (70.0, 90.0),
                "storage": (70.0, 90.0),
                "serverlog_storage": (70.0, 90.0),
            },
            [
                Result(state=State.WARN, summary="IO: 88.50% (warn/crit at 70.00%/90.00%)"),
                Metric("io_consumption_percent", 88.5, levels=(70.0, 90.0)),
                Result(state=State.OK, summary="Storage: 2.95%"),
                Metric("storage_percent", 2.95, levels=(70.0, 90.0)),
                Result(state=State.OK, summary="Server log storage: 0%"),
                Metric("serverlog_storage_percent", 0.0, levels=(70.0, 90.0)),
            ],
        ),
    ],
)
def test_check_storage(
    section: Section,
    item: str,
    params: Mapping[str, Any],
    expected_result: Sequence[Result | Metric],
) -> None:
    assert list(check_storage()(item, params, section)) == expected_result


@pytest.mark.parametrize(
    "section,expected_result",
    [
        pytest.param(
            PARSED_RESOURCES,
            [
                Result(state=State.OK, summary="Storage: 2.95%"),
                Metric("storage_percent", 2.95),
            ],
            id="one resource",
        ),
        pytest.param(MULTIPLE_RESOURCE_SECTION, [], id="multiple resources"),
    ],
)
def test_create_check_azure_metrics_function_single(
    section: Section, expected_result: CheckResult
) -> None:
    check_func = create_check_metrics_function_single(
        [
            MetricData(
                "average_storage_percent",
                "storage_percent",
                "Storage",
                render.percent,
                upper_levels_param="storage",
            ),
        ],
        suppress_error=True,
    )
    assert list(check_func({}, section)) == expected_result


def test_create_check_azure_metrics_function_single_error() -> None:
    check_func = create_check_metrics_function_single(
        [
            MetricData(
                "average_storage_percent",
                "storage_percent",
                "Storage",
                render.percent,
                upper_levels_param="storage",
            ),
        ]
    )
    with pytest.raises(IgnoreResultsError, match="Only one resource expected"):
        list(check_func({}, MULTIPLE_RESOURCE_SECTION))
