#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Good docs:
# http://www.cisco.com/en/US/tech/tk648/tk362/technologies_tech_note09186a0080094a91.shtml
# .1.3.6.1.4.1.9.9.106.1.1.1.0 5
# cHsrpGrpTable
###########################
# .1.3.6.1.4.1.9.9.106.1.2.1.1.2.1.192  "HSRP Secret key here"
# .1.3.6.1.4.1.9.9.106.1.2.1.1.2.7.193  "HSRP Secret key here"
# .1.3.6.1.4.1.9.9.106.1.2.1.1.3.1.192  100
# .1.3.6.1.4.1.9.9.106.1.2.1.1.3.7.193  100
# .1.3.6.1.4.1.9.9.106.1.2.1.1.4.1.192  1
# .1.3.6.1.4.1.9.9.106.1.2.1.1.4.7.193  1
# .1.3.6.1.4.1.9.9.106.1.2.1.1.5.1.192  300
# .1.3.6.1.4.1.9.9.106.1.2.1.1.5.7.193  300
# .1.3.6.1.4.1.9.9.106.1.2.1.1.6.1.192  2
# .1.3.6.1.4.1.9.9.106.1.2.1.1.6.7.193  2
# .1.3.6.1.4.1.9.9.106.1.2.1.1.7.1.192  0
# .1.3.6.1.4.1.9.9.106.1.2.1.1.7.7.193  0
# .1.3.6.1.4.1.9.9.106.1.2.1.1.8.1.192  0
# .1.3.6.1.4.1.9.9.106.1.2.1.1.8.7.193  0
# .1.3.6.1.4.1.9.9.106.1.2.1.1.9.1.192  3000
# .1.3.6.1.4.1.9.9.106.1.2.1.1.9.7.193  3000
# .1.3.6.1.4.1.9.9.106.1.2.1.1.10.1.192  10000
# .1.3.6.1.4.1.9.9.106.1.2.1.1.10.7.193  10000
# .1.3.6.1.4.1.9.9.106.1.2.1.1.11.1.192  192.168.10.4
# .1.3.6.1.4.1.9.9.106.1.2.1.1.11.7.193  172.20.10.20 <- hsrp ip
# .1.3.6.1.4.1.9.9.106.1.2.1.1.12.1.192  1
# .1.3.6.1.4.1.9.9.106.1.2.1.1.12.7.193  1
# HSRP Monitored IP interfaces. If any of those go down, the priority of
# the router will be lowered.
# .1.3.6.1.4.1.9.9.106.1.2.1.1.13.1.192  192.168.10.5 <- ip Router 1 int 1
# .1.3.6.1.4.1.9.9.106.1.2.1.1.13.7.193  172.20.10.21 <- ip Router 2 int 7
# .1.3.6.1.4.1.9.9.106.1.2.1.1.14.1.192  192.168.10.6 <- ip Router 1 int 1
# .1.3.6.1.4.1.9.9.106.1.2.1.1.14.7.193  172.20.10.22 <- ip Router 2 int 7
# .1.3.6.1.4.1.9.9.106.1.2.1.1.15.1.192  6     <- group #1 "standby" state
# .1.3.6.1.4.1.9.9.106.1.2.1.1.15.7.193  6     <- group #2 "standby" state
# .1.3.6.1.4.1.9.9.106.1.2.1.1.16.1.192  "00 00 0C 07 AC C0 "
# .1.3.6.1.4.1.9.9.106.1.2.1.1.16.7.193  "00 00 0C 07 AC C1 "
# .1.3.6.1.4.1.9.9.106.1.2.1.1.17.1.192  1
# .1.3.6.1.4.1.9.9.106.1.2.1.1.17.7.193  1

# we'll be alerting if the state is not either 5 or 6.
# We could also not inventorize if the state isn't 5/6 but
# since you have to configure a group, to even show up in the
# MIB it's supposedly ok to alert if something isn't right there.
# otherwise modify the inventory.


from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    all_of,
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    exists,
    OIDEnd,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)

hsrp_states = {1: "initial", 2: "learn", 3: "listen", 4: "speak", 5: "standby", 6: "active"}


def inventory_cisco_hsrp(section: StringTable) -> DiscoveryResult:
    for line in section:
        hsrp_grp_entry, vip, _actrouter, _sbrouter, r_hsrp_state, _vmac = line
        _interface_index, hsrp_grp = hsrp_grp_entry.split(".")
        hsrp_state = int(r_hsrp_state)
        # if the group is in a working state (both routers see and talk to each other),
        # inventorize HSRP group name+IP and the standby state as seen from "this" box.
        if hsrp_state in [5, 6]:
            vip_grp = f"{vip}-{hsrp_grp}"
            yield Service(item=vip_grp, parameters={"group": hsrp_grp, "state": hsrp_state})


def check_cisco_hsrp(item: str, params: Mapping[str, Any], section: StringTable) -> CheckResult:
    _hsrp_grp_wanted, hsrp_state_wanted = params["group"], params["state"]

    for line in section:
        hsrp_grp_entry, vip, _actrouter, _sbrouter, r_hsrp_state, _vmac = line
        _interface_index, hsrp_grp = hsrp_grp_entry.split(".")
        hsrp_state = int(r_hsrp_state)

        if "-" in item:
            vip_grp = f"{vip}-{hsrp_grp}"
        else:
            vip_grp = vip

        if vip_grp == item:
            # FIXME: This should be shorter.
            # Validate that we the inventorized state is a "good one"
            # if it's also the one we have now, then we're fine.

            if hsrp_state_wanted in [3, 5, 6] and hsrp_state == hsrp_state_wanted:
                state = State.OK
                msgtxt = "Redundancy Group %s is OK" % vip_grp
            # otherwise if it's a good one, but flipped, then we are in a failover
            elif hsrp_state in [5, 6]:
                state = State.WARN
                msgtxt = "Redundancy Group %s has failed over" % hsrp_grp
            # anything else must be a non-operative state already
            else:
                state = State.CRIT
                msgtxt = "Redundancy Group %s" % hsrp_grp

            yield Result(
                state=state,
                summary="{}, Status: {}".format(msgtxt, hsrp_states.get(hsrp_state, "unknown")),
            )
            return

    yield Result(state=State.UNKNOWN, summary="HSRP Group not found in Agent output")
    return


def parse_cisco_hsrp(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_cisco_hsrp = SimpleSNMPSection(
    name="cisco_hsrp",
    detect=all_of(contains(".1.3.6.1.2.1.1.1.0", "cisco"), exists(".1.3.6.1.4.1.9.9.106.1.1.1.0")),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9.9.106.1.2.1.1",
        oids=[OIDEnd(), "11", "13", "14", "15", "16"],
    ),
    parse_function=parse_cisco_hsrp,
)
check_plugin_cisco_hsrp = CheckPlugin(
    name="cisco_hsrp",
    service_name="HSRP Group %s",
    discovery_function=inventory_cisco_hsrp,
    check_function=check_cisco_hsrp,
    check_default_parameters={},
)
