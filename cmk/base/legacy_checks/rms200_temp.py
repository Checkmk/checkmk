#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import equals, SNMPTree, StringTable
from cmk.base.check_legacy_includes.temperature import check_temperature

check_info = {}


def discover_rms200_temp(info):
    for line in info:
        if line[2] != "-27300":
            yield (line[0], {})
        # otherwise no sensor is connected


def check_rms200_temp(item, params, info):
    for line in info:
        if line[0] == item:
            status, infotext, perfdata = check_temperature(
                float(line[2]) / 100, params, "rms200_temp_%s" % item
            )
            infotext += " (%s)" % line[1]  # Name from SNMP data
            return status, infotext, perfdata
    return None


def parse_rms200_temp(string_table: StringTable) -> StringTable:
    return string_table


check_info["rms200_temp"] = LegacyCheckDefinition(
    name="rms200_temp",
    parse_function=parse_rms200_temp,
    detect=equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.1909.13"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1909.13.1.1.1",
        oids=["1", "2", "5"],
    ),
    service_name="Temperature %s ",
    discovery_function=discover_rms200_temp,
    check_function=check_rms200_temp,
    check_ruleset_name="temperature",
    check_default_parameters={"levels": (25.0, 28.0)},
)
