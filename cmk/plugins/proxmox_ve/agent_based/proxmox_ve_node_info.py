#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-any-return"
from datetime import datetime
from typing import TypedDict

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    FixedLevelsT,
    NoLevelsT,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.proxmox_ve.lib.node_info import SectionNodeInfo


class Params(TypedDict):
    required_node_status: str
    required_subscription_status: str
    subscription_expiration_days_levels: NoLevelsT | FixedLevelsT[int]


def parse_proxmox_ve_node_info(string_table: StringTable) -> SectionNodeInfo:
    return SectionNodeInfo.model_validate_json(string_table[0][0])


def discover_single(section: SectionNodeInfo) -> DiscoveryResult:
    yield Service()


def _check_days_until_expiration(
    expiration_days_levels: NoLevelsT | FixedLevelsT[int],
    expiration_date_str: str,
    now: datetime,
) -> CheckResult:
    expiration_date = datetime.strptime(expiration_date_str, "%Y-%m-%d")
    delta = (expiration_date - now).days
    yield from check_levels(
        value=delta,
        label="Subscription expiration in",
        render_func=lambda days: f"{int(days)} day{'s' if days != 1 else ''}",
        levels_lower=expiration_days_levels,
        metric_name="days_until_subscription_expiration",
        boundaries=expiration_days_levels[1] if expiration_days_levels[1] else None,
    )


def check_proxmox_ve_node_info(params: Params, section: SectionNodeInfo) -> CheckResult:
    req_node_status = params["required_node_status"].lower()
    yield Result(
        state=State.OK if not req_node_status or req_node_status == section.status else State.WARN,
        summary=f"Status: {section.status}{f' (required: {req_node_status})' if req_node_status else ''}",
    )

    req_subs_status = params["required_subscription_status"].lower()
    yield Result(
        state=State.OK
        if not req_subs_status or req_subs_status == section.subscription.status
        else State.WARN,
        summary=f"Subscription: {section.subscription.status}{f' (required: {req_subs_status})' if req_subs_status else ''}",
    )

    if section.subscription.next_due_date:
        yield from _check_days_until_expiration(
            expiration_days_levels=params["subscription_expiration_days_levels"],
            expiration_date_str=section.subscription.next_due_date,
            now=datetime.now(),
        )

    yield Result(state=State.OK, summary=f"Version: {section.version}")
    yield Result(
        state=State.OK,
        summary=f"Hosted VMs: {len(section.lxc)}x LXC, {len(section.qemu)}x Qemu",
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
        "subscription_expiration_days_levels": ("fixed", (30, 7)),
    },
)
