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


from cmk.base.check_api import LegacyCheckDefinition, saveint
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import contains, IgnoreResultsError, SNMPTree

dell_powerconnect_cpu_default_levels = (80, 90)


# Inventory of dell power connect CPU details.
def inventory_dell_powerconnect_cpu(info):
    if info:
        enabled, onesecondperc, _oneminuteperc, _fiveminutesperc = info[0]
        if enabled == "1" and onesecondperc != "" and int(onesecondperc) >= 0:
            return [(None, dell_powerconnect_cpu_default_levels)]
    return []


# Check of dell power connect CPU details.
def check_dell_powerconnect_cpu(item, params, info):
    try:
        enabled, onesecondperc, oneminuteperc, fiveminutesperc = map(int, info[0])
    except ValueError:
        raise IgnoreResultsError("Ignoring empty data from SNMP agent")
    if int(enabled) == 1:
        cpu_util = saveint(onesecondperc)
        if cpu_util >= 0 <= 100:
            status = 0
            output = ""
            if cpu_util >= params[1]:
                status = 2
                output = " (Above %d%%)" % params[1]
            elif cpu_util >= params[0]:
                status = 1
                output = " (Above %d%%)" % params[0]

            # Darn. It again happend. Someone mixed up load and utilization.
            # We do *not* rename the performance variables here, in order not
            # to mix up existing RRDs...
            return (
                status,
                "CPU utilization is %d%% %s" % (cpu_util, output),
                [
                    ("util", "%d%%" % cpu_util, params[0], params[1], 0, 100),
                    ("util1", "%d%%" % saveint(oneminuteperc), params[0], params[1], 0, 100),
                    ("util5", "%d%%" % saveint(fiveminutesperc), params[0], params[1], 0, 100),
                ],
            )

    return (3, "Invalid  information in SNMP data")


check_info["dell_powerconnect_cpu"] = LegacyCheckDefinition(
    detect=contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.674.10895"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.89.1",
        oids=["6", "7", "8", "9"],
    ),
    service_name="CPU utilization",
    discovery_function=inventory_dell_powerconnect_cpu,
    check_function=check_dell_powerconnect_cpu,
)
