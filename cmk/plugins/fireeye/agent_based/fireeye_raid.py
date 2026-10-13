#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import NamedTuple

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.fireeye.lib import DETECT, DISK_STATUS_MAP, HEALTH_MAP, STATUS_MAP

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


class Disk(NamedTuple):
    name: str
    status: str
    health: str


class Section(NamedTuple):
    raid: tuple[str, str] | None
    disks: Sequence[Disk]


def parse_fireeye_raid(string_table: Sequence[StringTable]) -> Section:
    # We only discover in case of a raid system
    if len(string_table[1]) <= 1:
        return Section(raid=None, disks=[])

    status, health = string_table[0][0]
    return Section(
        raid=(status, health),
        disks=[Disk(*line) for line in string_table[1]],
    )


def check_fireeye_raid(section: Section) -> CheckResult:
    if section.raid is None:
        return
    status, health = section.raid
    state, state_readable = STATUS_MAP.get(status.lower(), (2, f"unknown: {status}"))
    yield Result(state=State(state), summary=f"Status: {state_readable}")
    state, state_readable = HEALTH_MAP.get(health, (2, f"unknown: {health}"))
    yield Result(state=State(state), summary=f"Health: {state_readable}")


def discover_fireeye_raid(section: Section) -> DiscoveryResult:
    if section.raid is not None:
        yield Service()


snmp_section_fireeye_raid = SNMPSection(
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
)


check_plugin_fireeye_raid = CheckPlugin(
    name="fireeye_raid",
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


def check_fireeye_raid_disks(item: str, section: Section) -> CheckResult:
    for disk in section.disks:
        if disk.name == item:
            state, state_readable = DISK_STATUS_MAP.get(
                disk.status.lower(), (2, f"unknown: {disk.status}")
            )
            yield Result(state=State(state), summary=f"Disk status: {state_readable}")
            state, state_readable = HEALTH_MAP.get(disk.health, (2, f"unknown: {disk.health}"))
            yield Result(state=State(state), summary=f"Health: {state_readable}")


def discover_fireeye_raid_disks(section: Section) -> DiscoveryResult:
    for disk in section.disks:
        yield Service(item=disk.name)


check_plugin_fireeye_raid_disks = CheckPlugin(
    name="fireeye_raid_disks",
    service_name="Disk status %s",
    sections=["fireeye_raid"],
    discovery_function=discover_fireeye_raid_disks,
    check_function=check_fireeye_raid_disks,
)
