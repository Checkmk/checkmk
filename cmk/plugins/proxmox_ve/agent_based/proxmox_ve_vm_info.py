#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
import json
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)

Section = Mapping[str, Any]


def parse_proxmox_ve_vm_info(string_table: StringTable) -> Section:
    return json.loads(string_table[0][0])


def discover_single(section: Section) -> DiscoveryResult:
    yield Service()


def check_proxmox_ve_vm_info(params: Mapping[str, Any], section: Section) -> CheckResult:
    vm_status = section.get("status", "n/a").lower()
    req_vm_status = (params.get("required_vm_status") or "").lower()
    yield Result(state=State.OK, summary=f"VM ID: {section.get('vmid')}")
    yield Result(
        state=State.OK if not req_vm_status or vm_status == req_vm_status else State.WARN,
        summary=f"Status: {vm_status}%s" % (req_vm_status and f" (required: {req_vm_status})"),
    )
    yield Result(state=State.OK, summary=f"Type: {section.get('type')}")
    yield Result(state=State.OK, summary=f"Host: {section.get('node')}")
    td = datetime.timedelta(seconds=section.get("uptime", 0))
    startup_date = datetime.datetime.today() - td
    startup_string = startup_date.strftime("%Y-%m-%d %H:%M:%S")
    if td.days > 365:
        uptime_string = f"Uptime: {td.days % 365} years {td.days // 365} days"
    else:
        uptime_string = f"Uptime: {td.days} days {td.seconds // 3600} hours"
    yield Result(state=State.OK, summary=f"Up since {startup_string}")
    yield Result(state=State.OK, summary=f"{uptime_string}")


agent_section_proxmox_ve_vm_info = AgentSection(
    name="proxmox_ve_vm_info",
    parse_function=parse_proxmox_ve_vm_info,
)

check_plugin_proxmox_ve_vm_info = CheckPlugin(
    name="proxmox_ve_vm_info",
    service_name="Proxmox VE VM Info",
    discovery_function=discover_single,
    check_function=check_proxmox_ve_vm_info,
    check_ruleset_name="proxmox_ve_vm_info",
    check_default_parameters={
        "required_vm_status": "",
    },
)
