#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

#
# 2017 comNET GmbH, Bjoern Mueller

import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from itertools import chain
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.kentix.lib import DETECT_KENTIX


@dataclass(frozen=True)
class Sensor:
    value: int
    maximum: int


Section = Mapping[str, Sensor]


def parse_kentix_motion(string_table: Sequence[StringTable]) -> Section:
    return {
        index: Sensor(
            value=int(value),
            maximum=int(maximum),
        )
        for index, value, maximum in chain.from_iterable(string_table)
    }


def discover_kentix_motion(section: Section) -> DiscoveryResult:
    yield from (Service(item=index) for index in section)


def _test_in_period(
    time_tuple: tuple[int, int],
    periods: Sequence[tuple[tuple[int, int], tuple[int, int]]],
) -> bool:
    time_mins = time_tuple[0] * 60 + time_tuple[1]
    for per in periods:
        per_mins_low = per[0][0] * 60 + per[0][1]
        per_mins_high = per[1][0] * 60 + per[1][1]
        if per_mins_low <= time_mins < per_mins_high:
            return True
    return False


_WEEKDAYS = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)


def check_kentix_motion(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if (sensor := section.get(item)) is None:
        return

    today = time.localtime()
    if "time_periods" in params:
        periods = params["time_periods"][_WEEKDAYS[today.tm_wday]]
    else:
        periods = [((0, 0), (24, 0))]

    if sensor.value >= sensor.maximum:
        state = State.WARN if _test_in_period((today.tm_hour, today.tm_min), periods) else State.OK
        yield Result(state=state, summary="Motion detected")
    else:
        yield Result(state=State.OK, summary="No motion detected")
    yield Metric("motion", sensor.value, levels=(sensor.maximum, None), boundaries=(0, 100))


snmp_section_kentix_motion = SNMPSection(
    name="kentix_motion",
    detect=DETECT_KENTIX,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.37954.2.1.5",
            oids=["0", "1", "2"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.37954.3.1.5",
            oids=["0", "1", "2"],
        ),
    ],
    parse_function=parse_kentix_motion,
)


check_plugin_kentix_motion = CheckPlugin(
    name="kentix_motion",
    service_name="Motion Detector %s",
    discovery_function=discover_kentix_motion,
    check_function=check_kentix_motion,
    check_ruleset_name="motion",
    check_default_parameters={},
)
