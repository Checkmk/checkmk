#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="var-annotated"

from collections.abc import Mapping
from typing import Any, TypedDict

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition, LegacyCheckResult
from cmk.agent_based.v2 import (
    any_of,
    DiscoveryResult,
    OIDCached,
    OIDEnd,
    Service,
    SNMPTree,
    startswith,
    StringTable,
)
from cmk.base.check_legacy_includes.cpu_util import check_cpu_util
from cmk.base.check_legacy_includes.mem import check_memory_element
from cmk.base.check_legacy_includes.temperature import check_temperature


class DeviceData(TypedDict):
    temp: int
    cpu: int
    mem_total: int
    mem_used: float
    admin: str
    oper: str


check_info = {}


def parse_hp_hh3c_ext(string_table: list[StringTable]) -> Mapping[str, DeviceData]:
    entity_info = dict(string_table[1])
    parsed: dict[str, DeviceData] = {}
    for index, admin_state, oper_state, cpu, mem_usage, temperature, mem_size in string_table[0]:
        name = entity_info.get(index, (None, None))

        # mem_size measured in 'bytes' (hh3cEntityExtMemSize)
        # check_memory_elements needs values in bytes, not percent
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


#   .--temperature---------------------------------------------------------.
#   |      _                                      _                        |
#   |     | |_ ___ _ __ ___  _ __   ___ _ __ __ _| |_ _   _ _ __ ___       |
#   |     | __/ _ \ '_ ` _ \| '_ \ / _ \ '__/ _` | __| | | | '__/ _ \      |
#   |     | ||  __/ | | | | | |_) |  __/ | | (_| | |_| |_| | | |  __/      |
#   |      \__\___|_| |_| |_| .__/ \___|_|  \__,_|\__|\__,_|_|  \___|      |
#   |                       |_|                                            |
#   '----------------------------------------------------------------------'


def discover_hp_hh3c_ext(parsed: Mapping[str, DeviceData]) -> DiscoveryResult:
    for k, v in parsed.items():
        # The invalid value is 65535.
        # We assume: If mem_total <= 0, this module is not installed or
        # does not provide reasonable data or is not a real sensor.
        if v["temp"] != 65535 and v["mem_total"] > 0:
            yield Service(item=k)


def check_hp_hh3c_ext(
    item: str, params: Any, parsed: Mapping[str, DeviceData]
) -> LegacyCheckResult:
    if item not in parsed:
        return
    yield check_temperature(float(parsed[item]["temp"]), params, "hp_hh3c_ext.%s" % item)


check_info["hp_hh3c_ext"] = LegacyCheckDefinition(
    name="hp_hh3c_ext",
    detect=any_of(
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.25506.11.1.239"),
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
    service_name="Temperature %s",
    discovery_function=discover_hp_hh3c_ext,
    check_function=check_hp_hh3c_ext,
    check_ruleset_name="temperature",
)

# .
#   .--states--------------------------------------------------------------.
#   |                          _        _                                  |
#   |                      ___| |_ __ _| |_ ___  ___                       |
#   |                     / __| __/ _` | __/ _ \/ __|                      |
#   |                     \__ \ || (_| | ||  __/\__ \                      |
#   |                     |___/\__\__,_|\__\___||___/                      |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_hp_hh3c_ext_states(parsed: Mapping[str, DeviceData]) -> DiscoveryResult:
    for k, v in parsed.items():
        if v["mem_total"] > 0:
            # We assume: if mem_total > 0 then
            # this module is installed and provides
            # reasonable data.
            yield Service(item=k)


def check_hp_hh3c_ext_states(
    item: str, params: Any, parsed: Mapping[str, DeviceData]
) -> LegacyCheckResult:
    if item not in parsed:
        return

    map_admin_states = {
        "1": (1, "not_supported", "not supported"),
        "2": (0, "locked", "locked"),
        "3": (2, "shutting_down", "shutting down"),
        "4": (2, "unlocked", "unlocked"),
    }
    map_oper_states = {
        "1": (1, "not_supported", "not supported"),
        "2": (2, "disabled", "disabled"),
        "3": (0, "enabled", "enabled"),
        "4": (2, "dangerous", "dangerous"),
    }

    attrs = parsed[item]

    # Check admin state
    dev_state = attrs["admin"]
    state, params_key, state_readable = map_admin_states.get(
        dev_state, (3, "unknown", "unknown[%s]" % dev_state)
    )
    params_admin = params.get("admin", {})
    if params_key in params_admin:
        state = params_admin[params_key]
    yield state, f"Administrative: {state_readable}"

    # Check operational state
    dev_state = attrs["oper"]
    state, params_key, state_readable = map_oper_states.get(
        dev_state, (3, "unknown", "unknown[%s]" % dev_state)
    )
    params_oper = params.get("oper", {})
    if params_key in params_oper:
        state = params_oper[params_key]
    yield state, f"Operational: {state_readable}"


check_info["hp_hh3c_ext.states"] = LegacyCheckDefinition(
    name="hp_hh3c_ext_states",
    service_name="Status %s",
    sections=["hp_hh3c_ext"],
    discovery_function=discover_hp_hh3c_ext_states,
    check_function=check_hp_hh3c_ext_states,
    check_ruleset_name="hp_hh3c_ext_states",
)

# .
#   .--CPU utilization-----------------------------------------------------.
#   |    ____ ____  _   _         _   _ _ _          _   _                 |
#   |   / ___|  _ \| | | |  _   _| |_(_) (_)______ _| |_(_) ___  _ __      |
#   |  | |   | |_) | | | | | | | | __| | | |_  / _` | __| |/ _ \| '_ \     |
#   |  | |___|  __/| |_| | | |_| | |_| | | |/ / (_| | |_| | (_) | | | |    |
#   |   \____|_|    \___/   \__,_|\__|_|_|_/___\__,_|\__|_|\___/|_| |_|    |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_hp_hh3c_ext_cpu(parsed: Mapping[str, DeviceData]) -> DiscoveryResult:
    for k, v in parsed.items():
        if v["mem_total"] > 0:
            # We assume: if mem_total > 0 then
            # this module is installed and provides
            # reasonable data.
            yield Service(item=k)


def check_hp_hh3c_ext_cpu(
    item: str, params: Any, parsed: Mapping[str, DeviceData]
) -> LegacyCheckResult:
    if item not in parsed:
        return
    yield from check_cpu_util(parsed[item]["cpu"], params)


check_info["hp_hh3c_ext.cpu"] = LegacyCheckDefinition(
    name="hp_hh3c_ext_cpu",
    service_name="CPU utilization %s",
    sections=["hp_hh3c_ext"],
    discovery_function=discover_hp_hh3c_ext_cpu,
    check_function=check_hp_hh3c_ext_cpu,
    check_ruleset_name="cpu_utilization_multiitem",
)

# .
#   .--memory--------------------------------------------------------------.
#   |                                                                      |
#   |              _ __ ___   ___ _ __ ___   ___  _ __ _   _               |
#   |             | '_ ` _ \ / _ \ '_ ` _ \ / _ \| '__| | | |              |
#   |             | | | | | |  __/ | | | | | (_) | |  | |_| |              |
#   |             |_| |_| |_|\___|_| |_| |_|\___/|_|   \__, |              |
#   |                                                  |___/               |
#   '----------------------------------------------------------------------'


def discover_hp_hh3c_ext_mem(parsed: Mapping[str, DeviceData]) -> DiscoveryResult:
    for name, attrs in parsed.items():
        if attrs["mem_total"] > 0:
            # We assume: if mem_total > 0 then
            # this module is installed and provides
            # reasonable data.
            yield Service(item=name)


def check_hp_hh3c_ext_mem(
    item: str, params: Any, parsed: Mapping[str, DeviceData]
) -> LegacyCheckResult:
    if not (data := parsed.get(item)):
        return
    levels = params.get("levels")
    yield check_memory_element(
        "Usage",
        data["mem_used"],
        data["mem_total"],
        (
            "abs_used" if isinstance(levels, tuple) and isinstance(levels[0], int) else "perc_used",
            levels,
        ),
        metric_name="memused",
    )


check_info["hp_hh3c_ext.mem"] = LegacyCheckDefinition(
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
