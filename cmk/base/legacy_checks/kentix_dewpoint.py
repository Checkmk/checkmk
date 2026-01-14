#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

from collections.abc import Iterable, Mapping

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree
from cmk.base.check_legacy_includes.temperature import check_temperature, TempParamType
from cmk.plugins.kentix.lib import DETECT_KENTIX

check_info = {}

#
# 2017 comNET GmbH, Bjoern Mueller

Section = Mapping[str, float]


def parse_kentix_dewpoint(string_table: list[list[str]]) -> Section | None:
    if not string_table:
        return None
    for item, reading in zip(("LAN", "Rack"), string_table[0]):
        try:
            return {item: float(reading) / 10}
        except ValueError:
            pass
    return {}


def discover_kentix_dewpoint(section: Section) -> Iterable[tuple[str, dict]]:
    yield from ((item, {}) for item in section)


def check_kentix_dewpoint(item: str, params: TempParamType, section: Section) -> Iterable:
    if (reading := section.get(item)) is None:
        return
    yield check_temperature(reading, params, "kentix_temp_%s" % item)


check_info["kentix_dewpoint"] = LegacyCheckDefinition(
    name="kentix_dewpoint",
    detect=DETECT_KENTIX,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.37954",
        oids=["2.1.3.1", "3.1.2.1"],
    ),
    parse_function=parse_kentix_dewpoint,
    service_name="Dewpoint %s",
    discovery_function=discover_kentix_dewpoint,
    check_function=check_kentix_dewpoint,
    check_ruleset_name="temperature",
)
