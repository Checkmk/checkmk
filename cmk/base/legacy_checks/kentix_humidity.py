#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

from collections.abc import Iterable, Mapping
from typing import NamedTuple

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree
from cmk.plugins.kentix.lib import DETECT_KENTIX

check_info = {}


class Section(NamedTuple):
    reading: float
    lower_warn: float
    upper_warn: float
    text: str


def parse_kentix_humidity(string_table: list[list[list[str]]]) -> Section | None:
    info = string_table[0] or string_table[1]
    if not info:
        return None
    value, lower_warn, upper_warn, text = info[0]
    return Section(
        reading=float(value) / 10,
        lower_warn=float(lower_warn),
        upper_warn=float(upper_warn),
        text=text,
    )


def discover_kentix_humidity(section: Section) -> Iterable[tuple[None, dict]]:
    yield None, {}


def check_kentix_humidity(
    _no_item: None, _no_params: Mapping[str, object], section: Section
) -> Iterable:
    perfdata = [("humidity", section.reading, section.upper_warn, None)]
    infotext = (
        f"{section.reading:.1f}% (min/max at {section.lower_warn:.1f}%/{section.upper_warn:.1f}%)"
    )
    if section.reading >= section.upper_warn or section.reading <= section.lower_warn:
        state = 1
        infotext = f"{section.text}:  {infotext}"
    else:
        state = 0
    return state, infotext, perfdata


_OIDS = [
    "1",  # humidityValue
    "2",  # humidityMin
    "3",  # humidityMax
    "5",  # humidityAlarmtext
]


check_info["kentix_humidity"] = LegacyCheckDefinition(
    name="kentix_humidity",
    detect=DETECT_KENTIX,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.37954.2.1.2",
            oids=["1", "2", "3", "5"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.37954.3.1.2",
            oids=["1", "2", "3", "5"],
        ),
    ],
    parse_function=parse_kentix_humidity,
    service_name="Humidity",
    discovery_function=discover_kentix_humidity,
    check_function=check_kentix_humidity,
)
