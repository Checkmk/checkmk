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

LRM_NODE_STATUS_TO_STATE_MAP = {
    "active": State.OK,
    "idle": State.OK,
    "maintenance mode": State.WARN,
    "maintenance": State.WARN,
}


class Params(TypedDict):
    differing_service_state: Literal[0, 1, 2, 3]


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

    if section.master:
        yield Result(
            state=State.OK,
            summary=f'Master node: "{section.master.node}"',
        )

    if (node := section.lrm_nodes.get(item)) is None:
        return

    yield from _check_lrm_node(node)

    services = [svc for svc in node.services.values() if svc.type in ("vm", "ct")]
    yield from _check_services(services, params)


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


def _check_services(services: Sequence[ServiceItem], params: Params) -> CheckResult:
    counts = Counter(service.state for service in services)

    for state, count in counts.items():
        yield Result(
            state=State.OK,
            summary=f"{state.capitalize()}: {count}",
        )

    for service in services:
        if service.request_state and service.state != service.request_state:
            yield Result(
                state=State(params["differing_service_state"]),
                summary=(
                    f'VM/CT "{service.sid}" state "{service.state}" '
                    f'differs from requested state "{service.request_state}"'
                ),
            )


check_plugin_proxmox_ve_ha_manager_status = CheckPlugin(
    name="proxmox_ve_ha_manager_status",
    service_name="Proxmox VE HA Manager Watcher %s",
    discovery_function=discover_proxmox_ve_ha_manager_status,
    check_function=check_proxmox_ve_ha_manager_status,
    check_ruleset_name="proxmox_ve_ha_manager_status",
    check_default_parameters={"differing_service_state": 1},
)
