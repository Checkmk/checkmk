#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, InitVar
from enum import Enum

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    startswith,
    State,
    StringTable,
)


class RedundancyStateV3(Enum):
    OTHER = "1"
    UNKNOWN = "2"
    FULL = "3"
    DEGRADED = "4"
    LOST = "5"
    NOT_REDUNDANT = "6"
    REDUNDANCY_OFFLINE = "7"

    @property
    def label(self) -> str:
        return self.name.lower().replace("_", " ")

    @property
    def state(self) -> State:
        match self:
            case RedundancyStateV3.OTHER | RedundancyStateV3.UNKNOWN:
                return State.UNKNOWN
            case RedundancyStateV3.FULL | RedundancyStateV3.NOT_REDUNDANT:
                return State.OK
            case RedundancyStateV3.DEGRADED | RedundancyStateV3.REDUNDANCY_OFFLINE:
                return State.WARN
            case _:
                return State.CRIT


class RedundancyStateV4(Enum):
    NOT_REDUNDANT = "0"
    FULL = "1"
    LOST = "2"

    @property
    def label(self) -> str:
        return self.name.lower().replace("_", " ")

    @property
    def state(self) -> State:
        match self:
            case RedundancyStateV4.LOST:
                return State.CRIT
            case _:
                return State.OK


RedundancyState = RedundancyStateV3 | RedundancyStateV4


@dataclass
class PowerUnit:
    # Base OID: .1.3.6.1.4.1.674.10892.5.4.600.10.1
    index: int  # .2
    redundancy_state: RedundancyState  # .5
    required_for_redundancy: int  # .6

    @property
    def item(self) -> str:
        return str(self.index)


class PowerSupplyState(Enum):
    OTHER = "1"
    UNKNOWN = "2"
    OK = "3"
    NON_CRITICAL = "4"
    CRITICAL = "5"
    NON_RECOVERABLE = "6"

    @property
    def label(self) -> str:
        return self.name

    @property
    def state(self) -> State:
        match self:
            case PowerSupplyState.OK:
                return State.OK
            case PowerSupplyState.NON_CRITICAL:
                return State.WARN
            case PowerSupplyState.OTHER | PowerSupplyState.UNKNOWN:
                return State.UNKNOWN
            case _:
                return State.CRIT


class PowerSupplyType(Enum):
    OTHER = "1"
    UNKNOWN = "2"
    LINEAR = "3"
    SWITCHING = "4"
    BATTERY = "5"
    UPS = "6"
    CONVERTER = "7"
    REGULATOR = "8"
    AC = "9"
    DC = "10"
    VRM = "11"

    @property
    def label(self) -> str:
        return self.name


@dataclass
class PowerSupply:
    # Base OID: .1.3.6.1.4.1.674.10892.5.4.600.12.1
    index: int  # .2
    state: PowerSupplyState  # .5
    type: PowerSupplyType  # .7
    location_name: str  # .8

    @property
    def item(self) -> str:
        return str(self.index)


SectionUnit = Mapping[str, PowerUnit]
SectionSupply = Mapping[str, PowerSupply]
Section = tuple[SectionUnit, SectionSupply]


@dataclass
class MIBVersion:
    _FIRMWARE_PATTERN = re.compile(r"(?i)^idrac(\d+)")
    redundancy_state: type[RedundancyState] = field(init=False)
    firmware_shortname: InitVar[str | None] = None

    def __post_init__(self, firmware_shortname: str | None) -> None:
        """
        Get the version dependent powerUnitRedundancyStatus table.

        With iDRAC10 v4 of the MIB was introduced, all other still supported generations use v3.
        """
        if firmware_shortname is None:
            self.redundancy_state = RedundancyStateV4
            return

        match = self._FIRMWARE_PATTERN.match(firmware_shortname)
        if not match:
            self.redundancy_state = RedundancyStateV4
            return

        if int(match.group(1)) < 10:
            self.redundancy_state = RedundancyStateV3
            return

        self.redundancy_state = RedundancyStateV4


def parse_dell_idrac_power(string_table: Sequence[StringTable]) -> Section:
    try:
        firmware_shortname = string_table[2][0][0]
    except IndexError:
        firmware_shortname = None
    mib_version = MIBVersion(firmware_shortname=firmware_shortname)
    return (
        {
            unit.item: unit
            for unit in (
                PowerUnit(
                    index=int(row[0]),
                    redundancy_state=mib_version.redundancy_state(row[1]),
                    required_for_redundancy=int(row[2]),
                )
                for row in string_table[0]
            )
        },
        {
            supply.item: supply
            for supply in (
                PowerSupply(
                    index=int(row[0]),
                    state=PowerSupplyState(row[1]),
                    type=PowerSupplyType(row[2]),
                    location_name=row[3],
                )
                for row in string_table[1]
            )
        },
    )


snmp_section_dell_idrac_power = SNMPSection(
    name="dell_idrac_power",
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.674.10892.5"),
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.674.10892.5.4.600.10.1",
            oids=["2", "5", "6"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.674.10892.5.4.600.12.1",
            oids=["2", "5", "7", "8"],
        ),
        SNMPTree(base=".1.3.6.1.4.1.674.10892.5.1.1", oids=["2"]),
    ],
    parse_function=parse_dell_idrac_power,
)


def discover_dell_idrac_power(section: Section) -> DiscoveryResult:
    for item in section[0]:
        yield Service(item=item)


def check_dell_idrac_power(item: str, section: Section) -> CheckResult:
    power_supply = section[0].get(item)
    if power_supply is None:
        return

    yield Result(
        state=power_supply.redundancy_state.state,
        summary=f"Status: {power_supply.redundancy_state.label}",
    )


check_plugin_dell_idrac_power = CheckPlugin(
    name="dell_idrac_power",
    service_name="Power Supply Redundancy %s",
    discovery_function=discover_dell_idrac_power,
    check_function=check_dell_idrac_power,
)


def discover_dell_idrac_power_unit(section: Section) -> DiscoveryResult:
    for item in section[1]:
        yield Service(item=item)


def check_dell_idrac_power_unit(item: str, section: Section) -> CheckResult:
    power_supply = section[1].get(item)
    if power_supply is None:
        return

    yield Result(state=power_supply.state.state, summary=f"Status: {power_supply.state.label}")
    yield Result(state=State.OK, summary=f"Type: {power_supply.type.label}")
    yield Result(state=State.OK, summary=f"Name: {power_supply.location_name}")


check_plugin_dell_idrac_power_unit = CheckPlugin(
    name="dell_idrac_power_unit",
    service_name="Power Supply %s",
    sections=["dell_idrac_power"],
    discovery_function=discover_dell_idrac_power_unit,
    check_function=check_dell_idrac_power_unit,
)
