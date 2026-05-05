#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import collections
from collections.abc import Mapping
from typing import Any, TypedDict

from cmk.agent_based.legacy.conversion import convert_legacy_results
from cmk.agent_based.legacy.v0_unstable import check_levels
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    startswith,
    State,
    StringTable,
)

# Default levels: issue a WARN/CRIT if 1%/2% of read or write IO
# operations have a latency of 10-20 ms or above.
NimbleReadsType = "read"
NimbleWritesType = "write"

# Type aliases for the parsed data structure
type LatencyRanges = collections.OrderedDict[str, tuple[str, int]]


class LatencyData(TypedDict, total=False):
    total: int
    ranges: LatencyRanges


type VolumeData = dict[str, LatencyData]
type ParsedNimbleLatency = dict[str, VolumeData]


def parse_nimble_read_latency(string_table: StringTable) -> ParsedNimbleLatency:
    range_keys = [
        ("total", "Total"),
        ("0.1", "0-0.1 ms"),
        ("0.2", "0.1-0.2 ms"),
        ("0.5", "0.2-0.5 ms"),
        ("1", "0.5-1.0 ms"),
        ("2", "1-2 ms"),
        ("5", "2-5 ms"),
        ("10", "5-10 ms"),
        ("20", "10-20 ms"),
        ("50", "20-50 ms"),
        ("100", "50-100 ms"),
        ("200", "100-200 ms"),
        ("500", "200-500 ms"),
        ("1000", "500+ ms"),
    ]
    parsed: ParsedNimbleLatency = {}

    for line in string_table:
        vol_name = line[0]
        for ty, start_idx in [
            (NimbleReadsType, 1),
            (NimbleWritesType, 15),
        ]:
            values = line[start_idx : start_idx + 14]
            latencies: LatencyData = {}
            for (key, title), value_str in zip(range_keys, values):
                try:
                    value = int(value_str)
                except ValueError:
                    continue
                if key == "total":
                    latencies["total"] = value
                    continue
                # maintain the key order so that long output is sorted later
                latencies.setdefault("ranges", collections.OrderedDict())[key] = title, value
            parsed.setdefault(vol_name, {}).setdefault(ty, latencies)

    return parsed


def _discover_nimble_latency(section: ParsedNimbleLatency, ty: str) -> DiscoveryResult:
    for vol_name, vol_attrs in section.items():
        if vol_attrs.get(ty):
            yield Service(item=vol_name)


def _check_nimble_latency(params: Mapping[str, Any], data: VolumeData, ty: str) -> CheckResult:
    ty_data = data.get(ty)
    if ty_data is None:
        return

    total_value = ty_data["total"]
    if total_value == 0:
        yield Result(state=State.OK, summary=f"No current {ty} operations")
        return

    range_reference = float(params["range_reference"])
    running_total_percent = 0.0
    breakdown_results = []
    for key, (title, value) in ty_data["ranges"].items():
        metric_name = f"nimble_{ty}_latency_{key.replace('.', '')}"
        percent_value = value / total_value * 100

        if float(key) >= range_reference:
            running_total_percent += percent_value

        breakdown_results.append(
            check_levels(
                value=percent_value,
                dsname=metric_name,
                params=None,
                human_readable_func=render.percent,
                infoname=title,
            )
        )

    aggregate = check_levels(
        value=running_total_percent,
        dsname=None,
        params=params[ty],
        human_readable_func=render.percent,
        infoname=f"At or above {ty_data['ranges'][params['range_reference']][0]}",
    )

    yield from convert_legacy_results(
        [
            aggregate,
            (0, "\nLatency breakdown:", []),
            *breakdown_results,
        ]
    )


def check_nimble_latency_reads(
    item: str, params: Mapping[str, Any], section: ParsedNimbleLatency
) -> CheckResult:
    if not (data := section.get(item)):
        return
    yield from _check_nimble_latency(params, data, NimbleReadsType)


def discover_nimble_latency(section: ParsedNimbleLatency) -> DiscoveryResult:
    yield from _discover_nimble_latency(section, NimbleReadsType)


snmp_section_nimble_latency = SimpleSNMPSection(
    name="nimble_latency",
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.37447.3.1"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.37447.1.2.1",
        oids=[
            "3",
            "13",
            "21",
            "22",
            "23",
            "24",
            "25",
            "26",
            "27",
            "28",
            "29",
            "30",
            "31",
            "32",
            "33",
            "34",
            "39",
            "40",
            "41",
            "42",
            "43",
            "44",
            "45",
            "46",
            "47",
            "48",
            "49",
            "50",
            "51",
        ],
    ),
    parse_function=parse_nimble_read_latency,
)


check_plugin_nimble_latency = CheckPlugin(
    name="nimble_latency",
    service_name="Volume %s Read IO",
    discovery_function=discover_nimble_latency,
    check_function=check_nimble_latency_reads,
    check_ruleset_name="nimble_latency",
    check_default_parameters={
        # The latency range that is used to start measuring against levels.
        # The numbers of operations of and above this range are added and then
        # taken as a percentage of the total number of operations.
        "range_reference": "20",
        # These are percentage values!
        "read": (10.0, 20.0),
        "write": (10.0, 20.0),
    },
)


def check_nimble_latency_writes(
    item: str, params: Mapping[str, Any], section: ParsedNimbleLatency
) -> CheckResult:
    if not (data := section.get(item)):
        return
    yield from _check_nimble_latency(params, data, NimbleWritesType)


def discover_nimble_latency_write(section: ParsedNimbleLatency) -> DiscoveryResult:
    yield from _discover_nimble_latency(section, NimbleWritesType)


check_plugin_nimble_latency_write = CheckPlugin(
    name="nimble_latency_write",
    service_name="Volume %s Write IO",
    sections=["nimble_latency"],
    discovery_function=discover_nimble_latency_write,
    check_function=check_nimble_latency_writes,
    check_ruleset_name="nimble_latency",
    check_default_parameters={
        # The latency range that is used to start measuring against levels.
        # The numbers of operations of and above this range are added and then
        # taken as a percentage of the total number of operations.
        "range_reference": "20",
        # These are percentage values!
        "read": (10.0, 20.0),
        "write": (10.0, 20.0),
    },
)
