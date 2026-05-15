#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import NamedTuple

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


class Section(NamedTuple):
    reading: float
    lower_warn: float
    upper_warn: float
    text: str


def parse_kentix_humidity(string_table: Sequence[StringTable]) -> Section | None:
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


def discover_kentix_humidity(section: Section) -> DiscoveryResult:
    yield Service()


def check_kentix_humidity(section: Section) -> CheckResult:
    summary = (
        f"{section.reading:.1f}% (min/max at {section.lower_warn:.1f}%/{section.upper_warn:.1f}%)"
    )
    if section.reading >= section.upper_warn or section.reading <= section.lower_warn:
        yield Result(state=State.WARN, summary=f"{section.text}:  {summary}")
    else:
        yield Result(state=State.OK, summary=summary)
    yield Metric("humidity", section.reading, levels=(section.upper_warn, None))


snmp_section_kentix_humidity = SNMPSection(
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
)


check_plugin_kentix_humidity = CheckPlugin(
    name="kentix_humidity",
    service_name="Humidity",
    discovery_function=discover_kentix_humidity,
    check_function=check_kentix_humidity,
)
