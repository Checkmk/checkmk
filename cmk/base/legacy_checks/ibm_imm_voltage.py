#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.lib.ibm import DETECT_IBM_IMM


def inventory_ibm_imm_voltage(info):
    for line in info:
        yield line[0], None


def check_ibm_imm_voltage(item, _no_params, info):
    for line in info:
        if line[0] == item:
            volt, crit, warn, crit_low, warn_low = (float(v) / 1000 for v in line[1:])
            infotext = "%.2f Volt" % volt

            perfdata = [
                ("volt", volt, str(warn_low) + ":" + str(warn), str(crit_low) + ":" + str(crit))
            ]
            levelstext = " (levels warn/crit lower: {:.1f}/{:.1f} upper: {:.1f}/{:.1f})".format(
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


def parse_ibm_imm_voltage(string_table: StringTable) -> StringTable:
    return string_table


check_info["ibm_imm_voltage"] = LegacyCheckDefinition(
    parse_function=parse_ibm_imm_voltage,
    detect=DETECT_IBM_IMM,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2.3.51.3.1.2.2.1",
        oids=["2", "3", "6", "7", "9", "10"],
    ),
    service_name="Voltage %s",
    discovery_function=inventory_ibm_imm_voltage,
    check_function=check_ibm_imm_voltage,
)
