#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections import Counter
from collections.abc import Sequence
from typing import Literal, TypedDict

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
from cmk.plugins.proxmox_ve.lib.ha_manager_status import (
    LrmNode,
    QuorumItem,
    SectionHaManagerCurrent,
    ServiceItem,
)

STATE_MAP = {
    "started": (State.OK, "OK"),
}

LRM_NODE_STATUS_TO_STATE_MAP = {
    "active": State.OK,
    "idle": State.OK,
    "maintenance mode": State.WARN,
    "maintenance": State.WARN,
}


class Params(TypedDict):
    ignored_vms_state: Literal[0, 1, 2, 3]
    stopped_vms_state: Literal[0, 1, 2, 3]


def parse_proxmox_ve_ha_manager_status(string_table: StringTable) -> SectionHaManagerCurrent:
    return SectionHaManagerCurrent.model_validate_json(string_table[0][0])


agent_section_proxmox_ve_ha_manager_status = AgentSection(
    name="proxmox_ve_ha_manager_status",
    parse_function=parse_proxmox_ve_ha_manager_status,
)


def discover_proxmox_ve_ha_manager_status(section: SectionHaManagerCurrent) -> DiscoveryResult:
    if not section.quorum:
        return

    yield Service(item=section.quorum.id)
    yield from (Service(item=node) for node in section.lrm_nodes)


def check_proxmox_ve_ha_manager_status(
    item: str,
    params: Params,
    section: SectionHaManagerCurrent,
) -> CheckResult:
    if not section.quorum:
        return

    yield from _check_quorum(section.quorum)
    if (node := section.lrm_nodes.get(item)) is None:
        return

    yield from _check_lrm_node(node)

    vms = [svc for svc in node.services.values() if svc.type == "vm"]
    yield from _check_vms(vms, params)


def _check_quorum(quorum: QuorumItem) -> CheckResult:
    if quorum.status != "OK":
        yield Result(state=State.CRIT, summary=f"Quorum status: {quorum.status}")
        return

    yield Result(state=State.OK, summary="Quorum status: OK")


def _check_lrm_node(node: LrmNode) -> CheckResult:
    yield Result(
        state=LRM_NODE_STATUS_TO_STATE_MAP.get(node.readable_status, State.CRIT),
        summary=f'Node "{node.node}" status: {node.readable_status.upper()}',
    )


def _check_vms(vms: Sequence[ServiceItem], params: Params) -> CheckResult:
    counts = Counter(vm.state for vm in vms)
    state_map = {
        "started": State.OK,
        "disabled": State.OK,
        "stopped": State(params["stopped_vms_state"]),
        "ignored": State(params["ignored_vms_state"]),
    }
    for state, count in counts.items():
        yield Result(
            state=state_map.get(state, State.CRIT),
            summary=f"{state.capitalize()}: {count}",
        )


check_plugin_proxmox_ve_ha_manager_status = CheckPlugin(
    name="proxmox_ve_ha_manager_status",
    service_name="Proxmox VE HA Manager Watcher %s",
    discovery_function=discover_proxmox_ve_ha_manager_status,
    check_function=check_proxmox_ve_ha_manager_status,
    check_ruleset_name="proxmox_ve_ha_manager_status",
    check_default_parameters={"ignored_vms_state": 0, "stopped_vms_state": 0},
)
