#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.plugins.lib.prism import load_json

from .agent_based_api.v1 import register, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable

Section = Mapping[Any, Any]


def parse_prism_remote_support(string_table: StringTable) -> Section:
    return load_json(string_table)


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
