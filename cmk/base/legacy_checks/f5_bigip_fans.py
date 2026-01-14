#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree
from cmk.base.check_legacy_includes.fan import check_fan
from cmk.plugins.f5_bigip.lib import F5_BIGIP

check_info = {}

# Agent / MIB output
# see 1.3.6.1.4.1.3375.2.1.3.2.1.1.0
# F5-BIGIP-SYSTEM-MIB::sysChassisFanIndex.1   .1.3.6.1.4.1.3375.2.1.3.2.1.1.1 = 1
# F5-BIGIP-SYSTEM-MIB::sysChassisFanIndex.2   .1.3.6.1.4.1.3375.2.1.3.2.1.1.2 = 2
# F5-BIGIP-SYSTEM-MIB::sysChassisFanIndex.3   .1.3.6.1.4.1.3375.2.1.3.2.1.1.3 = 3
# F5-BIGIP-SYSTEM-MIB::sysChassisFanIndex.4   .1.3.6.1.4.1.3375.2.1.3.2.1.1.4 = 4
# F5-BIGIP-SYSTEM-MIB::sysChassisFanSpeed.1   .1.3.6.1.4.1.3375.2.1.3.2.1.3.1 = 2915
# F5-BIGIP-SYSTEM-MIB::sysChassisFanSpeed.2   .1.3.6.1.4.1.3375.2.1.3.2.1.3.2 = 2930
# F5-BIGIP-SYSTEM-MIB::sysChassisFanSpeed.3   .1.3.6.1.4.1.3375.2.1.3.2.1.3.3 = 2945
# F5-BIGIP-SYSTEM-MIB::sysChassisFanSpeed.4   .1.3.6.1.4.1.3375.2.1.3.2.1.3.4 = 2960
# see 1.3.6.1.4.1.3375.2.1.3.6.1.0
# F5-BIGIP-SYSTEM-MIB::sysCpuSensorFanSpeed.1.1.   1.3.6.1.4.1.3375.2.1.3.6.2.1.3.1.1 = 4715
# F5-BIGIP-SYSTEM-MIB::sysCpuSensorFanSpeed.2.1.   1.3.6.1.4.1.3375.2.1.3.6.2.1.3.2.1 = 4730
# F5-BIGIP-SYSTEM-MIB::sysCpuSensorName.1.1.       1.3.6.1.4.1.3375.2.1.3.6.2.1.4.1.1 = 1/cpu1
# F5-BIGIP-SYSTEM-MIB::sysCpuSensorName.2.1.       1.3.6.1.4.1.3375.2.1.3.6.2.1.4.2.1 = 2/cpu1


def parse_f5_bigip_fans(string_table):
    fantyp = ["Chassis", "Processor"]
    fanchoice = 0
    parsed: dict[str, tuple[int, int | None]] = {}

    for line in string_table:
        for fanentry in line:
            if fanchoice >= len(fantyp):
                continue
            if fanchoice == 0:
                parsed[("%s %d" % (fantyp[fanchoice], int(fanentry[0])))] = (
                    int(fanentry[2]),
                    int(fanentry[1]),
                )
            else:
                parsed[(f"{fantyp[fanchoice]} {fanentry[0]}")] = (int(fanentry[1]), None)
        fanchoice += 1

    return parsed


def discover_f5_bigip_fans(parsed):
    for item in parsed.keys():
        yield item, {}


def check_f5_bigip_fans(item, params, parsed):
    fanspeed, fanstatus = parsed.get(item)

    # Status Map:
    # 0: Bad
    # 1: Good
    # 2: Not Present
    if fanspeed == 0 and fanstatus == 1:
        yield 0, "Fan Status: OK"
        return

    if fanspeed is None:
        # do not change this to if not fanspeed! fanspeed could be 0.
        yield 3, "Could not detect speed"
        return

    yield check_fan(fanspeed, params)


# Get ID and Speed from the CPU and chassis fan tables

check_info["f5_bigip_fans"] = LegacyCheckDefinition(
    name="f5_bigip_fans",
    detect=F5_BIGIP,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.3375.2.1.3.2.1.2.1",
            oids=["1", "2", "3"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.3375.2.1.3.6.2.1",
            oids=["4", "3"],
        ),
    ],
    parse_function=parse_f5_bigip_fans,
    service_name="FAN %s",
    discovery_function=discover_f5_bigip_fans,
    check_function=check_f5_bigip_fans,
    check_ruleset_name="hw_fans",
    check_default_parameters={"lower": (2000, 500)},
)
