#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
from typing import Any, Mapping

from cmk.base.plugins.agent_based.agent_based_api.v1 import register, Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)

Section = Mapping[str, Any]


def parse_proxmox_ve_vm_info(string_table: StringTable) -> Section:
    return json.loads(string_table[0][0])


def discover_single(section: Section) -> DiscoveryResult:
    yield Service()


def check_proxmox_ve_vm_info(params: Mapping[str, Any], section: Section) -> CheckResult:
    """
    >>> for result in check_proxmox_ve_vm_info(
    ...     {},
    ...     parse_proxmox_ve_vm_info([[
    ...         '{"name": "backup.lan.tribe29.com",'
    ...         ' "node": "pve-muc",'
    ...         ' "status": "running",'
    ...         ' "type": "qemu",'
    ...         ' "vmid": "109"}'
    ...     ]])):
    ...   print(result)
    Result(state=<State.OK: 0>, summary='VM ID: 109')
    Result(state=<State.OK: 0>, summary='Status: running')
    Result(state=<State.OK: 0>, summary='Type: qemu')
    Result(state=<State.OK: 0>, summary='Host: pve-muc')
    """
    vm_status = section.get("status", "n/a").lower()
    req_vm_status = (params.get("required_vm_status") or "").lower()
    yield Result(state=State.OK, summary=f"VM ID: {section.get('vmid')}")
    yield Result(
        state=State.OK if not req_vm_status or vm_status == req_vm_status else State.WARN,
        summary=f"Status: {vm_status}%s" % (req_vm_status and f" (required: {req_vm_status})"),
    )
    yield Result(state=State.OK, summary=f"Type: {section.get('type')}")
    yield Result(state=State.OK, summary=f"Host: {section.get('node')}")


register.agent_section(
    name="proxmox_ve_vm_info",
    parse_function=parse_proxmox_ve_vm_info,
)

register.check_plugin(
    name="proxmox_ve_vm_info",
    service_name="Proxmox VE VM Info",
    discovery_function=discover_single,
    check_function=check_proxmox_ve_vm_info,
    check_ruleset_name="proxmox_ve_vm_info",
    check_default_parameters={
        "required_vm_status": None,
    },
)
