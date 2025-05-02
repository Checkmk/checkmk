#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
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


def parse_proxmox_ve_node_info(string_table: StringTable) -> Section:
    return json.loads(string_table[0][0])


def discover_single(section: Section) -> DiscoveryResult:
    yield Service()


def check_proxmox_ve_node_info(params: Mapping[str, Any], section: Section) -> CheckResult:
    """
    >>> for result in check_proxmox_ve_node_info(
    ...     {},
    ...     parse_proxmox_ve_node_info([[
    ...         '{'
    ...         '"lxc": ["103", "101", "108", "105", "104"],'
    ...         '"proxmox_ve_version": {"release": "6.2", "repoid": "48bd51b6", "version": "6.2-15"},'
    ...         '"qemu": ["102", "9000", "106", "109"],'
    ...         '"status": "online",'
    ...         '"subscription": {'
    ...         '    "checktime": "1607143921",'
    ...         '    "key": "pve2c-be9cadf297",'
    ...         '    "level": "c",'
    ...         '    "nextduedate": "2021-07-03",'
    ...         '    "productname": "Proxmox VE Community Subscription 2 CPUs/year",'
    ...         '    "regdate": "2020-07-03 00:00:00",'
    ...         '    "status": "Active"}}'
    ...     ]])):
    ...   print(result)
    Result(state=<State.OK: 0>, summary='Status: online')
    Result(state=<State.OK: 0>, summary='Subscription: active')
    Result(state=<State.OK: 0>, summary='Version: 6.2-15')
    Result(state=<State.OK: 0>, summary='Hosted VMs: 5x LXC, 4x Qemu')
    """
    node_status = section.get("status", "n/a").lower()
    subs_status = section.get("subscription", {}).get("status", "n/a").lower()
    proxmox_ve_version = section.get("proxmox_ve_version", {}).get("version", "n/a")
    req_node_status = (params.get("required_node_status") or "").lower()
    req_subs_status = (params.get("required_subscription_status") or "").lower()
    yield Result(
        state=State.OK if not req_node_status or node_status == req_node_status else State.WARN,
        summary=(f"Status: {node_status}{req_node_status and f' (required: {req_node_status})'}"),
    )
    yield Result(
        state=State.OK if not req_subs_status or subs_status == req_subs_status else State.WARN,
        summary=(
            f"Subscription: {subs_status}{req_subs_status and f' (required: {req_subs_status})'}"
        ),
    )
    yield Result(state=State.OK, summary=f"Version: {proxmox_ve_version}")
    yield Result(
        state=State.OK,
        summary=(
            f"Hosted VMs: {len(section.get('lxc', []))}x LXC, {len(section.get('qemu', []))}x Qemu"
        ),
    )


agent_section_proxmox_ve_node_info = AgentSection(
    name="proxmox_ve_node_info",
    parse_function=parse_proxmox_ve_node_info,
)

check_plugin_proxmox_ve_node_info = CheckPlugin(
    name="proxmox_ve_node_info",
    service_name="Proxmox VE Node Info",
    discovery_function=discover_single,
    check_function=check_proxmox_ve_node_info,
    check_ruleset_name="proxmox_ve_node_info",
    check_default_parameters={
        "required_node_status": "online",
        "required_subscription_status": "Active",
    },
)
