#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_legacy_includes import dell_compellent

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree
from cmk.plugins.lib.dell import DETECT_DELL_COMPELLENT

check_info = {}

# example output
# .1.3.6.1.4.1.674.11000.2000.500.1.2.14.1.2.1 1
# .1.3.6.1.4.1.674.11000.2000.500.1.2.14.1.2.2 2
# .1.3.6.1.4.1.674.11000.2000.500.1.2.14.1.3.1 1
# .1.3.6.1.4.1.674.11000.2000.500.1.2.14.1.3.2 1
# .1.3.6.1.4.1.674.11000.2000.500.1.2.14.1.5.1 1
# .1.3.6.1.4.1.674.11000.2000.500.1.2.14.1.5.2 1
# .1.3.6.1.4.1.674.11000.2000.500.1.2.14.1.6.1 ""
# .1.3.6.1.4.1.674.11000.2000.500.1.2.14.1.6.2 ""
# .1.3.6.1.4.1.674.11000.2000.500.1.2.14.1.11.1 1
# .1.3.6.1.4.1.674.11000.2000.500.1.2.14.1.11.2 1

dell_compellent_disks_health_map = {
    "1": (0, "healthy"),
    "0": (2, "not healthy"),
}


def parse_dell_compellent_disks(string_table):
    disk_info = string_table[0]
    disk_serials = dict(string_table[1])

    return {
        disk_name_position: [status, health, health_message, enclosure, disk_serials.get(number)]
        for number, status, disk_name_position, health, health_message, enclosure in disk_info
    }


def check_dell_compellent_disks(item, _no_params, parsed):
    if not (data := parsed.get(item)):
        return
    dev_state, health, health_message, enclosure, serial = data
    state, state_readable = dell_compellent.dev_state_map(dev_state)
    yield state, "Status: %s" % state_readable

    yield 0, "Location: Enclosure %s" % enclosure
    if serial is not None:
        yield 0, "Serial number: %s" % serial

    if health_message:
        health_state, health_state_readable = dell_compellent_disks_health_map.get(
            health, (3, "unknown[%s]" % health)
        )
        yield health_state, f"Health: {health_state_readable}, Reason: {health_message}"


def discover_dell_compellent_disks(section):
    yield from ((item, {}) for item in section)


check_info["dell_compellent_disks"] = LegacyCheckDefinition(
    name="dell_compellent_disks",
    detect=DETECT_DELL_COMPELLENT,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.674.11000.2000.500.1.2.14.1",
            oids=["2", "3", "4", "5", "6", "11"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.674.11000.2000.500.1.2.45.1",
            oids=["2", "3"],
        ),
    ],
    parse_function=parse_dell_compellent_disks,
    service_name="Disk %s",
    discovery_function=discover_dell_compellent_disks,
    check_function=check_dell_compellent_disks,
)
