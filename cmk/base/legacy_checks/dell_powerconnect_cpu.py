#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Relevant SNMP OIDs:
# .1.3.6.1.4.1.89.1.1.0 = INTEGER: 65535
# .1.3.6.1.4.1.89.1.2.0 = INTEGER: none(26)
# .1.3.6.1.4.1.89.1.4.0 = Hex-STRING: E0
# .1.3.6.1.4.1.89.1.5.0 = INTEGER: 1
# .1.3.6.1.4.1.89.1.6.0 = INTEGER: true(1)
# .1.3.6.1.4.1.89.1.7.0 = INTEGER: 91
# .1.3.6.1.4.1.89.1.8.0 = INTEGER: 10
# .1.3.6.1.4.1.89.1.9.0 = INTEGER: 4

# Default values for parameters that can be overriden.


from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import IgnoreResultsError, render

check_info = {}


# Discovery of dell power connect CPU details.
def inventory_dell_powerconnect_cpu(info):
    if info:
        enabled, onesecondperc, _oneminuteperc, _fiveminutesperc = info[0]
        if enabled == "1" and onesecondperc != "" and int(onesecondperc) >= 0:
            yield None, {}


# Check of dell power connect CPU details.
def check_dell_powerconnect_cpu(item, params, info):
    try:
        enabled, onesecondperc, oneminuteperc, fiveminutesperc = map(int, info[0])
    except ValueError:
        raise IgnoreResultsError("Ignoring empty data from SNMP agent")

    if enabled != 1:
        return

    if onesecondperc < 0 or onesecondperc > 100:
        return

    # Darn. It again happend. Someone mixed up load and utilization.
    # We do *not* rename the performance variables here, in order not
    # to mix up existing RRDs...
    yield check_levels(
        onesecondperc,
        "util",
        params["levels"],
        human_readable_func=render.percent,
        infoname="CPU utilization",
        boundaries=(0, 100),
    )
    yield (
        0,
        "",
        [
            ("util1", oneminuteperc, None, None, 0, 100),
            ("util5", fiveminutesperc, None, None, 0, 100),
        ],
    )


check_info["dell_powerconnect_cpu"] = LegacyCheckDefinition(
    name="dell_powerconnect_cpu",
    service_name="CPU utilization",
    discovery_function=inventory_dell_powerconnect_cpu,
    check_function=check_dell_powerconnect_cpu,
    check_default_parameters={"levels": (80.0, 90.0)},
)
