#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, Sequence
from typing import Any

# mypy: disable-error-code="misc"
import pytest

from cmk.agent_based.v2 import Metric, Result, State
from cmk.plugins.azure_v2.agent_based.azure_databases import (
    check_plugin_azure_databases_connections,
    create_check_azure_databases_connections,
    create_check_azure_databases_cpu,
    create_check_azure_databases_deadlock,
    create_check_azure_databases_dtu,
    create_check_azure_databases_storage,
)
from cmk.plugins.azure_v2.agent_based.lib import AzureMetric, Resource

LEVELS = (5.0, 20.0)
METRIC_CONN_FAILED_OK = Metric(name="connections_failed_rate", value=10)
METRIC_CONN_FAILED_WARN = Metric(name="connections_failed_rate", value=10, levels=LEVELS)
METRIC_CONN_SUCCESS_OK = Metric(name="connections", value=10)
METRIC_CONN_SUCCESS_WARN = Metric(name="connections", value=10, levels=LEVELS)
METRIC_CPU_OK = Metric(name="util", value=10.0)
METRIC_CPU_WARN = Metric(name="util", value=10.0, levels=LEVELS)
METRIC_DEADLOCK_OK = Metric(name="deadlocks", value=10.0)
METRIC_DEADLOCK_WARN = Metric(name="deadlocks", value=10.0, levels=LEVELS)
METRIC_DTU_OK = Metric(name="dtu_percent", value=10.0)
METRIC_DTU_WARN = Metric(name="dtu_percent", value=10.0, levels=LEVELS)
METRIC_STORAGE_OK = Metric(name="storage_percent", value=10.0)
METRIC_STORAGE_WARN = Metric(name="storage_percent", value=10.0, levels=LEVELS)

RESULT_CONN_SUCCESS_OK = Result(state=State.OK, summary="Successful connections: 10")
RESULT_CONN_SUCCESS_WARN = Result(
    state=State.WARN, summary="Successful connections: 10 (warn/crit at 5.0/20.0)"
)
RESULT_CONN_FAILED_OK = Result(state=State.OK, summary="Failed connections: 10")
RESULT_CONN_FAILED_WARN = Result(
    state=State.WARN, summary="Failed connections: 10 (warn/crit at 5.0/20.0)"
)
RESULT_CPU_OK = Result(state=State.OK, summary="CPU: 10.00%")
RESULT_CPU_WARN = Result(state=State.WARN, summary="CPU: 10.00% (warn/crit at 5.00%/20.00%)")
RESULT_DEADLOCK_OK = Result(state=State.OK, summary="Deadlocks: 10")
RESULT_DEADLOCK_WARN = Result(state=State.WARN, summary="Deadlocks: 10 (warn/crit at 5.0/20.0)")
RESULT_DTU_OK = Result(state=State.OK, summary="Database throughput units: 10.00%")
RESULT_DTU_WARN = Result(
    state=State.WARN, summary="Database throughput units: 10.00% (warn/crit at 5.00%/20.00%)"
)
RESULT_STORAGE_OK = Result(state=State.OK, summary="Storage: 10.00%")
RESULT_STORAGE_WARN = Result(
    state=State.WARN, summary="Storage: 10.00% (warn/crit at 5.00%/20.00%)"
)


@pytest.mark.parametrize(
    "section, params, expected_result",
    [
        pytest.param(
            Resource(
                id="/subscriptions/1234/resourceGroups/group/foo/bar/foo",
                name="foo",
                type="foo/bar",
                group="group",
                location="westeurope",
                metrics={
                    "average_storage_percent": AzureMetric(
                        name="storage_percent",
                        aggregation="average",
                        value=10,
                        unit="percent",
                    )
                },
            ),
            {},
            [RESULT_STORAGE_OK, METRIC_STORAGE_OK],
            id="Storage without levels",
        ),
        pytest.param(
            Resource(
                id="/subscriptions/1234/resourceGroups/group/foo/bar/foo",
                name="foo",
                type="foo/bar",
                group="group",
                location="westeurope",
                metrics={
                    "average_storage_percent": AzureMetric(
                        name="storage_percent",
                        aggregation="average",
                        value=10,
                        unit="percent",
                    )
                },
            ),
            {"storage_percent": ("fixed", LEVELS)},
            [RESULT_STORAGE_WARN, METRIC_STORAGE_WARN],
            id="Storage with WARN level exceeded",
        ),
    ],
)
def test_check_azure_databases_storage(
    section: Resource,
    params: Mapping[str, Any],
    expected_result: Sequence[Result | Metric],
) -> None:
    assert list(create_check_azure_databases_storage()(params, section)) == expected_result


@pytest.mark.parametrize(
    "section, params, expected_result",
    [
        pytest.param(
            Resource(
                id="/subscriptions/1234/resourceGroups/group/foo/bar/foo",
                name="foo",
                type="foo/bar",
                group="group",
                location="westeurope",
                metrics={
                    "average_deadlock": AzureMetric(
                        name="deadlock",
                        aggregation="average",
                        value=10,
                        unit="count",
                    )
                },
            ),
            {},
            [RESULT_DEADLOCK_OK, METRIC_DEADLOCK_OK],
            id="Deadlock without levels",
        ),
        pytest.param(
            Resource(
                id="/subscriptions/1234/resourceGroups/group/foo/bar/foo",
                name="foo",
                type="foo/bar",
                group="group",
                location="westeurope",
                metrics={
                    "average_deadlock": AzureMetric(
                        name="deadlock",
                        aggregation="average",
                        value=10,
                        unit="count",
                    )
                },
            ),
            {"deadlocks": ("fixed", LEVELS)},
            [RESULT_DEADLOCK_WARN, METRIC_DEADLOCK_WARN],
            id="Deadlock without WARN levels exceeded",
        ),
    ],
)
def test_check_azure_databases_deadlock(
    section: Resource,
    params: Mapping[str, Any],
    expected_result: Sequence[Result | Metric],
) -> None:
    assert list(create_check_azure_databases_deadlock()(params, section)) == expected_result


@pytest.mark.parametrize(
    "section, params, expected_result",
    [
        pytest.param(
            Resource(
                id="/subscriptions/1234/resourceGroups/group/foo/bar/foo",
                name="foo",
                type="foo/bar",
                group="group",
                location="westeurope",
                metrics={
                    "average_cpu_percent": AzureMetric(
                        name="cpu_percent",
                        aggregation="average",
                        value=10,
                        unit="percent",
                    )
                },
            ),
            {},
            [RESULT_CPU_OK, METRIC_CPU_OK],
            id="CPU without levels",
        ),
        pytest.param(
            Resource(
                id="/subscriptions/1234/resourceGroups/group/foo/bar/foo",
                name="foo",
                type="foo/bar",
                group="group",
                location="westeurope",
                metrics={
                    "average_cpu_percent": AzureMetric(
                        name="cpu_percent",
                        aggregation="average",
                        value=10,
                        unit="percent",
                    )
                },
            ),
            {"cpu_percent": ("fixed", LEVELS)},
            [RESULT_CPU_WARN, METRIC_CPU_WARN],
            id="CPU with WARN level exceeded",
        ),
    ],
)
def test_check_azure_databases_cpu(
    section: Resource,
    params: Mapping[str, Any],
    expected_result: Sequence[Result | Metric],
) -> None:
    assert list(create_check_azure_databases_cpu()(params, section)) == expected_result


@pytest.mark.parametrize(
    "section, params, expected_result",
    [
        pytest.param(
            Resource(
                id="/subscriptions/1234/resourceGroups/group/foo/bar/foo",
                name="foo",
                type="foo/bar",
                group="group",
                location="westeurope",
                metrics={
                    "average_dtu_consumption_percent": AzureMetric(
                        name="dtu_percent",
                        aggregation="average",
                        value=10,
                        unit="percent",
                    )
                },
            ),
            {},
            [RESULT_DTU_OK, METRIC_DTU_OK],
            id="DTU without levels",
        ),
        pytest.param(
            Resource(
                id="/subscriptions/1234/resourceGroups/group/foo/bar/foo",
                name="foo",
                type="foo/bar",
                group="group",
                location="westeurope",
                metrics={
                    "average_dtu_consumption_percent": AzureMetric(
                        name="dtu_percent",
                        aggregation="average",
                        value=10,
                        unit="percent",
                    )
                },
            ),
            {"dtu_percent": ("fixed", LEVELS)},
            [RESULT_DTU_WARN, METRIC_DTU_WARN],
            id="DTU with WARN level exceeded",
        ),
    ],
)
def test_check_azure_databases_dtu(
    section: Resource,
    params: Mapping[str, Any],
    expected_result: Sequence[Result | Metric],
) -> None:
    assert list(create_check_azure_databases_dtu()(params, section)) == expected_result


@pytest.mark.parametrize(
    "section, params, expected_result",
    [
        pytest.param(
            Resource(
                id="/subscriptions/1234/resourceGroups/group/foo/bar/foo",
                name="foo",
                type="foo/bar",
                group="group",
                location="westeurope",
                metrics={
                    "average_connection_successful": AzureMetric(
                        name="connection_successful",
                        aggregation="average",
                        value=10,
                        unit="count",
                    ),
                    "average_connection_failed": AzureMetric(
                        name="connection_failed",
                        aggregation="average",
                        value=10,
                        unit="count",
                    ),
                },
            ),
            {},
            [
                RESULT_CONN_SUCCESS_OK,
                METRIC_CONN_SUCCESS_OK,
                RESULT_CONN_FAILED_OK,
                METRIC_CONN_FAILED_OK,
            ],
            id="DB connections without levels",
        ),
        pytest.param(
            Resource(
                id="/subscriptions/1234/resourceGroups/group/foo/bar/foo",
                name="foo",
                type="foo/bar",
                group="group",
                location="westeurope",
                metrics={
                    "average_connection_successful": AzureMetric(
                        name="connection_successful",
                        aggregation="average",
                        value=10,
                        unit="count",
                    ),
                    "average_connection_failed": AzureMetric(
                        name="connection_failed",
                        aggregation="average",
                        value=10,
                        unit="count",
                    ),
                },
            ),
            {"successful_connections": ("fixed", LEVELS), "failed_connections": ("fixed", LEVELS)},
            [
                RESULT_CONN_SUCCESS_WARN,
                METRIC_CONN_SUCCESS_WARN,
                RESULT_CONN_FAILED_WARN,
                METRIC_CONN_FAILED_WARN,
            ],
            id="Both DB connection metrics above WARN threshold",
        ),
        pytest.param(
            Resource(
                id="/subscriptions/1234/resourceGroups/group/foo/bar/foo",
                name="foo",
                type="foo/bar",
                group="group",
                location="westeurope",
                metrics={
                    "average_connection_successful": AzureMetric(
                        name="connection_successful",
                        aggregation="average",
                        value=10,
                        unit="count",
                    ),
                    "average_connection_failed": AzureMetric(
                        name="connection_failed",
                        aggregation="average",
                        value=10,
                        unit="count",
                    ),
                },
            ),
            check_plugin_azure_databases_connections.check_default_parameters,
            [
                Result(state=State.OK, summary="Successful connections: 10"),
                Metric("connections", 10.0),
                Result(state=State.CRIT, summary="Failed connections: 10 (warn/crit at 1/1)"),
                Metric("connections_failed_rate", 10.0, levels=(1.0, 1.0)),
            ],
            id="Default levels",
        ),
    ],
)
def test_check_azure_databases_connections(
    section: Resource,
    params: Mapping[str, Any],
    expected_result: Sequence[Result | Metric],
) -> None:
    assert list(create_check_azure_databases_connections()(params, section)) == expected_result
