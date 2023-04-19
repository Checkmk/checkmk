#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping

from .agent_based_api.v1 import (
    check_levels,
    IgnoreResultsError,
    register,
    render,
    Result,
    Service,
    State,
)
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult
from .utils import esx_vsphere


def discovery_mem_usage(section: esx_vsphere.SectionVM) -> DiscoveryResult:
    if section is None:
        return

    if section.memory is not None:
        yield Service()


def check_mem_usage(params: Mapping[str, Any], section: esx_vsphere.SectionVM) -> CheckResult:
    if section is None:
        raise IgnoreResultsError("No VM information currently available")

    if section.power_state != "poweredOn":
        yield Result(state=State.OK, summary=f"VM is {section.power_state}, skipping this check")
        return

    memory_section = section.memory
    if memory_section is None:
        raise IgnoreResultsError(
            "Hostsystem did not provide memory information (reason may be high load)"
        )

    for metric_name, value in [
        ("host", memory_section.host_usage),
        ("guest", memory_section.guest_usage),
        ("ballooned", memory_section.ballooned),
        ("private", memory_section.private),
        ("shared", memory_section.shared),
    ]:
        yield from check_levels(
            value=value,
            levels_upper=params.get(metric_name),
            metric_name=metric_name,
            render_func=render.bytes,
            label=metric_name.title(),
        )


register.check_plugin(
    name="esx_vsphere_vm_mem_usage",
    sections=["esx_vsphere_vm"],
    service_name="ESX Memory",
    discovery_function=discovery_mem_usage,
    check_function=check_mem_usage,
    check_ruleset_name="esx_vsphere_vm_memory",
    check_default_parameters={},
)
