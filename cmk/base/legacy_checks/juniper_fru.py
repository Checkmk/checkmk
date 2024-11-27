#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Frus (Field replaceable units) can be
# - power supply
# - fan tray
# - uplink module
# - transceivers
#
# .1.3.6.1.4.1.2636.3.1.15.1.5.2.1.1.0 Power Supply: Power Supply 0 @ 0/0/* --> JUNIPER-MIB::jnxFruName.2.1.1.0
# .1.3.6.1.4.1.2636.3.1.15.1.5.2.2.1.0 Power Supply: Power Supply 0 @ 1/0/* --> JUNIPER-MIB::jnxFruName.2.2.1.0
# .1.3.6.1.4.1.2636.3.1.15.1.5.4.1.1.1 FAN: Fan 1 @ 0/0/0 --> JUNIPER-MIB::jnxFruName.4.1.1.1
# .1.3.6.1.4.1.2636.3.1.15.1.5.4.1.1.2 FAN: Fan 2 @ 0/0/1 --> JUNIPER-MIB::jnxFruName.4.1.1.2
# .1.3.6.1.4.1.2636.3.1.15.1.5.4.2.1.1 FAN: Fan 1 @ 1/0/0 --> JUNIPER-MIB::jnxFruName.4.2.1.1
# .1.3.6.1.4.1.2636.3.1.15.1.5.4.2.1.2 FAN: Fan 2 @ 1/0/1 --> JUNIPER-MIB::jnxFruName.4.2.1.2
# .1.3.6.1.4.1.2636.3.1.15.1.5.7.1.0.0 FPC: EX3300 48-Port @ 0/*/* --> JUNIPER-MIB::jnxFruName.7.1.0.0
# .1.3.6.1.4.1.2636.3.1.15.1.5.7.2.0.0 FPC: EX3300 48-Port @ 1/*/* --> JUNIPER-MIB::jnxFruName.7.2.0.0
# .1.3.6.1.4.1.2636.3.1.15.1.5.8.1.1.0 PIC: 48x 10/100/1000 Base-T @ 0/0/* --> JUNIPER-MIB::jnxFruName.8.1.1.0
# .1.3.6.1.4.1.2636.3.1.15.1.5.8.1.2.0 PIC: 4x GE/XE SFP+ @ 0/1/* --> JUNIPER-MIB::jnxFruName.8.1.2.0
# .1.3.6.1.4.1.2636.3.1.15.1.5.8.2.1.0 PIC: 48x 10/100/1000 Base-T @ 1/0/* --> JUNIPER-MIB::jnxFruName.8.2.1.0
# .1.3.6.1.4.1.2636.3.1.15.1.5.8.2.2.0 PIC: 4x GE/XE SFP+ @ 1/1/* --> JUNIPER-MIB::jnxFruName.8.2.2.0
# .1.3.6.1.4.1.2636.3.1.15.1.5.9.1.0.0 Routing Engine 0 --> JUNIPER-MIB::jnxFruName.9.1.0.0
# .1.3.6.1.4.1.2636.3.1.15.1.5.9.2.0.0 Routing Engine 1 --> JUNIPER-MIB::jnxFruName.9.2.0.0
# .1.3.6.1.4.1.2636.3.1.15.1.6.2.1.1.0 7 --> JUNIPER-MIB::jnxFruType.2.1.1.0
# .1.3.6.1.4.1.2636.3.1.15.1.6.2.2.1.0 7 --> JUNIPER-MIB::jnxFruType.2.2.1.0
# .1.3.6.1.4.1.2636.3.1.15.1.6.4.1.1.1 13 --> JUNIPER-MIB::jnxFruType.4.1.1.1
# .1.3.6.1.4.1.2636.3.1.15.1.6.4.1.1.2 13 --> JUNIPER-MIB::jnxFruType.4.1.1.2
# .1.3.6.1.4.1.2636.3.1.15.1.6.4.2.1.1 13 --> JUNIPER-MIB::jnxFruType.4.2.1.1
# .1.3.6.1.4.1.2636.3.1.15.1.6.4.2.1.2 13 --> JUNIPER-MIB::jnxFruType.4.2.1.2
# .1.3.6.1.4.1.2636.3.1.15.1.6.7.1.0.0 3 --> JUNIPER-MIB::jnxFruType.7.1.0.0
# .1.3.6.1.4.1.2636.3.1.15.1.6.7.2.0.0 3 --> JUNIPER-MIB::jnxFruType.7.2.0.0
# .1.3.6.1.4.1.2636.3.1.15.1.6.8.1.1.0 11 --> JUNIPER-MIB::jnxFruType.8.1.1.0
# .1.3.6.1.4.1.2636.3.1.15.1.6.8.1.2.0 11 --> JUNIPER-MIB::jnxFruType.8.1.2.0
# .1.3.6.1.4.1.2636.3.1.15.1.6.8.2.1.0 11 --> JUNIPER-MIB::jnxFruType.8.2.1.0
# .1.3.6.1.4.1.2636.3.1.15.1.6.8.2.2.0 11 --> JUNIPER-MIB::jnxFruType.8.2.2.0
# .1.3.6.1.4.1.2636.3.1.15.1.6.9.1.0.0 6 --> JUNIPER-MIB::jnxFruType.9.1.0.0
# .1.3.6.1.4.1.2636.3.1.15.1.6.9.2.0.0 6 --> JUNIPER-MIB::jnxFruType.9.2.0.0
# .1.3.6.1.4.1.2636.3.1.15.1.8.2.1.1.0 6 --> JUNIPER-MIB::jnxFruState.2.1.1.0
# .1.3.6.1.4.1.2636.3.1.15.1.8.2.2.1.0 6 --> JUNIPER-MIB::jnxFruState.2.2.1.0
# .1.3.6.1.4.1.2636.3.1.15.1.8.4.1.1.1 6 --> JUNIPER-MIB::jnxFruState.4.1.1.1
# .1.3.6.1.4.1.2636.3.1.15.1.8.4.1.1.2 6 --> JUNIPER-MIB::jnxFruState.4.1.1.2
# .1.3.6.1.4.1.2636.3.1.15.1.8.4.2.1.1 6 --> JUNIPER-MIB::jnxFruState.4.2.1.1
# .1.3.6.1.4.1.2636.3.1.15.1.8.4.2.1.2 6 --> JUNIPER-MIB::jnxFruState.4.2.1.2
# .1.3.6.1.4.1.2636.3.1.15.1.8.7.1.0.0 6 --> JUNIPER-MIB::jnxFruState.7.1.0.0
# .1.3.6.1.4.1.2636.3.1.15.1.8.7.2.0.0 6 --> JUNIPER-MIB::jnxFruState.7.2.0.0
# .1.3.6.1.4.1.2636.3.1.15.1.8.8.1.1.0 6 --> JUNIPER-MIB::jnxFruState.8.1.1.0
# .1.3.6.1.4.1.2636.3.1.15.1.8.8.1.2.0 6 --> JUNIPER-MIB::jnxFruState.8.1.2.0
# .1.3.6.1.4.1.2636.3.1.15.1.8.8.2.1.0 6 --> JUNIPER-MIB::jnxFruState.8.2.1.0
# .1.3.6.1.4.1.2636.3.1.15.1.8.8.2.2.0 6 --> JUNIPER-MIB::jnxFruState.8.2.2.0
# .1.3.6.1.4.1.2636.3.1.15.1.8.9.1.0.0 6 --> JUNIPER-MIB::jnxFruState.9.1.0.0
# .1.3.6.1.4.1.2636.3.1.15.1.8.9.2.0.0 6 --> JUNIPER-MIB::jnxFruState.9.2.0.0

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition

check_info = {}


def inventory_juniper_fru(parsed, fru_types):
    return [
        (fru_name, None)
        for fru_name, fru_data in parsed.items()
        if fru_data["fru_type"] in fru_types and fru_data["fru_state"] != "2"
    ]  # ignore "empty" states


_MAP_FRU_STATE = {
    "1": (3, "unknown"),
    "2": (2, "empty"),
    "3": (1, "present"),
    "4": (0, "ready"),
    "5": (0, "announce online"),
    "6": (0, "online"),
    "7": (2, "anounce offline"),
    "8": (2, "offline"),
    "9": (1, "diagnostic"),
    "10": (1, "standby"),
}


def check_juniper_fru(item, _no_params, parsed):
    if item in parsed:
        state, state_readable = _MAP_FRU_STATE[parsed[item]["fru_state"]]
        return state, "Operational status: %s" % state_readable
    return None


def discover_juniper_fru(info):
    return inventory_juniper_fru(info, ("7", "18"))


check_info["juniper_fru"] = LegacyCheckDefinition(
    name="juniper_fru",
    # section already migrated!
    service_name="Power Supply FRU %s",
    discovery_function=discover_juniper_fru,
    check_function=check_juniper_fru,
)


def discover_juniper_fru_fan(info):
    return inventory_juniper_fru(info, ("13",))


# .
#   .--fan-----------------------------------------------------------------.
#   |                            __                                        |
#   |                           / _| __ _ _ __                             |
#   |                          | |_ / _` | '_ \                            |
#   |                          |  _| (_| | | | |                           |
#   |                          |_|  \__,_|_| |_|                           |
#   |                                                                      |
#   '----------------------------------------------------------------------'

check_info["juniper_fru.fan"] = LegacyCheckDefinition(
    name="juniper_fru_fan",
    service_name="Fan FRU %s",
    sections=["juniper_fru"],
    discovery_function=discover_juniper_fru_fan,
    check_function=check_juniper_fru,
)
