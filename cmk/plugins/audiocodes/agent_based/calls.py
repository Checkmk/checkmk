#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    FixedLevelsT,
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
    average_call_duration: int | None
    active_calls_in: int | None
    active_calls_out: int | None
    established_calls_rate_in: int | None
    established_calls_rate_out: int | None
    answer_seizure_ratio: int | None
    network_effectiveness_ratio: int | None
    abnormal_terminated_calls_in_total: int | None
    abnormal_terminated_calls_out_total: int | None


def parse_audiocodes_calls(string_table: Sequence[StringTable]) -> Calls | None:
    # We treat all the values as possibly missing
    return (
        Calls(
            average_call_duration=int(val) if (val := line[0][0]) else None,
            active_calls_in=int(val) if (val := line[0][1]) else None,
            active_calls_out=int(val) if (val := line[0][2]) else None,
            established_calls_rate_in=int(val) if (val := line[0][3]) else None,
            established_calls_rate_out=int(val) if (val := line[0][4]) else None,
            answer_seizure_ratio=int(val) if (val := line[0][5]) else None,
            network_effectiveness_ratio=int(val) if (val := line[0][6]) else None,
            abnormal_terminated_calls_in_total=int(val) if (val := line[0][7]) else None,
            abnormal_terminated_calls_out_total=int(val) if (val := line[0][8]) else None,
        )
        if string_table[0] and (line := string_table[0])
        else None
    )


snmp_section_audiocodes_alarms = SNMPSection(
    name="audiocodes_calls",
    detect=DETECT_AUDIOCODES,
    fetch=[
        # The data we collect here and the OIDs we use assume AudioCodes v7.4
        # audiocodes.com/media/15570/sbc-gateway-performance-monitoring-reference-guide-ver-74.pdf
        # (page numbers below are document page, not pdf page)
        SNMPTree(
            base=".1.3.6.1.4.1.5003.15.3.1.1.1",
            oids=[
                "1",  # Average Call Duration (p. 556)
                "2",  # Active Calls In (p. 539)
                "3",  # Active Calls Out (p. 542)
                "10",  # Established Calls Rate In (p. 565)
                "11",  # Established Calls Rate Out (p. 567)
                "12",  # Answer Seizure Ratio (p. 548)
                "13",  # Network Effectiveness Ratio (p. 581)
                "35",  # Abnormal Terminated Calls In Total (p. 535)
                "36",  # Abnormal Terminated Calls Out Total (p. 537)
            ],
        ),
    ],
    parse_function=parse_audiocodes_calls,
)


def discover_audiocodes_calls(section: Calls) -> DiscoveryResult:
    yield Service()


def check_audiocodes_calls(
    params: Mapping[str, NoLevelsT | FixedLevelsT],
    section: Calls,
) -> CheckResult:
    yield from check_audiocodes_calls_testable(
        params=params,
        section=section,
    )


def check_audiocodes_calls_testable(
    *,
    params: Mapping[str, NoLevelsT | FixedLevelsT],
    section: Calls,
) -> CheckResult:
    if section.average_call_duration is not None:
        yield from check_levels(
            value=section.average_call_duration,
            label="Average call duration",
            metric_name="audiocodes_average_call_duration",
            render_func=render.timespan,
            notice_only=True,
        )
    if section.active_calls_in is not None:
        yield from check_levels(
            value=section.active_calls_in,
            label="Active calls in",
            metric_name="audiocodes_active_calls_in",
            render_func=lambda x: str(x),
        )
    if section.active_calls_out is not None:
        yield from check_levels(
            value=section.active_calls_out,
            label="Active calls out",
            metric_name="audiocodes_active_calls_out",
            render_func=lambda x: str(x),
        )
    if section.established_calls_rate_in is not None:
        yield from check_levels(
            value=section.established_calls_rate_in,
            label="Established calls in rate",
            metric_name="audiocodes_established_calls_in",
            render_func=lambda x: f"{x:.2f}/s",
            notice_only=True,
        )
    if section.established_calls_rate_out is not None:
        yield from check_levels(
            value=section.established_calls_rate_out,
            label="Established calls out rate",
            metric_name="audiocodes_established_calls_out",
            render_func=lambda x: f"{x:.2f}/s",
            notice_only=True,
        )
    if section.answer_seizure_ratio is not None:
        yield from check_levels(
            value=section.answer_seizure_ratio,
            label="Answer seizure ratio",
            metric_name="audiocodes_answer_seizure_ratio",
            render_func=render.percent,
            notice_only=True,
            levels_lower=params.get("answer_seizure_ratio_lower_levels"),
        )
    if section.network_effectiveness_ratio is not None:
        yield from check_levels(
            value=section.network_effectiveness_ratio,
            label="Network effectiveness ratio",
            metric_name="audiocodes_network_effectiveness_ratio",
            render_func=render.percent,
            notice_only=True,
            levels_lower=params.get("network_effectiveness_ratio_lower_levels"),
        )
    if section.abnormal_terminated_calls_in_total is not None:
        yield from check_levels(
            value=section.abnormal_terminated_calls_in_total,
            label="Abnormal terminated calls in",
            metric_name="audiocodes_abnormal_terminated_calls_in_total",
            render_func=lambda x: str(x),
            notice_only=True,
        )
    if section.abnormal_terminated_calls_out_total is not None:
        yield from check_levels(
            value=section.abnormal_terminated_calls_out_total,
            label="Abnormal terminated calls out",
            metric_name="audiocodes_abnormal_terminated_calls_out_total",
            render_func=lambda x: str(x),
            notice_only=True,
        )


check_plugin_audiocodes_calls = CheckPlugin(
    name="audiocodes_calls",
    service_name="SBC calls",
    discovery_function=discover_audiocodes_calls,
    check_function=check_audiocodes_calls,
    check_ruleset_name="audiocodes_calls",
    check_default_parameters={
        "answer_seizure_ratio_lower_levels": ("fixed", (60.0, 50.0)),
        "network_effectiveness_ratio_lower_levels": ("fixed", (95.0, 90.0)),
    },
)
