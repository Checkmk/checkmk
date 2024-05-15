#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from .agent_based_api.v1 import register, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult

Section = Mapping[str, Any]


def discovery_prism_vm_tools(section: Section) -> DiscoveryResult:
    if section.get("nutanixGuestTools"):
        yield Service()


def check_prism_vm_tools(params: Mapping[str, Any], section: Section) -> CheckResult:
    install_state = params.get("tools_install")
    enabled_state = params.get("tools_enabled")
    data = section.get("nutanixGuestTools")
    if not data:
        return

    tool_install = data["installedVersion"]
    tool_enabled = data["enabled"]

    if tool_install is None and install_state == "installed":
        yield Result(state=State.WARN, summary="No tools installed but should be.")
    elif tool_install is None and install_state == "not_installed":
        yield Result(state=State.OK, summary="No tools installed")
    elif tool_install is not None and install_state == "installed":
        yield Result(state=State.OK, summary="Tools with version %s installed" % tool_install)
    elif install_state == "ignored":
        yield Result(state=State.OK, summary="Tools state are ignored")
    elif tool_install is not None and install_state == "not_installed":
        yield Result(
            state=State.WARN,
            summary="Tools with version %s installed but should not be" % tool_install,
        )

    if tool_enabled and enabled_state == "enabled":
        yield Result(state=State.OK, summary="Tools enabled")
    elif tool_enabled and enabled_state == "disabled":
        message = "Tools enabled, but should be disabled"
        yield Result(state=State.WARN, summary=message)
    elif tool_enabled is None and enabled_state == "enabled":
        message = "No tools enabled, but should be enabled"
        yield Result(state=State.WARN, summary=message)
    elif enabled_state == "ignored":
        yield Result(state=State.OK, summary="Tools enable state ignored")
    else:
        message = "No tools enabled"
        yield Result(state=State.OK, summary=message)


register.check_plugin(
    name="prism_vm_tools",
    service_name="NTNX VMTools",
    sections=["prism_vm"],
    check_default_parameters={
        "tools_install": "installed",
        "tools_enabled": "enabled",
    },
    discovery_function=discovery_prism_vm_tools,
    check_function=check_prism_vm_tools,
    check_ruleset_name="prism_vm_tools",
)
