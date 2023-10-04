#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# EES-POWER-MIB::SYSTEMSTATUS.0  .1.3.6.1.4.1.6302.2.1.2.1.0
# OPERATIONAL VALUES:
#                (1) UNKNOWN - STATUS HAS NOT YET BEEN DEFINED
#                (2) NORMAL - THERE ARE NO ACTIVATED ALARMS
#                (3) OBSERVATION - OA, LOWEST LEVEL OF 'ABNORMAL' STATUS
#                (4) WARNING - A3
#                (5) MINOR - MA
#                (6) MAJOR - CA, HIGHEST LEVEL OF 'ABNORMAL' STATUS
#                ADMINISTRATIVE VALUES:
#                (7) UNMANAGED
#                (8) RESTRICTED
#                (9) TESTING
#                (10) DISABLED"
#        SYNTAX INTEGER {
#                UNKNOWN(1),
#                NORMAL(2),
#                OBSERVATION(3),
#                WARNING(4),
#                MINOR(5),
#                MAJOR(6),
#                UNMANAGED(7),
#                RESTRICTED(8),
#                TESTING(9),
#                DISABLED(10) }

# the mib is the NetSure_ESNA.mib, which we have received directly
# from a customer, it is named "Emerson Energy Systems (EES) Power MIB"


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree, startswith

emerson_stat_default = (0, 0)  # warning / critical, unused


def inventory_emerson_stat(info):
    if info:
        return [(None, emerson_stat_default)]
    return []


def check_emerson_stat(item, params, info):
    if info:
        status_text = {
            1: "unknown",
            2: "normal",
            3: "observation",
            4: "warning - A3",
            5: "minor - MA",
            6: "major - CA",
            7: "unmanaged",
            8: "restricted",
            9: "testing",
            10: "disabled",
        }
        status = int(info[0][0])
        infotext = "Status: " + status_text[status]

        state = 0
        if status in [5, 6, 10]:
            state = 2
        elif status in [1, 3, 4, 7, 8, 9]:
            state = 1

        return (state, infotext)

    return (3, "Status not found in SNMP output")


check_info["emerson_stat"] = LegacyCheckDefinition(
    detect=startswith(".1.3.6.1.4.1.6302.2.1.1.1.0", "Emerson Network Power"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.6302.2.1.2.1",
        oids=["0"],
    ),
    service_name="Status",
    discovery_function=inventory_emerson_stat,
    check_function=check_emerson_stat,
)
