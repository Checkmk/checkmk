#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TypedDict

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


@dataclass(frozen=True, kw_only=True)
class VeeamManagedServer:
    """Mirrors the VBR REST API's ManagedServerModel
    (GET /api/v1/backupInfrastructure/managedServers).

    The API reference documents `isBackupServer` and `isDefaultMountServer` for
    Microsoft Windows servers only, so they are read as `False` when absent.
    """

    id: str
    type: str
    description: str
    status: str | None
    is_backup_server: bool
    is_default_mount_server: bool


Section = Mapping[str, VeeamManagedServer]


class CheckParameters(TypedDict):
    status_available: int
    status_unavailable: int


def parse_veeam_managed_servers(string_table: StringTable) -> Section:
    section: dict[str, VeeamManagedServer] = {}
    for line in string_table:
        server_dict = json.loads(line[0])
        section[server_dict["name"]] = VeeamManagedServer(
            id=server_dict["id"],
            type=server_dict["type"],
            description=server_dict["description"],
            status=server_dict.get("status"),
            is_backup_server=server_dict.get("isBackupServer", False),
            is_default_mount_server=server_dict.get("isDefaultMountServer", False),
        )
    return section


def discovery_veeam_managed_servers(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def _type_display_name(raw_type: str) -> str:
    match raw_type:
        case "WindowsHost":
            return "Microsoft Windows"
        case "LinuxHost":
            return "Linux"
        case "ViHost":
            return "VMware vSphere"
        case "CloudDirectorHost":
            return "VMware Cloud Director"
        case "HvServer":
            return "Hyper-V server"
        case "HvCluster":
            return "Hyper-V cluster"
        case "SCVMM":
            return "SCVMM"
        case "SmbV3Cluster":
            return "SMB3 cluster"
        case "SmbV3StandaloneHost":
            return "SMB3 server"
        case _:
            return raw_type


def _status_state(status: str | None, params: CheckParameters) -> State:
    # The API reference documents only these two values. Anything else (or a
    # missing status) must not pass as OK, so that it surfaces on the first
    # server that reports it.
    match status:
        case "Available":
            return State(params["status_available"])
        case "Unavailable":
            return State(params["status_unavailable"])
        case _:
            return State.UNKNOWN


def check_veeam_managed_servers(
    item: str, params: CheckParameters, section: Section
) -> CheckResult:
    if (server := section.get(item)) is None:
        return

    yield Result(
        state=_status_state(server.status, params),
        summary=f"{_type_display_name(server.type)}, {server.status or 'no status reported'}",
    )

    yield Result(
        state=State.OK,
        notice=f"Description: {server.description or 'none'}",
    )
    roles = [
        role
        for role, is_set in (
            ("Backup server", server.is_backup_server),
            ("Default mount server", server.is_default_mount_server),
        )
        if is_set
    ]
    if roles:
        yield Result(state=State.OK, notice=f"Roles: {', '.join(roles)}")
    yield Result(state=State.OK, notice=f"Server ID: {server.id}")


agent_section_veeam_managed_servers = AgentSection(
    name="veeam_managed_servers",
    parse_function=parse_veeam_managed_servers,
)

check_plugin_veeam_managed_servers = CheckPlugin(
    name="veeam_managed_servers",
    service_name="Managed server %s",
    discovery_function=discovery_veeam_managed_servers,
    check_function=check_veeam_managed_servers,
    check_ruleset_name="veeam_managed_servers",
    check_default_parameters=CheckParameters(status_available=0, status_unavailable=2),
)
