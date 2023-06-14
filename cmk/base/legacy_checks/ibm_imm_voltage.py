#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.ibm import DETECT_IBM_IMM


def inventory_ibm_imm_voltage(info):
    for line in info:
        yield line[0], None


def check_ibm_imm_voltage(item, _no_params, info):
    for line in info:
        if line[0] == item:
            volt, crit, warn, crit_low, warn_low = [float(v) / 1000 for v in line[1:]]
            infotext = "%.2f Volt" % volt

            perfdata = [
                ("volt", volt, str(warn_low) + ":" + str(warn), str(crit_low) + ":" + str(crit))
            ]
            levelstext = " (levels warn/crit lower: %.1f/%.1f upper: %.1f/%.1f)" % (
                warn_low,
                crit_low,
                warn,
                crit,
            )

            if (crit_low and volt <= crit_low) or (crit and volt >= crit):
                state = 2
                infotext += levelstext
            elif (warn_low and volt <= warn_low) or (warn and volt >= warn):
                state = 1
                infotext += levelstext
            else:
                state = 0

            return state, infotext, perfdata
    return None


check_info["ibm_imm_voltage"] = LegacyCheckDefinition(
    detect=DETECT_IBM_IMM,
    check_function=check_ibm_imm_voltage,
    discovery_function=inventory_ibm_imm_voltage,
    service_name="Voltage %s",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2.3.51.3.1.2.2.1",
        oids=["2", "3", "6", "7", "9", "10"],
    ),
)
