#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

# .1.3.6.1.4.1.231.7.2.9.3.8.1.3.1  "OpenStage 30"
# .1.3.6.1.4.1.231.7.2.9.3.8.1.3.2  "OpenStage 30"
# .1.3.6.1.4.1.231.7.2.9.3.8.1.3.7  "P. O. T."
# .1.3.6.1.4.1.231.7.2.9.3.8.1.3.9  "S0 extension"
# .1.3.6.1.4.1.231.7.2.9.3.8.1.3.11  "S0 trunk: extern"
# .1.3.6.1.4.1.231.7.2.9.3.8.1.3.13  "<not configured>: extern"
# [...]
# .1.3.6.1.4.1.231.7.2.9.3.8.1.4.11  2
# .1.3.6.1.4.1.231.7.2.9.3.8.1.4.13  1


from collections.abc import Sequence

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.sni_octopuse.lib import DETECT_SNI_OCTOPUSE

check_info = {}


def discover_octopus_trunks(info):
    trunkports = ["S0 trunk: extern"]
    inventory = []
    for line in info[0]:
        if len(line) == 4:
            portindex, cardindex, porttype, portstate = line
            portdesc = f"{cardindex}/{portindex}"
            if porttype in trunkports and portstate == "2":
                inventory.append((portdesc, None))
    return inventory


def check_octopus_trunks(item, _no_params, info):
    for line in info[0]:
        portindex, cardindex, porttype, portstate = line
        portdesc = f"{cardindex}/{portindex}"
        if item == portdesc:
            # There are two relevant card states, we use the one from
            # octoPortTable
            if portstate == "1":
                return (2, "Port [%s] is inactive" % porttype)
            return (0, "Port [%s] is active" % porttype)

    return (3, "UNKW - unknown data received from agent")


def parse_sni_octopuse_trunks(string_table: Sequence[StringTable]) -> Sequence[StringTable]:
    return string_table


check_info["sni_octopuse_trunks"] = LegacyCheckDefinition(
    name="sni_octopuse_trunks",
    parse_function=parse_sni_octopuse_trunks,
    detect=DETECT_SNI_OCTOPUSE,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.231.7.2.9.3.8.1",
            oids=["1", "2", "3", "4"],
        )
    ],
    service_name="Trunk Port %s",
    discovery_function=discover_octopus_trunks,
    check_function=check_octopus_trunks,
)
