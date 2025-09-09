#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from dataclasses import dataclass

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
from cmk.plugins.hpe_3par.lib.agent_based import parse_3par


@dataclass
class HPE3ParHost:
    name: str
    id: int | str
    os: str | None
    fc_paths_number: int
    iscsi_paths_number: int


HPE3ParHostsSection = Mapping[str, HPE3ParHost]


def parse_hpe_3par_hosts(string_table: StringTable) -> HPE3ParHostsSection:
    return {
        host.get("name"): HPE3ParHost(
            name=host.get("name"),
            id=host.get("id"),
            os=host.get("descriptors", {}).get("os"),
            fc_paths_number=len(host.get("FCPaths", [])),
            iscsi_paths_number=len(host.get("iSCSIPaths", [])),
        )
        for host in parse_3par(string_table).get("members", {})
        if host.get("name") is not None
    }


agent_section_3par_hosts = AgentSection(
    name="3par_hosts",
    parse_function=parse_hpe_3par_hosts,
)


def discover_hpe_3par_hosts(section: HPE3ParHostsSection) -> DiscoveryResult:
    for host in section:
        yield Service(item=host)


def check_hpe_3par_hosts(
    item: str,
    section: HPE3ParHostsSection,
) -> CheckResult:
    if (host := section.get(item)) is None:
        return

    yield Result(state=State.OK, summary=f"ID: {host.id}")

    if host.os:
        yield Result(state=State.OK, summary=f"OS: {host.os}")

    if host.fc_paths_number:
        yield Result(state=State.OK, summary=f"FC Paths: {host.fc_paths_number}")
    elif host.iscsi_paths_number:
        yield Result(state=State.OK, summary=f"iSCSI Paths: {host.iscsi_paths_number}")


check_plugin_3par_hosts = CheckPlugin(
    name="3par_hosts",
    service_name="Host %s",
    discovery_function=discover_hpe_3par_hosts,
    check_function=check_hpe_3par_hosts,
)
