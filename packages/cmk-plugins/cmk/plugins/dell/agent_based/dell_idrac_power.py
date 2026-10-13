#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
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

    @staticmethod
    def mib() -> str:
        return "iDRAC9 or older"

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

    @staticmethod
    def mib() -> str:
        return "iDRAC10 or newer"

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


@dataclass(frozen=True)
class UndefinedRedundancyState:
    # A value the detected MIB version does not define. Naming it in the service output makes a
    # wrong detection visible, instead of letting it fail the whole section.
    value: str
    mib: str

    @property
    def label(self) -> str:
        return f"undefined value {self.value} (assuming the MIB for {self.mib})"

    @property
    def state(self) -> State:
        return State.UNKNOWN


@dataclass
class PowerUnit:
    # Base OID: .1.3.6.1.4.1.674.10892.5.4.600.10.1
    index: str  # .2
    redundancy_state: RedundancyState | UndefinedRedundancyState | None  # .5
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

# RacTypeEnum gives every iDRAC generation a block of 16 values: iDRAC7 starts at 16, iDRAC8 at
# 32, iDRAC9 at 48 and continues at 64 and 80 for the 15th and 16th server generation, iDRAC10
# starts at 96. Below 16 only other(1) and unknown(2) are defined, neither of which names a
# generation.
_RAC_TYPE_IDRAC7 = 16
_RAC_TYPE_IDRAC10 = 96

_SHORT_NAME_PATTERN = re.compile(r"(?i)^idrac(\d+)")


def _select_redundancy_state_type(rac_type: str, short_name: str) -> type[RedundancyState]:
    """
    Get the version-dependent powerUnitRedundancyStatus value scope.

    iDRAC10 introduced v4 of the MIB; all other still-supported generations use v3. racType
    names the generation even on devices whose racShortName does not, so it is asked first.
    """

    def _redundancy_state_from_rac_type() -> type[RedundancyState] | None:
        try:
            value = int(rac_type)
        except ValueError:
            return None
        if value >= _RAC_TYPE_IDRAC10:
            return RedundancyStateV4
        if value >= _RAC_TYPE_IDRAC7:
            return RedundancyStateV3
        return None

    def _redundancy_state_from_short_name() -> type[RedundancyState] | None:
        if (match := _SHORT_NAME_PATTERN.match(short_name)) is None:
            return None
        return RedundancyStateV3 if int(match.group(1)) < 10 else RedundancyStateV4

    return (
        _redundancy_state_from_rac_type()
        or _redundancy_state_from_short_name()
        or RedundancyStateV4
    )


def _parse_power_unit(
    row: Sequence[str], redundancy_state: type[RedundancyState]
) -> PowerUnit | None:
    def _parse_redundancy_status(status: str) -> RedundancyState | UndefinedRedundancyState | None:
        # A column the device does not answer is padded with an empty string. An empty status
        # therefore means the device reported nothing, which is not the same as reporting a
        # value the detected MIB does not define.
        if not status:
            return None
        try:
            return redundancy_state(status)
        except ValueError:
            return UndefinedRedundancyState(value=status, mib=redundancy_state.mib())

    index, redundancy_status, required_for_redundancy = row
    if not index:
        return None
    return PowerUnit(
        index=index,
        redundancy_state=_parse_redundancy_status(redundancy_status),
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
    def _rac_info(column: int) -> str:
        """Read one of the racInfoGroup scalars, which the device may leave unanswered."""
        try:
            return string_table[2][0][column]
        except IndexError:
            return ""

    redundancy_state = _select_redundancy_state_type(
        rac_type=_rac_info(1),
        short_name=_rac_info(0),
    )
    return (
        {
            unit.item: unit
            for row in string_table[0]
            if (unit := _parse_power_unit(row, redundancy_state)) is not None
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
        SNMPTree(
            base=".1.3.6.1.4.1.674.10892.5.1.1",
            oids=[
                "2",  # IDRAC-MIB::racShortName
                "7",  # IDRAC-MIB::racType
            ],
        ),
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
