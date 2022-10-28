#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from .agent_based_api.v1 import register, render, Result, State
from .agent_based_api.v1.type_defs import CheckResult
from .utils.azure import (
    check_azure_metrics,
    discover_azure_by_metrics,
    iter_resource_attributes,
    MetricData,
    parse_resources,
    Section,
)

register.agent_section(
    name="azure_virtualnetworkgateways",
    parse_function=parse_resources,
)


def check_azure_virtual_network_gateways(
    item: str, params: Mapping[str, tuple[float, float]], section: Section
) -> CheckResult:
    yield from check_azure_metrics(
        [
            MetricData(
                "maximum_P2SConnectionCount",
                "connections",
                "Point-to-site connections",
                lambda v: str(int(v)),
                lower_levels_param="connections_levels_lower",
                upper_levels_param="connections_levels_upper",
                boundaries=(0, None),
            ),
            MetricData(
                "average_P2SBandwidth",
                "p2s_bandwidth",
                "Point-to-site bandwidth",
                render.iobandwidth,
                lower_levels_param="p2s_bandwidth_levels_lower",
                upper_levels_param="p2s_bandwidth_levels_upper",
                boundaries=(0, None),
            ),
            MetricData(
                "average_AverageBandwidth",
                "s2s_bandwidth",
                "Site-to-site bandwidth",
                render.iobandwidth,
                lower_levels_param="s2s_bandwidth_levels_lower",
                upper_levels_param="s2s_bandwidth_levels_upper",
                boundaries=(0, None),
            ),
        ]
    )(item, params, section)

    for name, value in iter_resource_attributes(section[item]):
        yield Result(state=State.OK, summary=f"{name}: {value}")


register.check_plugin(
    name="azure_virtual_network_gateways",
    sections=["azure_virtualnetworkgateways"],
    service_name="VNet Gateway %s",
    discovery_function=discover_azure_by_metrics(
        "maximum_P2SConnectionCount", "average_P2SBandwidth", "average_AverageBandwidth"
    ),
    check_function=check_azure_virtual_network_gateways,
    check_ruleset_name="azure_virtualnetworkgateways",
    check_default_parameters={},
)
