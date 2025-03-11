#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping
from dataclasses import dataclass
from typing import TypeVar

from cmk.agent_based.v2 import CheckResult, contains, Result, State, StringTable

DETECT_AUDIOCODES = contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.5003.8.1.1")

T = TypeVar("T")


def data_by_item(
    section_audiocodes_module_names: Mapping[str, str],
    data_section: Mapping[str, T],
) -> dict[str, T]:
    return {
        f"{name} {index}": data
        for index, data in data_section.items()
        if (name := section_audiocodes_module_names.get(index)) is not None
    }


@dataclass(frozen=True, kw_only=True)
class OPState:
    name: str
    state: State


@dataclass(frozen=True, kw_only=True)
class Presence:
    name: str
    state: State


@dataclass(frozen=True, kw_only=True)
class HAStatus:
    name: str
    state: State


OPERATIONAL_STATE_MAPPING = {
    "0": OPState(name="Invalid state", state=State.CRIT),
    "1": OPState(name="Disabled", state=State.CRIT),
    "2": OPState(name="Enabled", state=State.OK),
}
PRESENCE_MAPPING = {
    "0": Presence(name="Invalid status", state=State.CRIT),
    "1": Presence(name="Module present", state=State.OK),
    "2": Presence(name="Module missing", state=State.CRIT),
}

HA_STATUS_MAPPING = {
    "0": HAStatus(name="Invalid status", state=State.CRIT),
    "1": HAStatus(name="Active - no HA", state=State.WARN),
    "2": HAStatus(name="Active", state=State.OK),
    "3": HAStatus(name="Redundant", state=State.OK),
    "4": HAStatus(name="Stand alone", state=State.OK),
    "5": HAStatus(name="Redundant - no HA", state=State.WARN),
    "6": HAStatus(name="Not applicable", state=State.UNKNOWN),
}


@dataclass(frozen=True, kw_only=True)
class Module:
    op_state: OPState
    presence: Presence
    ha_status: HAStatus


def parse_audiocodes_operational_state(
    string_table: StringTable,
) -> Mapping[str, Module] | None:
    if not string_table:
        return None

    return {
        module[0]: Module(
            op_state=OPERATIONAL_STATE_MAPPING[module[1]],
            presence=PRESENCE_MAPPING[module[2]],
            ha_status=HA_STATUS_MAPPING[module[3]],
        )
        for module in string_table
    }


def check_audiocodes_operational_state(module: Module) -> CheckResult:
    yield Result(
        state=module.op_state.state,
        summary=f"Operational state: {module.op_state.name}",
    )
    yield Result(
        state=module.presence.state,
        notice=f"Presence: {module.presence.name}",
    )
    yield Result(
        state=module.ha_status.state,
        summary=f"HA status: {module.ha_status.name}",
    )


def parse_license_key_list(license_key_list: str) -> str:
    try:
        return bytes.fromhex(license_key_list.replace(" ", "")).decode("utf-8")
    except ValueError:
        return license_key_list
