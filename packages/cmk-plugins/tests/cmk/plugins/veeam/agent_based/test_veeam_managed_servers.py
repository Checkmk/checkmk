#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.veeam.agent_based.veeam_managed_servers import (
    check_veeam_managed_servers,
    CheckParameters,
    discovery_veeam_managed_servers,
    ManagedServerType,
    parse_veeam_managed_servers,
    VeeamManagedServer,
)

PARAMS = CheckParameters(status_available=0, status_unavailable=2)


def _server(name: str = "vcenter01.tech.local", **overrides: object) -> str:
    server_dict: dict[str, object] = {
        "id": "id-1",
        "name": name,
        "description": "Managed server",
        "type": "ViHost",
        "status": "Available",
        "credentialsId": "credentials-id-1",
    }
    server_dict.update(overrides)
    return json.dumps(server_dict)


def _server_without(*keys: str) -> str:
    server_dict = json.loads(_server())
    for key in keys:
        del server_dict[key]
    return json.dumps(server_dict)


def test_discovery_veeam_managed_servers() -> None:
    section = parse_veeam_managed_servers([[_server("server-1")], [_server("server-2")]])
    assert list(discovery_veeam_managed_servers(section)) == [
        Service(item="server-1"),
        Service(item="server-2"),
    ]


def test_parse_veeam_managed_servers() -> None:
    section = parse_veeam_managed_servers(
        [[_server(type="WindowsHost", isBackupServer=True, isDefaultMountServer=True)]]
    )
    assert section == {
        "vcenter01.tech.local": VeeamManagedServer(
            id="id-1",
            type=ManagedServerType.WINDOWS_HOST,
            description="Managed server",
            status="Available",
            is_backup_server=True,
            is_default_mount_server=True,
        )
    }
    assert section["vcenter01.tech.local"].type is ManagedServerType.WINDOWS_HOST


def test_parse_veeam_managed_servers_without_status_or_roles() -> None:
    section = parse_veeam_managed_servers([[_server_without("status")]])
    server = section["vcenter01.tech.local"]
    assert server.status is None
    assert not server.is_backup_server
    assert not server.is_default_mount_server


def test_check_veeam_managed_servers_available_is_ok() -> None:
    section = parse_veeam_managed_servers([[_server()]])
    results = list(check_veeam_managed_servers("vcenter01.tech.local", PARAMS, section))
    assert results[0] == Result(state=State.OK, summary="VMware vSphere, Available")


def test_check_veeam_managed_servers_unavailable_is_crit() -> None:
    section = parse_veeam_managed_servers([[_server(status="Unavailable")]])
    results = list(check_veeam_managed_servers("vcenter01.tech.local", PARAMS, section))
    assert results[0] == Result(state=State.CRIT, summary="VMware vSphere, Unavailable")


def test_check_veeam_managed_servers_unavailable_state_is_configurable() -> None:
    section = parse_veeam_managed_servers([[_server(status="Unavailable")]])
    params = CheckParameters(status_available=0, status_unavailable=1)
    results = list(check_veeam_managed_servers("vcenter01.tech.local", params, section))
    assert results[0] == Result(state=State.WARN, summary="VMware vSphere, Unavailable")


def test_check_veeam_managed_servers_unrecognized_status_is_unknown() -> None:
    section = parse_veeam_managed_servers([[_server(status="Maintenance")]])
    results = list(check_veeam_managed_servers("vcenter01.tech.local", PARAMS, section))
    assert results[0] == Result(state=State.UNKNOWN, summary="VMware vSphere, Maintenance")


def test_check_veeam_managed_servers_missing_status_is_unknown() -> None:
    section = parse_veeam_managed_servers([[_server_without("status")]])
    results = list(check_veeam_managed_servers("vcenter01.tech.local", PARAMS, section))
    assert results[0] == Result(state=State.UNKNOWN, summary="VMware vSphere, no status reported")


def test_check_veeam_managed_servers_type_falls_back_to_raw_value_when_unrecognized() -> None:
    section = parse_veeam_managed_servers([[_server(type="SomeFutureType")]])
    results = list(check_veeam_managed_servers("vcenter01.tech.local", PARAMS, section))
    assert results[0] == Result(state=State.OK, summary="SomeFutureType, Available")


def test_check_veeam_managed_servers_details() -> None:
    section = parse_veeam_managed_servers(
        [[_server(type="WindowsHost", isBackupServer=True, isDefaultMountServer=True)]]
    )
    results = list(check_veeam_managed_servers("vcenter01.tech.local", PARAMS, section))
    assert results[1:] == [
        Result(state=State.OK, notice="Description: Managed server"),
        Result(state=State.OK, notice="Roles: Backup server, Default mount server"),
        Result(state=State.OK, notice="Server ID: id-1"),
    ]


def test_check_veeam_managed_servers_details_without_roles() -> None:
    section = parse_veeam_managed_servers([[_server(description="")]])
    results = list(check_veeam_managed_servers("vcenter01.tech.local", PARAMS, section))
    assert results[1:] == [
        Result(state=State.OK, notice="Description: none"),
        Result(state=State.OK, notice="Server ID: id-1"),
    ]


def test_check_veeam_managed_servers_missing_item_yields_nothing() -> None:
    section = parse_veeam_managed_servers([[_server()]])
    assert not list(check_veeam_managed_servers("gone", PARAMS, section))
