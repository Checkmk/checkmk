#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping
from enum import StrEnum
from typing import assert_never, NamedTuple, Self

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib.hp_proliant import DETECT

type ConditionNumber = str
type ControllerID = str
type StateNumber = str
type RoleNumber = str


class SNMPCondition(StrEnum):
    OTHER = "other"
    OK = "ok"
    DEGRADED = "degraded"
    FAILED = "failed"

    def to_state(self) -> State:
        match self:
            case SNMPCondition.OK:
                return State.OK
            case SNMPCondition.OTHER | SNMPCondition.DEGRADED:
                return State.WARN
            case SNMPCondition.FAILED:
                return State.CRIT
            case _:
                assert_never("Unsupported Enum value")


class SNMPState(StrEnum):
    OTHER = "other"
    OK = "ok"
    GENERAL_FAILURE = "general failure"
    CABLE_PROBLEM = "cable problem"
    POWERED_OFF = "powered off"
    CACHE_MODULE_MISSING = "cache module missing"
    DEGRADED = "degraded"
    ENABLED = "enabled"
    DISABLED = "disabled"
    STANDBY_OFFLINE = "standby (offline)"
    STANDBY_SPARE = "standby (spare)"
    IN_TEST = "in test"
    STARTING = "starting"
    ABSENT = "absent"
    UNAVAILABLE = "unavailable (offline)"
    DEFERRING = "deferring"
    QUISCED = "quisced"
    UPDATING = "updating"
    QUALIFIED = "qualified"

    def to_state(self) -> State:
        match self:
            case (
                SNMPState.OK
                | SNMPState.ENABLED
                | SNMPState.DISABLED
                | SNMPState.STANDBY_SPARE
                | SNMPState.STARTING
                | SNMPState.DEFERRING
                | SNMPState.QUISCED
                | SNMPState.QUALIFIED
            ):
                return State.OK
            case (
                SNMPState.OTHER
                | SNMPState.CACHE_MODULE_MISSING
                | SNMPState.STANDBY_OFFLINE
                | SNMPState.IN_TEST
                | SNMPState.UPDATING
            ):
                return State.WARN
            case (
                SNMPState.GENERAL_FAILURE
                | SNMPState.CABLE_PROBLEM
                | SNMPState.POWERED_OFF
                | SNMPState.DEGRADED
                | SNMPState.ABSENT
                | SNMPState.UNAVAILABLE
            ):
                return State.CRIT
            case _:
                assert_never("Unsupported Enum value")


class Role(StrEnum):
    OTHER = "other"
    NOT_DUPLEXED = "notDuplexed"
    ACTIVE = "active"
    BACKUP = "backup"


class ControllerData(NamedTuple):
    id: ControllerID
    model: str
    slot: str
    cond: SNMPCondition
    role: Role
    b_status: SNMPState
    b_cond: SNMPCondition
    serial: str

    @classmethod
    def from_line(cls, line: list[str]) -> Self | None:
        index, model, slot, cond, role, b_status, b_cond, serial = line

        if "0" in (cond, role, b_status, b_cond):
            return None

        return cls(
            id=index,
            model=model,
            slot=slot,
            cond=PARSER_COND_MAP[cond],
            role=PARSER_ROLE_MAP[role],
            b_status=PARSER_STATE_MAP[b_status],
            b_cond=PARSER_COND_MAP[b_cond],
            serial=serial,
        )


ParsedSection = Mapping[ControllerID, ControllerData | None]


PARSER_COND_MAP: Mapping[ConditionNumber, SNMPCondition] = {
    "1": SNMPCondition.OTHER,
    "2": SNMPCondition.OK,
    "3": SNMPCondition.DEGRADED,
    "4": SNMPCondition.FAILED,
}


PARSER_ROLE_MAP: Mapping[RoleNumber, Role] = {
    "1": Role.OTHER,
    "2": Role.NOT_DUPLEXED,
    "3": Role.ACTIVE,
    "4": Role.BACKUP,
}


PARSER_STATE_MAP: Mapping[StateNumber, SNMPState] = {
    "1": SNMPState.OTHER,
    "2": SNMPState.OK,
    "3": SNMPState.GENERAL_FAILURE,
    "4": SNMPState.CABLE_PROBLEM,
    "5": SNMPState.POWERED_OFF,
    "6": SNMPState.CACHE_MODULE_MISSING,
    "7": SNMPState.DEGRADED,
    "8": SNMPState.ENABLED,
    "9": SNMPState.DISABLED,
    "10": SNMPState.STANDBY_OFFLINE,
    "11": SNMPState.STANDBY_SPARE,
    "12": SNMPState.IN_TEST,
    "13": SNMPState.STARTING,
    "14": SNMPState.ABSENT,
    "16": SNMPState.UNAVAILABLE,
    "17": SNMPState.DEFERRING,
    "18": SNMPState.QUISCED,
    "19": SNMPState.UPDATING,
    "20": SNMPState.QUALIFIED,
}


OTHER_STATE_DESCRIPTION = (
    "The instrument agent does not recognize the status of the controller. "
    "You may need to upgrade the instrument agent."
)


def parse_hp_proliant_da_cntlr(string_table: StringTable) -> ParsedSection:
    return {line[0]: ControllerData.from_line(line) for line in string_table}


def discovery_hp_proliant_da_cntlr(section: ParsedSection) -> DiscoveryResult:
    if section:
        yield from (Service(item=item) for item in section)


def check_hp_proliant_da_cntlr(item: ControllerID, section: ParsedSection) -> CheckResult:
    if not (subsection := section.get(item)):
        yield Result(state=State.UNKNOWN, summary="Controller not found in SNMP data")
        return

    states: Mapping[str, SNMPCondition | SNMPState] = {
        "Condition": subsection.cond,
        "Board-Condition": subsection.b_cond,
        "Board-Status": subsection.b_status,
    }

    yield Result(
        state=State.worst(*(state.to_state() for state in states.values())),
        summary=(
            f"{', '.join(f'{label}: {state}' for label, state in states.items())} "
            f"(Role: {subsection.role}, Model: {subsection.model}, Slot: {subsection.slot}, "
            f"Serial: {subsection.serial})"
        ),
        details=OTHER_STATE_DESCRIPTION
        if SNMPCondition.OTHER in states.values() or SNMPState.OTHER in states.values()
        else None,
    )


snmp_section_hp_proliant_da_cntlr = SimpleSNMPSection(
    name="hp_proliant_da_cntlr",
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.232.3.2.2.1.1",
        oids=["1", "2", "5", "6", "9", "10", "12", "15"],
    ),
    parse_function=parse_hp_proliant_da_cntlr,
)


check_plugin_hp_proliant_da_cntlr = CheckPlugin(
    name="hp_proliant_da_cntlr",
    service_name="HW Controller %s",
    discovery_function=discovery_hp_proliant_da_cntlr,
    check_function=check_hp_proliant_da_cntlr,
)
