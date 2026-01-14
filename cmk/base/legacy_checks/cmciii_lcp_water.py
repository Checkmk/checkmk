#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="type-arg"

from collections.abc import Iterable

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.plugins.cmciii.lib import DETECT_CMCIII_LCP

check_info = {}

# Note: The CMCIII checks for Water IN/OUT and similar stuff are
# deep and fundamentally broken (such as the implementation of
# Rittal). Need to rewrite an make *one* check with subchecks.

# [['Fan Unit'],
#  ['V09.005'],
#  ['V0000'],
#  ['OK'],
#  ['2'],
#  ['Air-Temperatures'],
#  ['19.8 \xb0C'],
#  ['19.0 \xb0C'],
#  ['18.2 \xb0C'],
#  ['19.9 \xb0C'],
#  ['18.9 \xb0C'],
#  ...
#  ['Water Unit'],
#  ['V09.002'],
#  ['V0000'],
#  ['OK'],
#  ['2'],
#  ['Water-In'],
#  ['18.2 \xb0C'],
#  ['50.0 \xb0C'],
#  ['40.0 \xb0C'],
#  ...
# ]]


Section = list[str]


def parse_cmciii_lcp_water(string_table: StringTable) -> Section:
    units = {}
    unit_lines: list[str] | None = None
    for line in string_table:
        if line[0].endswith(" Unit"):
            unit_name = line[0].split(" ")[0]
            unit_lines = []
            units[unit_name] = unit_lines
        elif unit_lines is not None:
            unit_lines.append(line[0])

    if "Water" in units:
        return units["Water"]

    return []


def discover_cmciii_lcp_water(section: Section) -> Iterable[tuple[str, dict]]:
    if section:
        yield "IN", {}
        yield "OUT", {}


def check_cmciii_lcp_water(item, params, parsed):
    # New check: This sensor is handled by cmciii.temp
    if not parsed:
        return

    def parse_status(status_name):
        if status_name.lower() == "ok":
            return 0
        if status_name.lower() == "warning":
            return 1
        return 2

    unit_status_name = parsed[2]
    yield parse_status(unit_status_name), "Unit: %s" % unit_status_name

    if item == "IN":
        lines = parsed[5:12]
    else:
        lines = parsed[14:21]

    # ['18.2 \xb0C', '50.0 \xb0C', '40.0 \xb0C', '13.0 \xb0C', '10.0 \xb0C', '3 %', 'OK']

    temperatures = [float(x.split()[0]) for x in lines[0:5]]
    temp = temperatures[0]
    limits = temperatures[1:]
    status_name = lines[-1]

    status, info_text, perf_data = check_temperature(
        temp,
        params,
        "cmciii_lcp_water_" + item,
        dev_levels=(limits[1], limits[0]),
        dev_levels_lower=(limits[2], limits[3]),
        dev_status=parse_status(status_name),
        dev_status_name=status_name,
    )

    yield status, "Temperature: " + info_text, perf_data


check_info["cmciii_lcp_water"] = LegacyCheckDefinition(
    name="cmciii_lcp_water",
    detect=DETECT_CMCIII_LCP,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2606.7.4.2.2.1.10",
        oids=["2"],
    ),
    parse_function=parse_cmciii_lcp_water,
    service_name="Temperature Water LCP %s",
    discovery_function=discover_cmciii_lcp_water,
    check_function=check_cmciii_lcp_water,
    check_ruleset_name="temperature",
)
