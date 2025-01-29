#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)

from .detection import DETECT_BLADE

# The BLADE-MIB is somewhat goofy redarding the blower
# information. The blowers are listed sequentially
# below the same subtrees:

# BLADE-MIB::blower1speed.0 = STRING: "50% of maximum"
# BLADE-MIB::blower2speed.0 = STRING: "50% of maximum"
# BLADE-MIB::blower1State.0 = INTEGER: good(1)
# BLADE-MIB::blower2State.0 = INTEGER: good(1)
# BLADE-MIB::blowers.20.0 = STRING: "1712"
# BLADE-MIB::blowers.21.0 = STRING: "1696"
# BLADE-MIB::blowers.30.0 = INTEGER: 0
# BLADE-MIB::blowers.31.0 = INTEGER: 0
#
# The same with -On:
# .1.3.6.1.4.1.2.3.51.2.2.3.1.0 = STRING: "49% of maximum"
# .1.3.6.1.4.1.2.3.51.2.2.3.2.0 = STRING: "No Blower"
# .1.3.6.1.4.1.2.3.51.2.2.3.10.0 = INTEGER: good(1)
# .1.3.6.1.4.1.2.3.51.2.2.3.11.0 = INTEGER: unknown(0)
# .1.3.6.1.4.1.2.3.51.2.2.3.20.0 = STRING: "1696"
# .1.3.6.1.4.1.2.3.51.2.2.3.21.0 = STRING: "No Blower"
# .1.3.6.1.4.1.2.3.51.2.2.3.30.0 = INTEGER: 0
# .1.3.6.1.4.1.2.3.51.2.2.3.31.0 = INTEGER: 2
#
# How can we safely determine the number of blowers without
# assuming that each blower has four entries?


# We assume that all blowers are in state OK (used for
# inventory only)


def number_of_blowers(info: StringTable) -> int:
    n = 0
    while len(info) > n and len(info[n][0]) > 1:  # state lines
        n += 1
    return n


def inventory_blade_blowers(section: StringTable) -> DiscoveryResult:
    n = number_of_blowers(section)
    for i in range(0, n):
        if section[i + n][0] != "0":  # skip unknown blowers
            yield Service(item="%d/%d" % (i + 1, n))


# This can be done much better; but I'm resisting the temptation to rewrite this.
# This is a result of a brainless migration from an much older API.
def check_blade_blowers(item: str, section: StringTable) -> CheckResult:
    blower, num_blowers = map(int, item.split("/"))
    text = section[blower - 1][0]
    perfdata: list[Metric] = []
    output = ""

    state = section[blower - 1 + num_blowers][0]

    try:
        rpm = int(section[blower - 1 + 2 * num_blowers][0])
        perfdata += [Metric("rpm", rpm)]
        output += "Speed at %d RMP" % rpm
    except Exception:
        pass

    try:
        perc = int(text.split("%")[0])
        perfdata += [Metric("perc", perc, boundaries=(0, 100))]
        if output == "":
            output += "Speed is at %d%% of max" % perc
        else:
            output += " (%d%% of max)" % perc
    except Exception:
        pass

    if state == "1":
        yield Result(state=State.OK, summary=output)
        yield from perfdata
        return

    yield Result(state=State.CRIT, summary=output)
    yield from perfdata
    return


def parse_blade_blowers(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_blade_blowers = SimpleSNMPSection(
    name="blade_blowers",
    detect=DETECT_BLADE,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2.3.51.2.2",
        oids=["3"],
    ),
    parse_function=parse_blade_blowers,
)
check_plugin_blade_blowers = CheckPlugin(
    name="blade_blowers",
    service_name="Blower %s",
    discovery_function=inventory_blade_blowers,
    check_function=check_blade_blowers,
)
