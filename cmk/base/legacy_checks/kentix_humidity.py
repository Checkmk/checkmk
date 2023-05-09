#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Mapping
from typing import NamedTuple

from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.kentix import DETECT_KENTIX


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


def inventory_kentix_humidity(section: Section) -> Iterable[tuple[None, dict]]:
    yield None, {}


def check_kentix_humidity(
    _no_item: None, _no_params: Mapping[str, object], section: Section
) -> Iterable:
    perfdata = [("humidity", section.reading, section.upper_warn, None)]
    infotext = "%.1f%% (min/max at %.1f%%/%.1f%%)" % (
        section.reading,
        section.lower_warn,
        section.upper_warn,
    )
    if section.reading >= section.upper_warn or section.reading <= section.lower_warn:
        state = 1
        infotext = "%s:  %s" % (section.text, infotext)
    else:
        state = 0
    return state, infotext, perfdata


_OIDS = [
    "1",  # humidityValue
    "2",  # humidityMin
    "3",  # humidityMax
    "5",  # humidityAlarmtext
]


check_info["kentix_humidity"] = {
    "detect": DETECT_KENTIX,
    "parse_function": parse_kentix_humidity,
    "check_function": check_kentix_humidity,
    "discovery_function": inventory_kentix_humidity,
    "service_name": "Humidity",
    "fetch": [
        SNMPTree(
            base=".1.3.6.1.4.1.37954.2.1.2",
            oids=["1", "2", "3", "5"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.37954.3.1.2",
            oids=["1", "2", "3", "5"],
        ),
    ],
}
