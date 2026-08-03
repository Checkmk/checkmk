#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="var-annotated"

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree
from cmk.plugins.fireeye.lib import DETECT, DISK_STATUS_MAP, HEALTH_MAP, STATUS_MAP

check_info = {}

# .1.3.6.1.4.1.25597.11.2.1.1.0 Good --> FE-FIREEYE-MIB::feRaidStatus.0
# .1.3.6.1.4.1.25597.11.2.1.2.0 1 --> FE-FIREEYE-MIB::feRaidIsHealthy.0
# .1.3.6.1.4.1.25597.11.2.1.3.1.2.1 0
# .1.3.6.1.4.1.25597.11.2.1.3.1.2.2 1
# .1.3.6.1.4.1.25597.11.2.1.3.1.3.1 Online
# .1.3.6.1.4.1.25597.11.2.1.3.1.3.2 Online
# .1.3.6.1.4.1.25597.11.2.1.3.1.4.1 1
# .1.3.6.1.4.1.25597.11.2.1.3.1.4.2 1

#   .--RAID----------------------------------------------------------------.
#   |                      ____      _    ___ ____                         |
#   |                     |  _ \    / \  |_ _|  _ \                        |
#   |                     | |_) |  / _ \  | || | | |                       |
#   |                     |  _ <  / ___ \ | || |_| |                       |
#   |                     |_| \_\/_/   \_\___|____/                        |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                             main check                               |
#   '----------------------------------------------------------------------'


def parse_fireeye_raid(string_table):
    # We only discover in case of a raid system
    parsed = {}
    if len(string_table[1]) > 1:
        for diskname, diskstatus, diskhealth in string_table[1]:
            parsed.setdefault("raid", string_table[0][0])
            parsed.setdefault("disks", [])
            parsed["disks"].append([diskname, diskstatus, diskhealth])

    return parsed


def check_fireeye_raid(_no_item, _no_params, parsed):
    status, health = parsed["raid"]
    state, state_readable = STATUS_MAP.get(status.lower(), (2, f"unknown: {status}"))
    yield state, f"Status: {state_readable}"
    state, state_readable = HEALTH_MAP.get(health, (2, f"unknown: {health}"))
    yield state, f"Health: {state_readable}"


def discover_fireeye_raid(parsed):
    yield from [(None, None)] if parsed.get("raid", []) else []


check_info["fireeye_raid"] = LegacyCheckDefinition(
    name="fireeye_raid",
    detect=DETECT,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.25597.11.2.1",
            oids=["1", "2"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.25597.11.2.1.3.1",
            oids=["2", "3", "4"],
        ),
    ],
    parse_function=parse_fireeye_raid,
    service_name="RAID status",
    discovery_function=discover_fireeye_raid,
    check_function=check_fireeye_raid,
)

# .
#   .--disks---------------------------------------------------------------.
#   |                            _ _     _                                 |
#   |                         __| (_)___| | _____                          |
#   |                        / _` | / __| |/ / __|                         |
#   |                       | (_| | \__ \   <\__ \                         |
#   |                        \__,_|_|___/_|\_\___/                         |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def check_fireeye_raid_disks(item, _no_params, parsed):
    for diskname, diskstatus, diskhealth in parsed["disks"]:
        if diskname == item:
            state, state_readable = DISK_STATUS_MAP.get(
                diskstatus.lower(), (2, f"unknown: {diskstatus}")
            )
            yield state, f"Disk status: {state_readable}"
            state, state_readable = HEALTH_MAP.get(diskhealth, (2, f"unknown: {diskhealth}"))
            yield state, f"Health: {state_readable}"


def discover_fireeye_raid_disks(parsed):
    for line in parsed.get("disks", []):
        yield line[0], None


check_info["fireeye_raid.disks"] = LegacyCheckDefinition(
    name="fireeye_raid_disks",
    service_name="Disk status %s",
    sections=["fireeye_raid"],
    discovery_function=discover_fireeye_raid_disks,
    check_function=check_fireeye_raid_disks,
)
