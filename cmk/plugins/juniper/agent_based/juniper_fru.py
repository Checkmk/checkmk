#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Frus (Field replaceable units) can be
# - power supply
# - fan tray
# - uplink module
# - transceivers

from collections.abc import Mapping

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
)

Section = Mapping[str, Mapping[str, str]]

_MAP_FRU_STATE: Mapping[str, tuple[State, str]] = {
    "1": (State.UNKNOWN, "unknown"),
    "2": (State.CRIT, "empty"),
    "3": (State.WARN, "present"),
    "4": (State.OK, "ready"),
    "5": (State.OK, "announce online"),
    "6": (State.OK, "online"),
    "7": (State.CRIT, "anounce offline"),
    "8": (State.CRIT, "offline"),
    "9": (State.WARN, "diagnostic"),
    "10": (State.WARN, "standby"),
}


def _discover_juniper_fru(section: Section, fru_types: tuple[str, ...]) -> DiscoveryResult:
    for fru_name, fru_data in section.items():
        if fru_data["fru_type"] in fru_types and fru_data["fru_state"] != "2":
            yield Service(item=fru_name)


def discover_juniper_fru(section: Section) -> DiscoveryResult:
    yield from _discover_juniper_fru(section, ("7", "18"))


def discover_juniper_fru_fan(section: Section) -> DiscoveryResult:
    yield from _discover_juniper_fru(section, ("13",))


def check_juniper_fru(item: str, section: Section) -> CheckResult:
    if item in section:
        state, state_readable = _MAP_FRU_STATE[section[item]["fru_state"]]
        yield Result(state=state, summary=f"Operational status: {state_readable}")


check_plugin_juniper_fru = CheckPlugin(
    name="juniper_fru",
    service_name="Power Supply FRU %s",
    discovery_function=discover_juniper_fru,
    check_function=check_juniper_fru,
)

check_plugin_juniper_fru_fan = CheckPlugin(
    name="juniper_fru_fan",
    service_name="Fan FRU %s",
    sections=["juniper_fru"],
    discovery_function=discover_juniper_fru_fan,
    check_function=check_juniper_fru,
)
