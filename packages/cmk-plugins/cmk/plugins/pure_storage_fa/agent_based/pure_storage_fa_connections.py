#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from pydantic import BaseModel
from typing import Optional

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


class Connections(BaseModel, frozen=True):
    id: Optional[str] = None
    name: Optional[str] = None
    management_address: Optional[str] = None
    replication_addresses: Optional[list] = None
    status: Optional[str] = None
    type: Optional[str] = None
    replication_transport: Optional[str] = None
    version: Optional[str] = None
    throttle: Optional[dict] = None


def parse_connections(string_table: StringTable) -> list[Connections]:
    json_data = json.loads(string_table[0][0])
    if "items" not in json_data:
        return None
    parsed = []
    for connection in json_data["items"]:
        parsed.append(Connections(**connection))

    return parsed


agent_section_pure_storage_fa_connections = AgentSection(
    name="pure_storage_fa_connections",
    parse_function=parse_connections,
)


def discover_connections(section: list[Connections]) -> DiscoveryResult:
    for connections in section:
        params = {
            "discovered_state": ["connected", connections.status],
            "discovered_throttled": ["False", connections.throttle],
        }
        yield Service(item=connections.name, parameters=dict(params))


def check_connections(item, params, section: list[Connections]) -> CheckResult:
    if section == []:
        yield Result(state=State.CRIT, summary="No Array Connection found")
        return

    for connection in section:
        if item == connection.name:
            if connection.status in params["discovered_state"]:
                if connection.throttle in params["discovered_throttled"]:
                    summary = f"Array {connection.name} is {connection.status}."
                    details = f"Throttled: {connection.throttle}\nVersion: {connection.version}\nManagement Address: {connection.management_address}\nReplication Addresses: {connection.replication_addresses}\nType: {connection.type}"
                    state = State.OK
                else:
                    summary = f"Array {connection.name} is {connection.status}, but throttled."
                    details = f"Version: {connection.version}\nManagement Address: {connection.management_address}\nReplication Addresses: {connection.replication_addresses}\nType: {connection.type}"
                    state = State.WARN
            else:
                summary = (
                    f"Array {connection.name} is {connection.status}, but throttled."
                )
                details = f"Throttled: {connection.throttle}\nVersion: {connection.version}\nManagement Address: {connection.management_address}\nReplication Addresses: {connection.replication_addresses}\nType: {connection.type}"
                state = State.CRIT

            yield Result(state=state, summary=summary, details=details)


check_plugin_pure_storage_fa_connections = CheckPlugin(
    name="pure_storage_fa_connections",
    service_name="Connection to %s",
    discovery_function=discover_connections,
    check_function=check_connections,
    check_ruleset_name="array_connections_default_levels",
    check_default_parameters={},
)
