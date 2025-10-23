#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"


from collections.abc import Mapping, Sequence
from types import EllipsisType
from typing import Any
from unittest import mock
from unittest.mock import Mock

import pytest
import time_machine

from cmk.agent_based.v2 import (
    check_levels as check_levels_v2,
)
from cmk.agent_based.v2 import (
    CheckResult,
    DiscoveryResult,
    Metric,
    render,
    Result,
    Service,
    ServiceLabel,
    State,
    TableRow,
)
from cmk.plugins.azure_v2.agent_based.lib import (
    _get_metrics,
    _get_metrics_number,
    _parse_resource,
    _threshold_hit_for_time,
    AzureMetric,
    check_connections,
    check_cpu,
    check_memory,
    check_network,
    check_resource_metrics,
    check_storage,
    create_check_metrics_function_single,
    create_discover_by_metrics_function,
    create_discover_by_metrics_function_single,
    create_inventory_function,
    iter_resource_attributes,
    MetricData,
    parse_resources,
    Resource,
    Section,
    SustainedLevelDirection,
)

EPOCH = 1757328437.8742359


RESOURCES = [
    ["Resource"],
    [
        '{"id": "/subscriptions/1234/resourceGroups/BurningMan/providers/Microsoft.DBforMySQL/servers/checkmk-mysql-server", "name": "checkmk-mysql-server", "type": "Microsoft.DBforMySQL/servers", "sku": {"name": "B_Gen5_1", "tier": "Basic", "family": "Gen5", "capacity": 1}, "location": "westeurope", "tags": {"tag1": "value1", "tag2": "value2"}, "subscription": "2fac104f-cb9c-461d-be57-037039662426", "group": "BurningMan", "provider": "Microsoft.DBforMySQL"}'
    ],
    ["metrics following", "9"],
    [
        '{"name": "cpu_percent", "aggregation": "average", "value": 0.0, "unit": "percent", "timestamp": "2022-07-19T07:53:00Z", "filter": null, "interval_id": "PT1M", "interval": "0:01:00", "cmk_metric_alias": "average_cpu_percent"}'
    ],
    [
        '{"name": "memory_percent", "aggregation": "average", "value": 24.36, "unit": "percent", "timestamp": "2022-07-19T07:53:00Z", "filter": null, "interval_id": "PT1M", "interval": "0:01:00", "cmk_metric_alias": "average_memory_percent"}'
    ],
    [
        '{"name": "serverlog_storage_percent", "aggregation": "average", "value": 0.0, "unit": "percent", "timestamp": "2022-07-19T07:53:00Z", "filter": null, "interval_id": "PT1M", "interval": "0:01:00", "cmk_metric_alias": "average_serverlog_storage_percent"}'
    ],
    [
        '{"name": "storage_percent", "aggregation": "average", "value": 2.95, "unit": "percent", "timestamp": "2022-07-19T07:53:00Z", "filter": null, "interval_id": "PT1M", "interval": "0:01:00", "cmk_metric_alias": "average_storage_percent"}'
    ],
    [
        '{"name": "io_consumption_percent", "aggregation": "average", "value": 88.5, "unit": "percent", "timestamp": "2022-07-19T07:53:00Z", "filter": null, "interval_id": "PT1M", "interval": "0:01:00", "cmk_metric_alias": "average_io_consumption_percent"}'
    ],
    [
        '{"name": "active_connections", "aggregation": "average", "value": 6.0, "unit": "count", "timestamp": "2022-07-19T07:53:00Z", "filter": null, "interval_id": "PT1M", "interval": "0:01:00", "cmk_metric_alias": "average_active_connections"}'
    ],
    [
        '{"name": "connections_failed", "aggregation": "total", "value": 2.0, "unit": "count", "timestamp": "2022-07-19T07:53:00Z", "filter": null, "interval_id": "PT1M", "interval": "0:01:00", "cmk_metric_alias": "total_connections_failed"}'
    ],
    [
        '{"name": "network_bytes_ingress", "aggregation": "total", "value": 1000.0, "unit": "bytes", "timestamp": "2022-07-19T07:53:00Z", "filter": null, "interval_id": "PT1M", "interval": "0:01:00", "cmk_metric_alias": "total_network_bytes_ingress"}'
    ],
    [
        '{"name": "network_bytes_egress", "aggregation": "total", "value": 1500.0, "unit": "bytes", "timestamp": "2022-07-19T07:53:00Z", "filter": null, "interval_id": "PT1M", "interval": "0:01:00", "cmk_metric_alias": "total_network_bytes_egress"}'
    ],
]

PARSED_RESOURCE = Resource(
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
PARSED_RESOURCES = {"checkmk-mysql-server": PARSED_RESOURCE}


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
        [
            '{"name": "cpu_percent", "aggregation": "average", "value": 0.0, "unit": "percent", "cmk_metric_alias": "average_cpu_percent"}'
        ]
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
                    '{"name": "cpu_percent", "aggregation": "average", "value": 0.0, "unit": "percent", "cmk_metric_alias": "average_cpu_percent" }'
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
                    '{"name": "cpu_percent", "aggregation": "average", "value": 0.0, "unit": "percent", "cmk_metric_alias": "average_cpu_percent"}'
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
                    '{"name": "cpu_percent", "aggregation": "average", "value": 0.0, "unit": "percent", "cmk_metric_alias": "average_cpupercent"}'
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
    "current_value1, current_value2, threshold, limits, now1, now2, timestamp_in_vs, direction, label, expected1, expected2",
    [
        pytest.param(
            50,
            48,
            60,
            (60, 120),
            EPOCH,
            EPOCH + 30,
            ...,
            SustainedLevelDirection.UPPER_BOUND,
            None,
            [],
            [],
            id="threshold not crossed",
        ),
        pytest.param(
            50,
            48,
            30,
            (60, 120),
            EPOCH,
            EPOCH + 30,
            ...,
            SustainedLevelDirection.UPPER_BOUND,
            None,
            [],
            [
                Result(state=State.OK, notice="Above the threshold for: 30 seconds"),
            ],
            id="threshold crossed, but time not crossed",
        ),
        pytest.param(
            50,
            48,
            30,
            (60, 120),
            EPOCH,
            EPOCH + 61,
            ...,
            SustainedLevelDirection.UPPER_BOUND,
            None,
            [],
            [
                Result(
                    state=State.WARN,
                    notice="Above the threshold for: 1 minute 1 second (warn/crit at 1 minute 0 seconds/2 minutes 0 seconds)",
                ),
            ],
            id="threshold crossed first run, time crossed second run",
        ),
        pytest.param(
            50,
            48,
            30,
            (60, 120),
            EPOCH,
            EPOCH + 1,
            ...,
            SustainedLevelDirection.UPPER_BOUND,
            None,
            [],
            [
                Result(state=State.OK, notice="Above the threshold for: 1 second"),
            ],
            id="threshold crossed first and second run, but time not crossed",
        ),
        pytest.param(
            50,
            28,
            30,
            (60, 120),
            EPOCH,
            EPOCH + 30,
            EPOCH - 15,
            SustainedLevelDirection.UPPER_BOUND,
            None,
            [
                Result(state=State.OK, notice="Above the threshold for: 15 seconds"),
            ],
            [],
            id="threshold still crossed from previous run, then ok",
        ),
        pytest.param(
            27,
            28,
            30,
            (60, 120),
            EPOCH,
            EPOCH + 30,
            EPOCH - 15,
            SustainedLevelDirection.UPPER_BOUND,
            None,
            [],
            [],
            id="threshold no longer crossed from previous run",
        ),
        pytest.param(
            50,
            68,
            70,
            (60, 120),
            EPOCH,
            EPOCH + 80,
            EPOCH - 15,
            SustainedLevelDirection.LOWER_BOUND,
            "Value is too low since",
            [
                Result(state=State.OK, notice="Value is too low since: 15 seconds"),
            ],
            [
                Result(
                    state=State.WARN,
                    notice="Value is too low since: 1 minute 35 seconds (warn/crit at 1 minute 0 seconds/2 minutes 0 seconds)",
                ),
            ],
            id="threshold crossed first run, is lower bound",
        ),
    ],
)
def test_threshold_hit_for_time(
    current_value1: float,
    current_value2: float,
    threshold: float,
    limits: tuple[float, float],
    now1: float,
    now2: float,
    timestamp_in_vs: Mapping[str, float] | EllipsisType,
    direction: SustainedLevelDirection,
    label: str | None,
    expected1: Sequence[Metric | Result],
    expected2: Sequence[Metric | Result],
) -> None:
    value_store = {}
    if timestamp_in_vs is not ...:
        value_store["timestamp"] = timestamp_in_vs

    first_result = _threshold_hit_for_time(
        current_value1,
        threshold,
        ("fixed", limits),
        now1,
        value_store,
        "timestamp",
        direction=direction,
        label=label,
    )
    assert list(first_result) == expected1
    second_result = _threshold_hit_for_time(
        current_value2,
        threshold,
        ("fixed", limits),
        now2,
        value_store,
        "timestamp",
        direction=direction,
        label=label,
    )
    assert list(second_result) == expected2


@pytest.mark.parametrize(
    "section,expected_result",
    [
        pytest.param(
            PARSED_RESOURCE,
            [
                Result(state=State.OK, summary="Storage: 2.95%"),
                Metric("storage_percent", 2.95),
            ],
            id="one resource",
        ),
    ],
)
def test_create_check_azure_metrics_function_single(
    section: Resource, expected_result: CheckResult
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


@pytest.mark.parametrize(
    "section,expected_result",
    [
        pytest.param(
            PARSED_RESOURCE,
            [
                Result(state=State.OK, summary="Storage: 2.95%"),
                Metric("storage_percent", 2.95),
            ],
            id="one resource",
        ),
    ],
)
def test_create_check_azure_metrics_function_single_specified_check_levels(
    section: Resource, expected_result: CheckResult
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
        check_levels=check_levels_v2,
    )
    assert list(check_func({}, section)) == expected_result


def test_check_resource_metric_map_func() -> None:
    metric_data = MetricData(
        "total_connections_failed",
        "connections_failed",
        "Connections failed",
        str,
    )

    metric_data_with_map_fn = MetricData(
        "total_connections_failed",
        "connections_failed_2",
        "Connections failed 2",
        str,
        map_func=lambda x: x * 10,
    )

    check_result = check_resource_metrics(
        PARSED_RESOURCE,
        {},
        [metric_data, metric_data_with_map_fn],
    )

    assert list(check_result) == (
        [
            Result(state=State.OK, summary="Connections failed: 2.0"),
            Metric("connections_failed", 2.0),
            Result(state=State.OK, summary="Connections failed 2: 20.0"),
            Metric("connections_failed_2", 20.0),
        ]
    )


def test_check_resource_metric_notice_only() -> None:
    metric_data = MetricData(
        "total_connections_failed",
        "connections_failed",
        "Connections failed",
        str,
    )

    metric_data_with_notice_only = MetricData(
        "total_connections_failed",
        "connections_failed_2",
        "Connections failed 2",
        str,
        notice_only=True,
    )

    check_result = check_resource_metrics(
        PARSED_RESOURCE,
        {},
        [metric_data, metric_data_with_notice_only],
    )

    assert list(check_result) == (
        [
            Result(state=State.OK, summary="Connections failed: 2.0"),
            Metric("connections_failed", 2.0),
            Result(state=State.OK, notice="Connections failed 2: 2.0"),
            Metric("connections_failed_2", 2.0),
        ]
    )


@mock.patch("cmk.plugins.azure_v2.agent_based.lib.get_value_store", return_value={})
@time_machine.travel(EPOCH)
def test_check_resource_metric_average(get_value_store: Mock) -> None:
    metric_data = MetricData(
        "total_connections_failed",
        "connections_failed",
        "Connections failed",
        str,
        average_param="average",
    )

    check_result = check_resource_metrics(
        PARSED_RESOURCE,
        {
            "average": ("seconds", 60 * 5),
        },
        [metric_data],
    )

    assert list(check_result) == (
        [
            Metric("connections_failed", 2.0),
            Result(state=State.OK, summary="Connections failed: 2.0"),
            Metric("connections_failed_average", 2.0),
        ]
    )

    get_value_store.assert_called_once()


@mock.patch(
    "cmk.plugins.azure_v2.agent_based.lib.get_value_store",
    return_value={"connections_failed_sustained_threshold": EPOCH - 1000},
)
@time_machine.travel(EPOCH)
def test_check_resource_sustained_threshold(get_value_store: Mock) -> None:
    metric_data = MetricData(
        "total_connections_failed",
        "connections_failed",
        "Connections failed",
        str,
        sustained_threshold_param="threshold",
        sustained_levels_time_param="threshold_levels",
        sustained_level_direction=SustainedLevelDirection.UPPER_BOUND,
    )

    check_result = check_resource_metrics(
        PARSED_RESOURCE,
        {
            "threshold": 1.5,
            "threshold_levels": ("fixed", (30.0, 60.0)),
        },
        [metric_data],
    )

    assert list(check_result) == (
        [
            Result(
                state=State.CRIT,
                summary=(
                    "Above the threshold for: 16 minutes 40 seconds "
                    "(warn/crit at 30 seconds/1 minute 0 seconds)"
                ),
            ),
            Result(state=State.OK, summary="Connections failed: 2.0"),
            Metric("connections_failed", 2.0),
        ]
    )

    get_value_store.assert_called_once()


@mock.patch(
    "cmk.plugins.azure_v2.agent_based.lib.get_value_store",
    return_value={"connections_failed_sustained_threshold": EPOCH - 1000},
)
@time_machine.travel(EPOCH)
def test_check_resource_sustained_threshold_map_func(get_value_store: Mock) -> None:
    metric_data = MetricData(
        "total_connections_failed",
        "connections_failed",
        "Connections failed",
        str,
        sustained_threshold_param="threshold",
        sustained_levels_time_param="threshold_levels",
        sustained_level_direction=SustainedLevelDirection.UPPER_BOUND,
        map_func=lambda value: value * 100,
    )

    check_result = check_resource_metrics(
        PARSED_RESOURCE,
        {
            "threshold": 199,
            "threshold_levels": ("fixed", (30.0, 60.0)),
        },
        [metric_data],
    )

    assert list(check_result) == (
        [
            Result(
                state=State.CRIT,
                summary="Above the threshold for: 16 minutes 40 seconds (warn/crit at 30 seconds/1 minute 0 seconds)",
            ),
            Result(state=State.OK, summary="Connections failed: 200.0"),
            Metric("connections_failed", 200.0),
        ]
    )

    get_value_store.assert_called_once()


@pytest.mark.parametrize(
    "resource_types,section,expected_discovery",
    [
        pytest.param(
            None,
            PARSED_RESOURCE,
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
            PARSED_RESOURCE,
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
            PARSED_RESOURCE,
            [],
            id="single resource, non-matching resource type",
        ),
    ],
)
def test_create_discover_by_metrics_function_single(
    resource_types: Sequence[str] | None, section: Resource, expected_discovery: DiscoveryResult
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
            PARSED_RESOURCE,
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
            PARSED_RESOURCE,
            [("Location", "westeurope"), ("Tag1", "value1"), ("Tag2", "value2")],
        ),
    ],
)
def test_iter_resource_attributes_default_keys(
    resource: Resource, expected_result: list[tuple[str, str | None]]
) -> None:
    assert list(iter_resource_attributes(resource)) == expected_result


def test_inventory_common_azure() -> None:
    inventory = list(create_inventory_function()(PARSED_RESOURCE))

    expected_metadata: dict[int | float | str, str] = {
        "Object": "Microsoft.DBforMySQL/servers",
        "Resource group": "BurningMan",
        "Entity": "Resource",
        "Cloud provider": "Azure",
        "Region": "westeurope",
        "Name": "checkmk-mysql-server",
        # TODO: These require updating the fixture data
        # "Subscription name": ,
        # "Subscription ID",
    }

    tags = {}
    matched_rows = 0
    for inv in inventory:
        assert isinstance(inv, TableRow)  # sate mypy
        if "metadata" in inv.path:
            key = inv.key_columns["information"]
            value = inv.inventory_columns["value"]

            # We might output more than we look for.
            # Particularly with outdated fixture data.
            if key in expected_metadata:
                matched_rows += 1
                assert expected_metadata[key] == value
        elif "tags" in inv.path:
            tags[inv.key_columns["name"]] = inv.inventory_columns["value"]

    # Since the test is not 1:1 with the expected rows, do an extra check after,
    # to ensure we actually ran the assertion above
    assert matched_rows == len(expected_metadata)

    assert tags["tag1"] == "value1"
    assert tags["tag2"] == "value2"
    assert len(tags) == 2


@pytest.mark.parametrize(
    "section, item, params, expected_result",
    [
        (
            PARSED_RESOURCE,
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
    section: Resource,
    item: str,
    params: Mapping[str, Any],
    expected_result: Sequence[Result | Metric],
) -> None:
    assert list(check_memory()("Memory", params, {"Memory": section})) == expected_result


@pytest.mark.parametrize(
    "section, item, params, expected_result",
    [
        (
            PARSED_RESOURCE,
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
    section: Resource,
    item: str,
    params: Mapping[str, Any],
    expected_result: Sequence[Result | Metric],
) -> None:
    assert list(check_cpu()(params, section)) == expected_result


@pytest.mark.parametrize(
    "section, item, params, expected_result",
    [
        (
            PARSED_RESOURCE,
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
    section: Resource,
    item: str,
    params: Mapping[str, Any],
    expected_result: Sequence[Result | Metric],
) -> None:
    assert list(check_connections()(params, section)) == expected_result


@pytest.mark.parametrize(
    "section, item, params, expected_result",
    [
        (
            PARSED_RESOURCE,
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
    section: Resource,
    item: str,
    params: Mapping[str, Any],
    expected_result: Sequence[Result | Metric],
) -> None:
    assert list(check_network()(params, section)) == expected_result


@pytest.mark.parametrize(
    "section, item, params, expected_result",
    [
        (
            PARSED_RESOURCE,
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
    section: Resource,
    item: str,
    params: Mapping[str, Any],
    expected_result: Sequence[Result | Metric],
) -> None:
    assert list(check_storage()(params, section)) == expected_result
