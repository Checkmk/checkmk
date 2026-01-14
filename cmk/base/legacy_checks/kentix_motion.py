#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="comparison-overlap"

# mypy: disable-error-code="redundant-expr"

# mypy: disable-error-code="type-arg"

#
# 2017 comNET GmbH, Bjoern Mueller

import time
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from itertools import chain
from typing import Any

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.kentix.lib import DETECT_KENTIX

check_info = {}


@dataclass(frozen=True)
class Sensor:
    value: int
    maximum: int


Section = Mapping[str, Sensor]


def parse_kentix_motion(string_table: list[StringTable]) -> Section:
    return {
        index: Sensor(
            value=int(value),
            maximum=int(maximum),
        )
        for index, value, maximum in chain.from_iterable(string_table)
    }


def discover_kentix_motion(section: Section) -> Iterable[tuple[str, dict]]:
    yield from ((index, {}) for index in section)


def check_kentix_motion(
    item: str, params: Mapping[str, Any], section: Section
) -> Iterable[tuple[int, str, list]]:
    def test_in_period(
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

    if (sensor := section.get(item)) is None:
        return

    weekdays = [
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    ]
    today = time.localtime()
    if params is not None and "time_periods" in params:
        periods = params["time_periods"][weekdays[today.tm_wday]]
    else:
        periods = [((0, 0), (24, 0))]

    if sensor.value >= sensor.maximum:
        status = 1 if test_in_period((today.tm_hour, today.tm_min), periods) else 0
        yield status, "Motion detected", [("motion", sensor.value, sensor.maximum, None, 0, 100)]
    else:
        yield 0, "No motion detected", [("motion", sensor.value, sensor.maximum, None, 0, 100)]


check_info["kentix_motion"] = LegacyCheckDefinition(
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
    service_name="Motion Detector %s",
    discovery_function=discover_kentix_motion,
    check_function=check_kentix_motion,
    check_ruleset_name="motion",
)
