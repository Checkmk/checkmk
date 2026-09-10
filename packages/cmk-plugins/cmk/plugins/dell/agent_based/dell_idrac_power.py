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
    index: str  # .2
    redundancy_state: RedundancyState | None  # .5
    required_for_redundancy: int | None  # .6

    @property
    def item(self) -> str:
        return self.index


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
    index: str  # .2
    state: PowerSupplyState | None  # .5
    type: PowerSupplyType | None  # .7
    location_name: str  # .8

    @property
    def item(self) -> str:
        return self.index


SectionUnit = Mapping[str, PowerUnit]
SectionSupply = Mapping[str, PowerSupply]
Section = tuple[SectionUnit, SectionSupply]

_NOT_REPORTED = "Status: not reported by the device"


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


def _parse_power_unit(
    row: Sequence[str], redundancy_state: type[RedundancyState]
) -> PowerUnit | None:
    index, redundancy_status, required_for_redundancy = row
    if not index:
        return None
    return PowerUnit(
        index=index,
        redundancy_state=redundancy_state(redundancy_status) if redundancy_status else None,
        required_for_redundancy=int(required_for_redundancy) if required_for_redundancy else None,
    )


def _parse_power_supply(row: Sequence[str]) -> PowerSupply | None:
    index, status, psu_type, location_name = row
    if not index:
        return None
    return PowerSupply(
        index=index,
        state=PowerSupplyState(status) if status else None,
        type=PowerSupplyType(psu_type) if psu_type else None,
        location_name=location_name,
    )


def parse_dell_idrac_power(string_table: Sequence[StringTable]) -> Section:
    # A column the device does not answer for a row is padded with an empty string, and a row
    # exists as soon as any column answers. An empty value therefore means the device reported
    # nothing, which is not the same as reporting a state the MIB does not define.
    try:
        firmware_shortname = string_table[2][0][0]
    except IndexError:
        firmware_shortname = None
    mib_version = MIBVersion(firmware_shortname=firmware_shortname)
    return (
        {
            unit.item: unit
            for row in string_table[0]
            if (unit := _parse_power_unit(row, mib_version.redundancy_state)) is not None
        },
        {
            supply.item: supply
            for row in string_table[1]
            if (supply := _parse_power_supply(row)) is not None
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

    if power_supply.redundancy_state is None:
        yield Result(state=State.UNKNOWN, summary=_NOT_REPORTED)
    else:
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

    if power_supply.state is None:
        yield Result(state=State.UNKNOWN, summary=_NOT_REPORTED)
    else:
        yield Result(state=power_supply.state.state, summary=f"Status: {power_supply.state.label}")
    if power_supply.type is not None:
        yield Result(state=State.OK, summary=f"Type: {power_supply.type.label}")
    if power_supply.location_name:
        yield Result(state=State.OK, summary=f"Name: {power_supply.location_name}")


check_plugin_dell_idrac_power_unit = CheckPlugin(
    name="dell_idrac_power_unit",
    service_name="Power Supply %s",
    sections=["dell_idrac_power"],
    discovery_function=discover_dell_idrac_power_unit,
    check_function=check_dell_idrac_power_unit,
)
