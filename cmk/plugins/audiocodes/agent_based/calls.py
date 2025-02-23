#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Mapping, MutableMapping, Sequence
from dataclasses import dataclass
from typing import Any

from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    FixedLevelsT,
    get_rate,
    get_value_store,
    NoLevelsT,
    render,
    Service,
    SNMPSection,
    SNMPTree,
    StringTable,
)

from .lib import DETECT_AUDIOCODES


@dataclass(frozen=True, kw_only=True)
class Calls:
    active_calls: int
    total_calls: int
    average_success_ratio: int
    average_call_duration: int
    active_calls_in: int | None = None
    active_calls_out: int | None = None


def parse_audiocodes_calls(string_table: Sequence[StringTable]) -> Calls | None:
    return (
        Calls(
            active_calls=int(line[0][0]),
            total_calls=int(line[0][1]),
            average_success_ratio=int(line[0][2]),
            average_call_duration=int(line[0][3]),
            active_calls_in=int(string_table[1][0][0]) if string_table[1] else None,
            active_calls_out=int(string_table[1][0][1]) if string_table[1] else None,
        )
        if string_table[0] and (line := string_table[0])
        else None
    )


snmp_section_audiocodes_alarms = SNMPSection(
    name="audiocodes_calls",
    detect=DETECT_AUDIOCODES,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.5003.10.8.2",
            oids=[
                "52.43.1.2.0",  # AC-PM-Control-MIB::acPMSIPSBCEstablishedCallsVal.0
                "52.43.1.9.0",  # AC-PM-Control-MIB::acPMSIPSBCEstablishedCallsTotal.0
                "54.49.1.2.0",  # AC-PM-Control-MIB::acPMSBCAsrVal.0
                "54.52.1.2.0",  # AC-PM-Control-MIB::acPMSBCAcdVal.0
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.5003.15.3.1.1.1",
            oids=[
                "2",  # acKpiSbcCallStatsCurrentGlobalActiveCallsIn
                "3",  # acKpiSbcCallStatsCurrentGlobalActiveCallsOut
            ],
        ),
    ],
    parse_function=parse_audiocodes_calls,
)


def discover_audiocodes_calls(section: Calls) -> DiscoveryResult:
    yield Service()


def check_audiocodes_calls(
    params: Mapping[str, NoLevelsT | FixedLevelsT], section: Calls
) -> CheckResult:
    yield from check_audiocodes_calls_testable(
        params=params,
        section=section,
        now=time.time(),
        value_store=get_value_store(),
    )


def check_audiocodes_calls_testable(
    *,
    params: Mapping[str, NoLevelsT | FixedLevelsT],
    section: Calls,
    now: float,
    value_store: MutableMapping[str, Any],
) -> CheckResult:
    yield from check_levels(
        value=section.active_calls,
        label="Active Calls",
        metric_name="audiocodes_active_calls",
    )

    call_rate = get_rate(
        value_store,
        "total_calls",
        now,
        section.total_calls,
    )
    yield from check_levels(
        value=call_rate,
        label="Calls per Second",
        metric_name="audiocodes_calls_per_sec",
        render_func=lambda x: f"{x:.2f}/s",
    )

    yield from check_levels(
        value=section.average_success_ratio,
        levels_lower=params.get("asr_lower_levels"),
        render_func=render.percent,
        label="Average Succes Ratio",
        metric_name="audiocodes_average_success_ratio",
    )

    yield from check_levels(
        value=section.average_call_duration,
        label="Average Call Duration",
        metric_name="audiocodes_average_call_duration",
        render_func=render.timespan,
    )

    if section.active_calls_in is not None:
        yield from check_levels(
            value=section.active_calls_in,
            label="Active Calls In",
            metric_name="audiocodes_active_calls_in",
            notice_only=True,
        )

    if section.active_calls_out is not None:
        yield from check_levels(
            value=section.active_calls_out,
            label="Active Calls Out",
            metric_name="audiocodes_active_calls_out",
            notice_only=True,
        )


check_plugin_audiocodes_calls = CheckPlugin(
    name="audiocodes_calls",
    service_name="SBC Calls",
    discovery_function=discover_audiocodes_calls,
    check_function=check_audiocodes_calls,
    check_ruleset_name="audiocodes_calls",
    check_default_parameters={
        "asr_lower_levels": ("no_levels", None),
    },
)
