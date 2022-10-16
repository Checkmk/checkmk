#!/usr/bin/env python3
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# (c) Andreas Doehler <andreas.doehler@bechtle.com/andreas.doehler@gmail.com>
# This is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.
from typing import Any, Dict, Mapping

from .agent_based_api.v1 import register, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult

Section = Dict[str, Any]


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
