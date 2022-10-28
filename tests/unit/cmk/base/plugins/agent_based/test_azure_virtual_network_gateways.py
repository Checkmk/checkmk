#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName, SectionName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.utils.azure import AzureMetric, Resource, Section

RESOURCE = {
    "TestGateway": Resource(
        id="/subscriptions/2fac104f-cb9c-461d-be57-037039662426/resourceGroups/Glastonbury/providers/Microsoft.Network/virtualNetworkGateways/TestGateway",
        name="TestGateway",
        type="Microsoft.Network/virtualNetworkGateways",
        group="Glastonbury",
        kind=None,
        location="westeurope",
        tags={},
        properties={},
        specific_info={},
        metrics={
            "average_AverageBandwidth": AzureMetric(
                name="AverageBandwidth",
                aggregation="average",
                value=13729.0,
                unit="bytes_per_second",
            ),
            "average_P2SBandwidth": AzureMetric(
                name="P2SBandwidth",
                aggregation="average",
                value=0.0,
                unit="bytes_per_second",
            ),
            "maximum_P2SConnectionCount": AzureMetric(
                name="P2SConnectionCount",
                aggregation="maximum",
                value=1.0,
                unit="count",
            ),
        },
        subscription="2fac104f-cb9c-461d-be57-037039662426",
    )
}


@pytest.mark.parametrize(
    "info,expected_parsed",
    [
        (
            [
                ["Resource"],
                [
                    '{"group": "Glastonbury", "name": "TestGateway", "location": "westeurope", "provider": "Microsoft.Network", "type": "Microsoft.Network/virtualNetworkGateways", "id": "/subscriptions/2fac104f-cb9c-461d-be57-037039662426/resourceGroups/Glastonbury/providers/Microsoft.Network/virtualNetworkGateways/TestGateway", "subscription": "2fac104f-cb9c-461d-be57-037039662426"}'
                ],
                ["metrics following", "3"],
                [
                    '{"filter": null, "unit": "bytes_per_second", "name": "AverageBandwidth", "interval_id": "PT1M", "timestamp": "1545049860", "interval": "0:01:00", "aggregation": "average", "value": 13729.0}'
                ],
                [
                    '{"name": "P2SBandwidth", "aggregation": "average", "value": 0.0, "unit": "bytes_per_second", "timestamp": "1545050040", "interval_id": "PT1M", "interval": "0:01:00", "filter": null}'
                ],
                [
                    '{"name": "P2SConnectionCount", "aggregation": "maximum", "value": 1.0, "unit": "count", "timestamp": "1545050040", "interval_id": "PT1M", "interval": "0:01:00", "filter":   null}'
                ],
            ],
            RESOURCE,
        ),
    ],
)
def test_parse_virtual_network_gateways(
    fix_register: FixRegister,
    info: Sequence[Sequence[str]],
    expected_parsed: Section,
) -> None:
    section_plugin = fix_register.agent_sections[SectionName("azure_virtualnetworkgateways")]
    result = section_plugin.parse_function(info)
    assert result == expected_parsed


@pytest.mark.parametrize(
    "section, expected_discovery",
    [
        (
            RESOURCE,
            [Service(item="TestGateway")],
        ),
    ],
)
def test_discovery_virtual_network_gateways(
    fix_register: FixRegister,
    section: Section,
    expected_discovery: Sequence[Service],
) -> None:
    check_plugin = fix_register.check_plugins[CheckPluginName("azure_virtualnetworkgateways")]
    assert list(check_plugin.discovery_function(section)) == expected_discovery


@pytest.mark.parametrize(
    "section, item, params, expected_result",
    [
        (
            RESOURCE,
            "TestGateway",
            {"s2s_bandwidth_levels_upper": (12000, 14000)},
            [
                Result(state=State.OK, summary="Point-to-site connections: 1"),
                Metric("connections", 1.0, boundaries=(0.0, None)),
                Result(state=State.OK, summary="Point-to-site bandwidth: 0.00 B/s"),
                Metric("p2s_bandwidth", 0.0, boundaries=(0.0, None)),
                Result(
                    state=State.WARN,
                    summary="Site-to-site bandwidth: 13.7 kB/s (warn/crit at 12.0 kB/s/14.0 kB/s)",
                ),
                Metric("s2s_bandwidth", 13729.0, levels=(12000.0, 14000.0), boundaries=(0.0, None)),
                Result(state=State.OK, summary="Location: westeurope"),
            ],
        ),
    ],
)
def test_check_virtual_network_gateways(
    fix_register: FixRegister,
    section: Section,
    item: str,
    params: Mapping[str, tuple[float, float]],
    expected_result: Sequence[Result | Metric],
) -> None:
    check_plugin = fix_register.check_plugins[CheckPluginName("azure_virtualnetworkgateways")]
    assert (
        list(check_plugin.check_function(item=item, params=params, section=section))
        == expected_result
    )
