#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="type-arg"

# Thanks to Andreas Döhler for the contribution.

#!/usr/bin/python
# # -*- encoding: utf-8; py-indent-offset: 4 -*-

from collections.abc import Mapping

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
)
from cmk.plugins.hyperv_cluster.lib import hyperv_vm_convert

Section = Mapping[str, str]


def discovery_hyperv_vm_ram(section: Section) -> DiscoveryResult:
    if "config.hardware.RAMType" in section:
        yield Service()


def get_hardware_ram_param(section: Mapping, key: str, default: str = "missing") -> str:
    return section.get(key, default)


def check_hyperv_vm_ram(section: Section) -> CheckResult:
    message = "RAM information is missing"

    if not section:
        yield Result(state=State.UNKNOWN, summary=message)
        return

    if section.get("config.hardware.RAMType") == "Dynamic Memory":
        message = (
            f"Dynamic Memory configured with "
            f"{get_hardware_ram_param(section, 'config.hardware.MinRAM')} MB minimum and "
            f"{get_hardware_ram_param(section, 'config.hardware.MaxRAM')} MB maximum - start "
            f"{get_hardware_ram_param(section, 'config.hardware.StartRAM')} MB"
        )
    else:
        message = f"Static Memory configured with {get_hardware_ram_param(section, 'config.hardware.RAM')} MB"

    yield Result(state=State.OK, summary=message)


agent_section_hyperv_vm_ram = AgentSection(
    name="hyperv_vm_ram",
    parse_function=hyperv_vm_convert,
)

check_plugin_hyperv_vm_ram = CheckPlugin(
    name="hyperv_vm_ram",
    service_name="HyperV RAM",
    sections=["hyperv_vm_ram"],
    discovery_function=discovery_hyperv_vm_ram,
    check_function=check_hyperv_vm_ram,
)
