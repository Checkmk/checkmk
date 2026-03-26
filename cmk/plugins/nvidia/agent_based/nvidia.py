#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.lib.temperature import check_temperature, TempParamType


def _format_nvidia_name(identifier: str) -> str:
    identifier = identifier.replace("Temp", "")
    if identifier == "GPUCore":
        return "GPU NVIDIA"

    # afaik temperature sensors can be GPU or Board, maybe memory
    return f"System NVIDIA {identifier}"


def _discover_nvidia_temp(core: bool, section: StringTable) -> DiscoveryResult:
    for line in section:
        line_san = line[0].strip(":")
        if line_san.lower().endswith("temp"):
            if core == (line_san == "GPUCoreTemp"):
                yield Service(item=_format_nvidia_name(line_san))


def check_nvidia_temp(item: str, params: TempParamType, section: StringTable) -> CheckResult:
    for line in section:
        if _format_nvidia_name(line[0].strip(":")) == item or item == line[0].strip(
            ":"
        ):  # compatibility code for "old discovered" services
            yield from check_temperature(
                int(line[1]),
                params,
                unique_name=f"nvidia_{item}",
                value_store=get_value_store(),
            )


def parse_nvidia(string_table: StringTable) -> StringTable:
    return string_table


agent_section_nvidia = AgentSection(
    name="nvidia",
    parse_function=parse_nvidia,
)


def discover_nvidia_temp(section: StringTable) -> DiscoveryResult:
    yield from _discover_nvidia_temp(False, section)


check_plugin_nvidia_temp = CheckPlugin(
    name="nvidia_temp",
    service_name="Temperature %s",
    sections=["nvidia"],
    discovery_function=discover_nvidia_temp,
    check_function=check_nvidia_temp,
    check_ruleset_name="temperature",
    check_default_parameters={"levels": (60.0, 65.0)},
)


def discover_nvidia_temp_core(section: StringTable) -> DiscoveryResult:
    yield from _discover_nvidia_temp(True, section)


check_plugin_nvidia_temp_core = CheckPlugin(
    name="nvidia_temp_core",
    service_name="Temperature %s",
    sections=["nvidia"],
    discovery_function=discover_nvidia_temp_core,
    check_function=check_nvidia_temp,
    check_ruleset_name="temperature",
    check_default_parameters={"levels": (90.0, 95.0)},
)


def discover_nvidia_errors(section: StringTable) -> DiscoveryResult:
    for line in section:
        if line[0] == "GPUErrors:":
            yield Service()


def check_nvidia_errors(section: StringTable) -> CheckResult:
    for line in section:
        if line[0] == "GPUErrors:":
            errors = int(line[1])
            if errors == 0:
                yield Result(state=State.OK, summary="No GPU errors")
                return
            yield Result(state=State.CRIT, summary=f"{errors} GPU errors")
            return
    yield Result(state=State.UNKNOWN, summary="incomplete output from agent")


check_plugin_nvidia_errors = CheckPlugin(
    name="nvidia_errors",
    service_name="NVIDIA GPU Errors",
    sections=["nvidia"],
    discovery_function=discover_nvidia_errors,
    check_function=check_nvidia_errors,
)
