#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="type-arg"

# Thanks to Andreas Döhler for the contribution.

from typing import NamedTuple, TypedDict

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
from cmk.plugins.hyperv_cluster.lib import hyperv_vm_convert


class Section(NamedTuple):
    assigned_ram: int
    min_ram: int
    max_ram: int
    ram_demand: int
    start_ram: int
    is_dynamic: bool


class CheckParameters(TypedDict):
    max_ram: FixedLevelsT[float] | NoLevelsT
    min_ram: FixedLevelsT[float] | NoLevelsT
    check_demand: bool


def discovery_hyperv_vm_ram(section: Section) -> DiscoveryResult:
    yield Service()


def parse_hyperv_vm_ram(string_table: StringTable) -> Section:
    raw = hyperv_vm_convert(string_table)

    return Section(
        assigned_ram=int(raw["config.hardware.AssignedRAM"]),
        ram_demand=int(raw.get("config.hardware.RAMDemand", "0")),
        start_ram=int(raw.get("config.hardware.StartRAM", "0")),
        max_ram=int(raw.get("config.hardware.MaxRAM", "0")),
        min_ram=int(raw.get("config.hardware.MinRAM", "0")),
        is_dynamic=raw.get("config.hardware.RAMType") == "dynamic",
    )


def check_hyperv_vm_ram(params: CheckParameters, section: Section) -> CheckResult:
    metric_name_prefix = "hyperv_ram_metrics_"

    # Our rules are described in percentage units
    # so we have to convert them to absolute values
    min_ram = params["min_ram"]
    if params["min_ram"][0] == "fixed":
        min_type, (min_warn, min_crit) = params["min_ram"]
        min_warn = min_warn / 100.0 * section.min_ram
        min_crit = min_crit / 100.0 * section.min_ram
        min_ram = (min_type, (min_warn, min_crit))

    max_ram = params["max_ram"]
    if params["max_ram"][0] == "fixed":
        max_type, (max_warn, max_crit) = params["max_ram"]
        max_warn = max_warn / 100.0 * section.max_ram
        max_crit = max_crit / 100.0 * section.max_ram
        max_ram = (max_type, (max_warn, max_crit))

    yield from check_levels(
        section.assigned_ram,
        metric_name=f"{metric_name_prefix}vm_assigned_ram",
        render_func=render.bytes,
        label="Current RAM",
        levels_lower=min_ram,
        levels_upper=max_ram,
    )

    # Demand may be zero for
    # certain guest systems which Hyper-V
    # doesn't integrate with.
    if section.ram_demand > 0:
        state = (
            State.WARN
            if params["check_demand"] and section.ram_demand > section.assigned_ram
            else State.OK
        )
        yield Result(state=state, summary=f"Demand: {render.bytes(section.ram_demand)}")
        yield Metric(
            f"{metric_name_prefix}vm_ram_demand",
            value=section.ram_demand,
        )

    yield from check_levels(
        section.start_ram,
        metric_name=f"{metric_name_prefix}vm_start_ram",
        render_func=render.bytes,
        label="Start RAM",
        notice_only=True,
    )

    yield from check_levels(
        section.max_ram,
        metric_name=f"{metric_name_prefix}vm_max_ram",
        render_func=render.bytes,
        label="Max RAM",
        notice_only=True,
    )

    yield from check_levels(
        section.min_ram,
        metric_name=f"{metric_name_prefix}vm_min_ram",
        render_func=render.bytes,
        label="Min RAM",
        notice_only=True,
    )

    yield Result(state=State.OK, notice=f"Dynamic memory Enabled: {section.is_dynamic}")


agent_section_hyperv_vm_ram = AgentSection(
    name="hyperv_vm_ram",
    parse_function=parse_hyperv_vm_ram,
)

check_plugin_hyperv_vm_ram = CheckPlugin(
    name="hyperv_vm_ram",
    service_name="Hyper-V RAM",
    check_ruleset_name="hyperv_vm_ram",
    discovery_function=discovery_hyperv_vm_ram,
    check_function=check_hyperv_vm_ram,
    check_default_parameters={
        "min_ram": ("no_levels", None),
        "max_ram": ("no_levels", None),
        "check_demand": False,
    },
)
