#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# iso.3.6.1.4.1.231.7.2.9.1.1.0 = INTEGER: 1
# The actual error state of the Octopus E PABX. Contains the highest severity level of the recent error events. This object is updated automatically, but it can also be modified manually.

# { normal(1), warning(2), minor(3), major(4), critical(5) }


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import DiscoveryResult, Service, SNMPTree, StringTable
from cmk.plugins.lib.sni_octopuse import DETECT_SNI_OCTOPUSE

check_info = {}


def discover_octopus_status(section: StringTable) -> DiscoveryResult:
    if len(section[0]) == 1:
        yield Service()


def check_octopus_status(_no_item, _no_params_info, info):
    octopus_states_map = {
        1: (0, "normal"),
        2: (1, "warning"),
        3: (1, "minor"),
        4: (2, "major"),
        5: (2, "critical"),
    }

    octopus_state = int(info[0][0])
    state = octopus_states_map[octopus_state][0]
    desc = octopus_states_map[octopus_state][1]

    msg = "PBX system state is %s" % desc
    if octopus_state >= 3:
        msg += " error"
    return (state, msg)


def parse_sni_octopuse_status(string_table: StringTable) -> StringTable | None:
    return string_table or None


check_info["sni_octopuse_status"] = LegacyCheckDefinition(
    name="sni_octopuse_status",
    parse_function=parse_sni_octopuse_status,
    detect=DETECT_SNI_OCTOPUSE,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.231.7.2.9.1.1",
        oids=["0"],
    ),
    service_name="Global status",
    discovery_function=discover_octopus_status,
    check_function=check_octopus_status,
)
