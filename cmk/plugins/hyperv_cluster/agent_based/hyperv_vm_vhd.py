#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# Thanks to Andreas Döhler for the contribution.

from collections.abc import Mapping
from enum import StrEnum
from pathlib import PurePath, PureWindowsPath
from typing import Literal, NamedTuple, TypedDict

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    FixedLevelsT,
    Metric,
    NoLevelsT,
    render,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.hyperv_cluster.lib import parse_hyperv


class VhdType(StrEnum):
    DIFFERENCING = "Differencing"
    DYNAMIC = "Dynamic"
    FIXED = "Fixed"


class VhdInfo(NamedTuple):
    main_path: PurePath
    disk_size: int
    file_size: int
    type: VhdType


Section = Mapping[str, VhdInfo]


class CheckParametersDynamic(TypedDict):
    size_limit: tuple[Literal["relative", "absolute"], FixedLevelsT[float] | NoLevelsT]


def discovery_hyperv_vm_vhd_dynamic(section: Section) -> DiscoveryResult:
    for key, info in section.items():
        if info.type in {VhdType.DYNAMIC, VhdType.DIFFERENCING}:
            yield Service(item=key)


def discovery_hyperv_vm_vhd_fixed(section: Section) -> DiscoveryResult:
    for key, info in section.items():
        if info.type == VhdType.FIXED:
            yield Service(item=key)


def parse_hyperv_vm_vhd(string_table: StringTable) -> Section:
    raw = parse_hyperv(string_table)

    return {
        f"{values['vhd.controller.Type']} {values['vhd.controller.Number']} {values['vhd.controller.Location']}": VhdInfo(
            main_path=PureWindowsPath(vhd_path),
            disk_size=int(values["vhd.DiskSize"]),
            file_size=int(values["vhd.FileSize"]),
            type=VhdType(vhd_type),
        )
        for key, values in raw.items()
        if (vhd_path := values.get("vhd.Path")) is not None
        and (vhd_type := values.get("vhd.Type")) is not None
        and vhd_type in VhdType
    }


prefix = "hyperv_vhd_metrics_"


def check_hyperv_vm_vhd_fixed(item: str, section: Section) -> CheckResult:
    if item not in section:
        yield Result(state=State.UNKNOWN, summary=f"No information available for {item}")
        return

    info = section[item]
    yield Result(state=State.OK, summary=f"Disk name: {info.main_path.name}")
    yield from check_levels(
        info.disk_size,
        metric_name=f"{prefix}disk_size",
        label="Maximum disk size",
        render_func=render.bytes,
    )

    yield Result(state=State.OK, summary=f"VHD type: {info.type}")


def check_hyperv_vm_vhd_dynamic(
    item: str, params: CheckParametersDynamic, section: Section
) -> CheckResult:
    if item not in section:
        yield Result(state=State.UNKNOWN, summary=f"No information available for {item}")
        return

    info = section[item]
    yield Result(state=State.OK, summary=f"Disk name: {info.main_path.name}")
    size_percent = info.file_size / info.disk_size * 100

    limit_type, levels = params["size_limit"]
    absolute_levels = levels

    if limit_type == "relative" and levels[0] == "fixed":
        level_type, (warn_level, crit_level) = levels
        warn_level = warn_level / 100.0 * info.disk_size
        crit_level = crit_level / 100.0 * info.disk_size
        absolute_levels = (level_type, (warn_level, crit_level))

    size_results = check_levels(
        info.file_size,
        metric_name=f"{prefix}file_size",
        render_func=render.bytes,
        levels_upper=absolute_levels,
    )

    for result in size_results:
        if isinstance(result, Result):
            yield Result(
                state=result.state,
                summary=f"Current disk size: {render.percent(size_percent)} - {render.bytes(info.file_size)} of {render.bytes(info.disk_size)}",
            )
            continue
        yield result

    yield Result(state=State.OK, summary=f"VHD type: {info.type}")

    yield Metric(
        f"{prefix}file_size_percent",
        size_percent,
        levels=levels[1] if limit_type == "relative" else None,
    )

    yield Metric(
        f"{prefix}disk_size",
        info.disk_size,
    )


agent_section_hyperv_vm_vhd = AgentSection(
    name="hyperv_vm_vhd",
    parse_function=parse_hyperv_vm_vhd,
)

check_plugin_hyperv_vm_vhd_fixed = CheckPlugin(
    name="hyperv_vm_vhd_fixed",
    service_name="Hyper-V VM Disk [%s]",
    sections=["hyperv_vm_vhd"],
    discovery_function=discovery_hyperv_vm_vhd_fixed,
    check_function=check_hyperv_vm_vhd_fixed,
)

check_plugin_hyperv_vm_vhd_dynamic = CheckPlugin(
    name="hyperv_vm_vhd_dynamic",
    service_name="Hyper-V VM Disk [%s]",
    sections=["hyperv_vm_vhd"],
    check_ruleset_name="hyperv_vm_vhd",
    discovery_function=discovery_hyperv_vm_vhd_dynamic,
    check_function=check_hyperv_vm_vhd_dynamic,
    check_default_parameters={"size_limit": ("absolute", ("no_levels", None))},
)
