#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.blade import DETECT_BLADE

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


# mypy: disable-error-code="list-item"


def number_of_blowers(info):
    n = 0
    while len(info) > n and len(info[n][0]) > 1:  # state lines
        n += 1
    return n


def inventory_blade_blowers(info):
    n = number_of_blowers(info)
    for i in range(0, n):
        if info[i + n][0] != "0":  # skip unknown blowers
            yield "%d/%d" % (i + 1, n), None


def check_blade_blowers(item, _no_params, info):
    blower, num_blowers = map(int, item.split("/"))
    text = info[blower - 1][0]
    perfdata = []
    output = ""

    state = info[blower - 1 + num_blowers][0]

    try:
        rpm = int(info[blower - 1 + 2 * num_blowers][0])
        perfdata += [("rpm", rpm)]
        output += "Speed at %d RMP" % rpm
    except Exception:
        pass

    try:
        perc = int(text.split("%")[0])
        perfdata += [("perc", perc, None, None, 0, 100)]
        if output == "":
            output += "Speed is at %d%% of max" % perc
        else:
            output += " (%d%% of max)" % perc
    except Exception:
        pass

    if state == "1":
        return (0, output, perfdata)
    return (2, output, perfdata)


check_info["blade_blowers"] = LegacyCheckDefinition(
    detect=DETECT_BLADE,
    check_function=check_blade_blowers,
    discovery_function=inventory_blade_blowers,
    service_name="Blower %s",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2.3.51.2.2",
        oids=["3"],
    ),
)
