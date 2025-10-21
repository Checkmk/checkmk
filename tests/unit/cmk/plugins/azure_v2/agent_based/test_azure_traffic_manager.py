#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import IgnoreResultsError, Metric, Result, State
from cmk.plugins.azure_v2.agent_based.azure_traffic_manager import (
    check_probe_state,
    check_qps,
    inventory_plugin_azure_traffic_manager,
)
from cmk.plugins.azure_v2.agent_based.lib import AzureMetric, Resource

from .inventory import get_inventory_value


@pytest.mark.parametrize(
    "section, params, expected_result",
    [
        (
            Resource(
                id="/subscriptions/c17d121d-dd5c-4156-875f-1df9862eef93/resourceGroups/Group1/providers/Microsoft.Network/trafficmanagerprofiles/traffic-manager-1",
                name="traffic-manager-1",
                type="Microsoft.Network/trafficmanagerprofiles",
                group="BurningMan",
                location="westeurope",
                metrics={
                    "total_QpsByEndpoint": AzureMetric(
                        name="QpsByEndpoint",
                        aggregation="total",
                        value=6000.0,
                        unit="count",
                    ),
                },
            ),
            {"levels": (10, 50)},
            [
                Result(state=State.CRIT, summary="Queries per second: 100 (warn/crit at 10/50)"),
                Metric("queries_per_sec", 100.0, levels=(10.0, 50.0)),
            ],
        ),
    ],
)
def test_check_qps(
    section: Resource,
    params: Mapping[str, Any],
    expected_result: Sequence[Result | Metric],
) -> None:
    assert list(check_qps(params, section)) == expected_result


@pytest.mark.parametrize(
    "section",
    [
        (
            Resource(
                id="/subscriptions/c17d121d-dd5c-4156-875f-1df9862eef93/resourceGroups/Group1/providers/Microsoft.Network/trafficmanagerprofiles/traffic-manager-1",
                name="traffic-manager-1",
                type="Microsoft.Network/trafficmanagerprofiles",
                group="BurningMan",
                location="westeurope",
                metrics={},
            )
        ),
    ],
)
def test_check_qps_stale(section: Resource) -> None:
    with pytest.raises(IgnoreResultsError, match="Data not present at the moment"):
        list(check_qps({}, section))


@pytest.mark.parametrize(
    "section, params, expected_result",
    [
        (
            Resource(
                id="/subscriptions/c17d121d-dd5c-4156-875f-1df9862eef93/resourceGroups/Group1/providers/Microsoft.Network/trafficmanagerprofiles/traffic-manager-1",
                name="traffic-manager-1",
                type="Microsoft.Network/trafficmanagerprofiles",
                group="BurningMan",
                location="westeurope",
                metrics={
                    "maximum_ProbeAgentCurrentEndpointStateByProfileResourceId": AzureMetric(
                        name="ProbeAgentCurrentEndpointStateByProfileResourceId",
                        aggregation="maximum",
                        value=0.0,
                        unit="count",
                    ),
                },
            ),
            {"custom_state": 1},
            [
                Result(state=State.WARN, summary="Probe state: not OK"),
            ],
        ),
        (
            Resource(
                id="/subscriptions/c17d121d-dd5c-4156-875f-1df9862eef93/resourceGroups/Group1/providers/Microsoft.Network/trafficmanagerprofiles/traffic-manager-1",
                name="traffic-manager-1",
                type="Microsoft.Network/trafficmanagerprofiles",
                group="BurningMan",
                location="westeurope",
                metrics={
                    "maximum_ProbeAgentCurrentEndpointStateByProfileResourceId": AzureMetric(
                        name="ProbeAgentCurrentEndpointStateByProfileResourceId",
                        aggregation="maximum",
                        value=1.0,
                        unit="count",
                    ),
                },
            ),
            {"custom_state": 1},
            [
                Result(state=State.OK, summary="Probe state: OK"),
            ],
        ),
    ],
)
def test_check_probe_state(
    section: Resource,
    params: Mapping[str, Any],
    expected_result: Sequence[Result | Metric],
) -> None:
    assert list(check_probe_state(params, section)) == expected_result


@pytest.mark.parametrize(
    "section",
    [
        (
            Resource(
                id="/subscriptions/c17d121d-dd5c-4156-875f-1df9862eef93/resourceGroups/Group1/providers/Microsoft.Network/trafficmanagerprofiles/traffic-manager-1",
                name="traffic-manager-1",
                type="Microsoft.Network/trafficmanagerprofiles",
                group="BurningMan",
                location="westeurope",
                metrics={},
            )
        ),
    ],
)
def test_check_probe_state_stale(section: Resource) -> None:
    with pytest.raises(IgnoreResultsError, match="Data not present at the moment"):
        list(check_probe_state({}, section))


def test_azure_traffic_manager_inventory() -> None:
    section = Resource(
        id="/subscriptions/c17d121d-dd5c-4156-875f-1df9862eef93/resourceGroups/Group1/providers/Microsoft.Network/trafficmanagerprofiles/traffic-manager-1",
        name="traffic-manager-1",
        type="Microsoft.Network/trafficmanagerprofiles",
        group="BurningMan",
        location="westeurope",
        metrics={
            "total_QpsByEndpoint": AzureMetric(
                name="QpsByEndpoint",
                aggregation="total",
                value=6000.0,
                unit="count",
            ),
        },
    )
    inventory = inventory_plugin_azure_traffic_manager.inventory_function(section)
    assert get_inventory_value(inventory, "Region") == "westeurope"
