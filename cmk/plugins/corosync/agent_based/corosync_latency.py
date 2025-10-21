#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TypedDict

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    FixedLevelsT,
    NoLevelsT,
    render,
    Result,
    Service,
    State,
    StringTable,
)


@dataclass(kw_only=True, frozen=True)
class Link:
    hostname: str
    name: str
    connected: bool
    latency_ave: float
    latency_max: float
    latency_min: float
    latency_samples: float


SectionCorosyncLatency = Mapping[str, Link]


class Params(TypedDict):
    latency_max: NoLevelsT | FixedLevelsT[float]
    latency_ave: NoLevelsT | FixedLevelsT[float]


def parse_corosync_latency(string_table: StringTable) -> SectionCorosyncLatency:
    data: dict[str, dict[str, dict[str, float]]] = {}

    if not string_table or not string_table[0]:
        return {}

    for metric, *_, raw_value in string_table:
        _, _, host, link, key = metric.split(".")
        data.setdefault(host, {}).setdefault(link, {})[key] = float(raw_value)

    return {
        f"{host}.{link_name}": Link(
            hostname=host,
            name=link_name,
            connected=bool(link_data["connected"]),
            latency_ave=link_data["latency_ave"],
            latency_max=link_data["latency_max"],
            latency_min=link_data["latency_min"],
            latency_samples=link_data["latency_samples"],
        )
        for host, host_links in data.items()
        for link_name, link_data in host_links.items()
    }


agent_section_corosync_latency = AgentSection(
    name="corosync_latency",
    parse_function=parse_corosync_latency,
)


def discover_corosync_latency(section: SectionCorosyncLatency) -> DiscoveryResult:
    for item, link in section.items():
        if link.latency_samples == 0 and link.connected is True:
            # We are skipping links that are connected but have no samples
            # as they did not have any traffic
            continue
        yield Service(item=item)


def check_corosync_latency(
    item: str,
    params: Params,
    section: SectionCorosyncLatency,
) -> CheckResult:
    if (link := section.get(item)) is None:
        return

    if link.connected is False:
        yield Result(state=State.CRIT, summary="Link is not connected or down")
        return

    yield from check_levels(
        value=link.latency_max / 1_000_000,  # Value is in microseconds -> convert to seconds
        metric_name="latency_max",
        label="Latency Max",
        levels_upper=params["latency_max"],
        render_func=render.timespan,
    )

    yield from check_levels(
        value=link.latency_ave / 1_000_000,  # Value is in microseconds -> convert to seconds
        metric_name="latency_ave",
        label="Latency Average",
        levels_upper=params["latency_ave"],
        render_func=render.timespan,
    )


check_plugin_corosync_latency = CheckPlugin(
    name="corosync_latency",
    service_name="Corosync Latency %s",
    discovery_function=discover_corosync_latency,
    check_function=check_corosync_latency,
    check_ruleset_name="corosync_latency",
    check_default_parameters={
        "latency_max": ("fixed", (5.0, 10.0)),
        "latency_ave": ("fixed", (5.0, 10.0)),
    },
)
