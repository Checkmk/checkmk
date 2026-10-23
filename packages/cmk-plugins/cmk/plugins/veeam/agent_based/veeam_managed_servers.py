#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
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


class ManagedServerType(StrEnum):
    WINDOWS_HOST = "WindowsHost"
    LINUX_HOST = "LinuxHost"
    VI_HOST = "ViHost"
    CLOUD_DIRECTOR_HOST = "CloudDirectorHost"
    HV_SERVER = "HvServer"
    HV_CLUSTER = "HvCluster"
    SCVMM = "SCVMM"
    SMB_V3_CLUSTER = "SmbV3Cluster"
    SMB_V3_STANDALONE_HOST = "SmbV3StandaloneHost"


@dataclass(frozen=True, kw_only=True)
class VeeamManagedServer:
    """Mirrors the VBR REST API's ManagedServerModel
    (GET /api/v1/backupInfrastructure/managedServers).

    The API reference documents `isBackupServer` and `isDefaultMountServer` for
    Microsoft Windows servers only, so they are read as `False` when absent.
    """

    id: str
    type: ManagedServerType | str
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
            type=_parse_type(server_dict["type"]),
            description=server_dict["description"],
            status=server_dict.get("status"),
            is_backup_server=server_dict.get("isBackupServer", False),
            is_default_mount_server=server_dict.get("isDefaultMountServer", False),
        )
    return section


def discovery_veeam_managed_servers(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def _parse_type(raw_type: str) -> ManagedServerType | str:
    try:
        return ManagedServerType(raw_type)
    except ValueError:
        return raw_type


def _known_type_display_name(type_: ManagedServerType) -> str:
    match type_:
        case ManagedServerType.WINDOWS_HOST:
            return "Microsoft Windows"
        case ManagedServerType.LINUX_HOST:
            return "Linux"
        case ManagedServerType.VI_HOST:
            return "VMware vSphere"
        case ManagedServerType.CLOUD_DIRECTOR_HOST:
            return "VMware Cloud Director"
        case ManagedServerType.HV_SERVER:
            return "Hyper-V server"
        case ManagedServerType.HV_CLUSTER:
            return "Hyper-V cluster"
        case ManagedServerType.SCVMM:
            return "SCVMM"
        case ManagedServerType.SMB_V3_CLUSTER:
            return "SMB3 cluster"
        case ManagedServerType.SMB_V3_STANDALONE_HOST:
            return "SMB3 server"


def _type_display_name(type_: ManagedServerType | str) -> str:
    return _known_type_display_name(type_) if isinstance(type_, ManagedServerType) else type_


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
