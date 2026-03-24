#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Self

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
from cmk.plugins.dell.lib import compellent_dev_state_map, DETECT_DELL_COMPELLENT


class Health(StrEnum):
    HEALTHY = "healthy"
    NOT_HEALTHY = "not healthy"
    UNKNOWN = "unknown"

    @classmethod
    def from_value(cls, value: str) -> Self:
        match value:
            case "1":
                return cls.HEALTHY
            case "2":
                return cls.NOT_HEALTHY
            case _:
                return cls.UNKNOWN


@dataclass(frozen=True)
class DiskInfo:
    status: str
    health: Health
    health_message: str
    enclosure: str
    serial: str | None

    @property
    def health_state(self) -> State:
        match self.health:
            case Health.HEALTHY:
                return State.OK
            case Health.NOT_HEALTHY:
                return State.CRIT
            case _:
                return State.UNKNOWN

    @property
    def health_summary(self) -> str:
        msg = f"Health: {self.health}"
        if self.health_message:
            msg += f", Reason: {self.health_message}"
        return msg


Section = Mapping[str, DiskInfo]


def parse_dell_compellent_disks(string_table: Sequence[StringTable]) -> Section:
    disk_info = string_table[0]
    disk_serials = dict(string_table[1])
    parsed: dict[str, DiskInfo] = {}
    for number, status, disk_name_position, health, health_message, enclosure in disk_info:
        health_enum = Health.from_value(health)
        if health_enum is Health.UNKNOWN:
            unknown_health_value = f"unknown health state [{health}]"
            if health_message:
                health_message += f", {unknown_health_value}"
            else:
                health_message = unknown_health_value

        parsed[disk_name_position] = DiskInfo(
            status=status,
            health=health_enum,
            health_message=health_message,
            enclosure=enclosure,
            serial=disk_serials.get(number),
        )
    return parsed


def discover_dell_compellent_disks(section: Section) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)


def check_dell_compellent_disks(item: str, section: Section) -> CheckResult:
    if not (disk := section.get(item)):
        return

    state, state_readable = compellent_dev_state_map(disk.status)
    yield Result(state=state, summary=f"Status: {state_readable}")
    yield Result(state=State.OK, summary=f"Location: Enclosure {disk.enclosure}")

    if disk.serial is not None:
        yield Result(state=State.OK, summary=f"Serial number: {disk.serial}")

    yield Result(state=disk.health_state, summary=disk.health_summary)


snmp_section_dell_compellent_disks = SNMPSection(
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
)

check_plugin_dell_compellent_disks = CheckPlugin(
    name="dell_compellent_disks",
    service_name="Disk %s",
    discovery_function=discover_dell_compellent_disks,
    check_function=check_dell_compellent_disks,
)
