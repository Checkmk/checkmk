#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import time
from collections.abc import Mapping, Sequence
from typing import Any, TypedDict

from cmk.agent_based.v2 import (
    any_of,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    OIDCached,
    OIDEnd,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    startswith,
    State,
    StringTable,
)
from cmk.plugins.lib.cpu_util import check_cpu_util
from cmk.plugins.lib.memory import check_element, MemoryLevels
from cmk.plugins.lib.temperature import check_temperature, TempParamType


class DeviceData(TypedDict):
    temp: int
    cpu: int
    mem_total: int
    mem_used: float
    admin: str
    oper: str


Section = Mapping[str, DeviceData]


def parse_hp_hh3c_ext(string_table: Sequence[StringTable]) -> Section:
    entity_info = dict(string_table[1])
    parsed: dict[str, DeviceData] = {}
    for index, admin_state, oper_state, cpu, mem_usage, temperature, mem_size in string_table[0]:
        name = entity_info.get(index, "")

        # mem_size measured in 'bytes' (hh3cEntityExtMemSize)
        # check_element needs values in bytes, not percent
        mem_total = int(mem_size)
        mem_used = 0.01 * int(mem_usage) * mem_total

        parsed.setdefault(
            f"{name} {index}",
            {
                "temp": int(temperature),
                "cpu": int(cpu),
                "mem_total": mem_total,
                "mem_used": mem_used,
                "admin": admin_state,
                "oper": oper_state,
            },
        )
    return parsed


snmp_section_hp_hh3c_ext = SNMPSection(
    name="hp_hh3c_ext",
    detect=any_of(
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.25506.11.1.239"),
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.25506.11.1.189"),
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.25506.11.1.87"),
    ),
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.25506.2.6.1.1.1.1",
            oids=[OIDEnd(), "2", "3", "6", "8", "12", "10"],
        ),
        SNMPTree(
            base=".1.3.6.1.2.1.47.1.1.1.1",
            oids=[OIDEnd(), OIDCached("2")],
        ),
    ],
    parse_function=parse_hp_hh3c_ext,
)


#   .--temperature---------------------------------------------------------.


def discover_hp_hh3c_ext(section: Section) -> DiscoveryResult:
    for name, data in section.items():
        # The invalid value is 65535.
        # We assume: If mem_total <= 0, this module is not installed or
        # does not provide reasonable data or is not a real sensor.
        if data["temp"] != 65535 and data["mem_total"] > 0:
            yield Service(item=name)


def check_hp_hh3c_ext(item: str, params: TempParamType, section: Section) -> CheckResult:
    if (data := section.get(item)) is None:
        return
    yield from check_temperature(
        float(data["temp"]),
        params,
        unique_name=f"hp_hh3c_ext.{item}",
        value_store=get_value_store(),
    )


check_plugin_hp_hh3c_ext = CheckPlugin(
    name="hp_hh3c_ext",
    service_name="Temperature %s",
    discovery_function=discover_hp_hh3c_ext,
    check_function=check_hp_hh3c_ext,
    check_ruleset_name="temperature",
    check_default_parameters={},
)


#   .--states--------------------------------------------------------------.

_ADMIN_STATES: dict[str, tuple[State, str, str]] = {
    "1": (State.WARN, "not_supported", "not supported"),
    "2": (State.OK, "locked", "locked"),
    "3": (State.CRIT, "shutting_down", "shutting down"),
    "4": (State.CRIT, "unlocked", "unlocked"),
}
_OPER_STATES: dict[str, tuple[State, str, str]] = {
    "1": (State.WARN, "not_supported", "not supported"),
    "2": (State.CRIT, "disabled", "disabled"),
    "3": (State.OK, "enabled", "enabled"),
    "4": (State.CRIT, "dangerous", "dangerous"),
}


def discover_hp_hh3c_ext_states(section: Section) -> DiscoveryResult:
    # We assume: if mem_total > 0 then this module is installed and provides reasonable data.
    for name, data in section.items():
        if data["mem_total"] > 0:
            yield Service(item=name)


def check_hp_hh3c_ext_states(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if (data := section.get(item)) is None:
        return

    for label, raw_state, mapping, override_key in (
        ("Administrative", data["admin"], _ADMIN_STATES, "admin"),
        ("Operational", data["oper"], _OPER_STATES, "oper"),
    ):
        state, params_key, state_readable = mapping.get(
            raw_state, (State.UNKNOWN, "unknown", f"unknown[{raw_state}]")
        )
        overrides = params.get(override_key, {})
        if params_key in overrides:
            state = State(overrides[params_key])
        yield Result(state=state, summary=f"{label}: {state_readable}")


check_plugin_hp_hh3c_ext_states = CheckPlugin(
    name="hp_hh3c_ext_states",
    service_name="Status %s",
    sections=["hp_hh3c_ext"],
    discovery_function=discover_hp_hh3c_ext_states,
    check_function=check_hp_hh3c_ext_states,
    check_ruleset_name="hp_hh3c_ext_states",
    check_default_parameters={},
)


#   .--CPU utilization-----------------------------------------------------.


def discover_hp_hh3c_ext_cpu(section: Section) -> DiscoveryResult:
    for name, data in section.items():
        if data["mem_total"] > 0:
            yield Service(item=name)


def check_hp_hh3c_ext_cpu(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if (data := section.get(item)) is None:
        return
    yield from check_cpu_util(
        util=data["cpu"],
        params=params,
        value_store=get_value_store(),
        this_time=time.time(),
    )


check_plugin_hp_hh3c_ext_cpu = CheckPlugin(
    name="hp_hh3c_ext_cpu",
    service_name="CPU utilization %s",
    sections=["hp_hh3c_ext"],
    discovery_function=discover_hp_hh3c_ext_cpu,
    check_function=check_hp_hh3c_ext_cpu,
    check_ruleset_name="cpu_utilization_multiitem",
    check_default_parameters={},
)


#   .--memory--------------------------------------------------------------.


def discover_hp_hh3c_ext_mem(section: Section) -> DiscoveryResult:
    for name, data in section.items():
        if data["mem_total"] > 0:
            yield Service(item=name)


def check_hp_hh3c_ext_mem(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    if (data := section.get(item)) is None:
        return
    levels = params.get("levels")
    if levels is None:
        memory_levels: MemoryLevels | None = None
    elif isinstance(levels[0], int):
        memory_levels = ("abs_used", levels)
    else:
        memory_levels = ("perc_used", levels)
    yield from check_element(
        "Usage",
        data["mem_used"],
        data["mem_total"],
        memory_levels,
        metric_name="memused",
    )


check_plugin_hp_hh3c_ext_mem = CheckPlugin(
    name="hp_hh3c_ext_mem",
    service_name="Memory %s",
    sections=["hp_hh3c_ext"],
    discovery_function=discover_hp_hh3c_ext_mem,
    check_function=check_hp_hh3c_ext_mem,
    check_ruleset_name="memory_multiitem",
    check_default_parameters={
        "levels": (80.0, 90.0),
    },
)
