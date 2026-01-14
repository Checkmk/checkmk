#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import StringTable
from cmk.base.check_legacy_includes.temperature import check_temperature

check_info = {}


def format_nvidia_name(identifier):
    identifier = identifier.replace("Temp", "")
    if identifier == "GPUCore":
        return "GPU NVIDIA"

    # afaik temperature sensors can be GPU or Board, maybe memory
    return "System NVIDIA %s" % identifier


def inventory_nvidia_temp(core, info):
    for line in info:
        line_san = line[0].strip(":")
        if line_san.lower().endswith("temp"):
            if core == (line_san == "GPUCoreTemp"):
                yield format_nvidia_name(line_san), {}


def check_nvidia_temp(item, params, info):
    for line in info:
        if format_nvidia_name(line[0].strip(":")) == item or item == line[0].strip(
            ":"
        ):  # compatibility code for "old discovered" services
            return check_temperature(int(line[1]), params, "nvidia_%s" % item)
    return None


def parse_nvidia(string_table: StringTable) -> StringTable:
    return string_table


check_info["nvidia"] = LegacyCheckDefinition(
    name="nvidia",
    parse_function=parse_nvidia,
)


def discover_nvidia_temp(info):
    return inventory_nvidia_temp(False, info)


check_info["nvidia.temp"] = LegacyCheckDefinition(
    name="nvidia_temp",
    service_name="Temperature %s",
    sections=["nvidia"],
    discovery_function=discover_nvidia_temp,
    check_function=check_nvidia_temp,
    check_ruleset_name="temperature",
    check_default_parameters={"levels": (60.0, 65.0)},
)


def discover_nvidia_temp_core(info):
    return inventory_nvidia_temp(True, info)


check_info["nvidia.temp_core"] = LegacyCheckDefinition(
    name="nvidia_temp_core",
    service_name="Temperature %s",
    sections=["nvidia"],
    discovery_function=discover_nvidia_temp_core,
    check_function=check_nvidia_temp,
    check_ruleset_name="temperature",
    check_default_parameters={"levels": (90.0, 95.0)},
)


def discover_nvidia_errors(info):
    for line in info:
        if line[0] == "GPUErrors:":
            return [(None, None)]
    return []


def check_nvidia_errors(_no_item, _no_params, info):
    for line in info:
        if line[0] == "GPUErrors:":
            errors = int(line[1])
            if errors == 0:
                return (0, "No GPU errors")
            return (2, "%d GPU errors" % errors)
    return (3, "incomplete output from agent")


check_info["nvidia.errors"] = LegacyCheckDefinition(
    name="nvidia_errors",
    service_name="NVIDIA GPU Errors",
    sections=["nvidia"],
    discovery_function=discover_nvidia_errors,
    check_function=check_nvidia_errors,
    check_ruleset_name="hw_errors",
)
