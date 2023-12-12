#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import IgnoreResultsError, Metric, Result, State
from cmk.plugins.azure.agent_based.azure_traffic_manager import check_probe_state, check_qps
from cmk.plugins.lib.azure import AzureMetric, Resource, Section


@pytest.mark.parametrize(
    "section, item, params, expected_result",
    [
        (
            {
                "traffic-manager-1": Resource(
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
            },
            "traffic-manager-1",
            {"levels": (10, 50)},
            [
                Result(state=State.CRIT, summary="Queries per second: 100 (warn/crit at 10/50)"),
                Metric("queries_per_sec", 100.0, levels=(10.0, 50.0)),
            ],
        ),
    ],
)
def test_check_qps(
    section: Section,
    item: str,
    params: Mapping[str, Any],
    expected_result: Sequence[Result | Metric],
) -> None:
    assert list(check_qps(item, params, section)) == expected_result


@pytest.mark.parametrize(
    "section, item",
    [
        (
            {
                "traffic-manager-1": Resource(
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
            },
            "traffic-manager-2",
        ),
        (
            {
                "traffic-manager-1": Resource(
                    id="/subscriptions/c17d121d-dd5c-4156-875f-1df9862eef93/resourceGroups/Group1/providers/Microsoft.Network/trafficmanagerprofiles/traffic-manager-1",
                    name="traffic-manager-1",
                    type="Microsoft.Network/trafficmanagerprofiles",
                    group="BurningMan",
                    location="westeurope",
                    metrics={},
                )
            },
            "traffic-manager-1",
        ),
    ],
)
def test_check_qps_stale(section: Section, item: str) -> None:
    with pytest.raises(IgnoreResultsError, match="Data not present at the moment"):
        list(check_qps(item, {}, section))


@pytest.mark.parametrize(
    "section, item, params, expected_result",
    [
        (
            {
                "traffic-manager-1": Resource(
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
                )
            },
            "traffic-manager-1",
            {"custom_state": 1},
            [
                Result(state=State.WARN, summary="Probe state: not OK"),
            ],
        ),
        (
            {
                "traffic-manager-1": Resource(
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
                )
            },
            "traffic-manager-1",
            {"custom_state": 1},
            [
                Result(state=State.OK, summary="Probe state: OK"),
            ],
        ),
    ],
)
def test_check_probe_state(
    section: Section,
    item: str,
    params: Mapping[str, Any],
    expected_result: Sequence[Result | Metric],
) -> None:
    assert list(check_probe_state(item, params, section)) == expected_result


@pytest.mark.parametrize(
    "section, item",
    [
        (
            {},
            "traffic-manager-2",
        ),
        (
            {
                "traffic-manager-1": Resource(
                    id="/subscriptions/c17d121d-dd5c-4156-875f-1df9862eef93/resourceGroups/Group1/providers/Microsoft.Network/trafficmanagerprofiles/traffic-manager-1",
                    name="traffic-manager-1",
                    type="Microsoft.Network/trafficmanagerprofiles",
                    group="BurningMan",
                    location="westeurope",
                    metrics={},
                )
            },
            "traffic-manager-1",
        ),
    ],
)
def test_check_probe_state_stale(section: Section, item: str) -> None:
    with pytest.raises(IgnoreResultsError, match="Data not present at the moment"):
        list(check_probe_state(item, {}, section))
