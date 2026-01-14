#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

#
# 2017 comNET GmbH, Bjoern Mueller

# Default levels from http://www.detectcarbonmonoxide.com/co-health-risks/

from collections.abc import Iterable

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.kentix.lib import DETECT_KENTIX

check_info = {}


def parse_kentix_co(string_table: StringTable) -> int | None:
    if not string_table:
        return None
    for value in string_table[0]:
        try:
            return int(value)
        except ValueError:
            pass
    return None


def discover_kentix_co(section: int) -> Iterable[tuple[None, dict]]:
    yield None, {}


def check_kentix_co(item: str, params: dict, section: int) -> Iterable:
    return check_levels(
        section,
        "parts_per_million",
        params["levels_ppm"],
        human_readable_func=lambda x: f"{x} ppm",
        infoname="CO concentration",
    )


check_info["kentix_co"] = LegacyCheckDefinition(
    name="kentix_co",
    detect=DETECT_KENTIX,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.37954",
        oids=["2.1.4.1", "3.1.3.1"],
    ),
    parse_function=parse_kentix_co,
    service_name="Carbon Monoxide",
    discovery_function=discover_kentix_co,
    check_function=check_kentix_co,
    check_ruleset_name="carbon_monoxide",
    check_default_parameters={
        "levels_ppm": (10, 25),
    },
)
