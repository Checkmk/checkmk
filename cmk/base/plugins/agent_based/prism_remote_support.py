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
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable

Section = Dict[Any, Any]


def parse_prism_remote_support(string_table: StringTable) -> Section:
    import ast

    parsed = {}
    parsed = ast.literal_eval(string_table[0][0])
    return parsed


register.agent_section(
    name="prism_remote_support",
    parse_function=parse_prism_remote_support,
)


def discovery_prism_remote_support(section: Section) -> DiscoveryResult:
    if section:
        yield Service()


_TUNNEL_STATE: dict[bool, str] = {
    True: "Remote Tunnel is enabled",
    False: "Remote Tunnel is disabled",
}


def check_prism_remote_support(params: Mapping[str, Any], section: Section) -> CheckResult:
    target_state = params.get("tunnel_state")
    active_state = section.get("enable", {"enabled": False}).get("enabled", False)
    message = _TUNNEL_STATE.get(active_state, "No matching Tunnel state found")

    if target_state != active_state:
        yield Result(state=State.WARN, summary=message)
    else:
        yield Result(state=State.OK, summary=message)


register.check_plugin(
    name="prism_remote_support",
    service_name="NTNX Remote Tunnel",
    sections=["prism_remote_support"],
    check_default_parameters={
        "tunnel_state": False,
    },
    discovery_function=discovery_prism_remote_support,
    check_function=check_prism_remote_support,
    check_ruleset_name="prism_remote_support",
)
