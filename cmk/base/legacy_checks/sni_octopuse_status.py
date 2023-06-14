#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# iso.3.6.1.4.1.231.7.2.9.1.1.0 = INTEGER: 1
# The actual error state of the Octopus E PABX. Contains the highest severity level of the recent error events. This object is updated automatically, but it can also be modified manually.

# { normal(1), warning(2), minor(3), major(4), critical(5) }


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.sni_octopuse import DETECT_SNI_OCTOPUSE


def inventory_octopus_status(info):
    if len(info[0][0]) == 1:
        return [(None, None)]
    return []


def check_octopus_status(_no_item, _no_params_info, info):
    octopus_states_map = {
        1: (0, "normal"),
        2: (1, "warning"),
        3: (1, "minor"),
        4: (2, "major"),
        5: (2, "critical"),
    }

    octopus_state = int(info[0][0][0])
    state = octopus_states_map[octopus_state][0]
    desc = octopus_states_map[octopus_state][1]

    msg = "PBX system state is %s" % desc
    if octopus_state >= 3:
        msg += " error"
    return (state, msg)


check_info["sni_octopuse_status"] = LegacyCheckDefinition(
    detect=DETECT_SNI_OCTOPUSE,
    check_function=check_octopus_status,
    discovery_function=inventory_octopus_status,
    service_name="Global status",
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.231.7.2.9.1.1",
            oids=["0"],
        )
    ],
)
