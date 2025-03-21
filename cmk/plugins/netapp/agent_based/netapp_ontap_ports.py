#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Container, Mapping

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
from cmk.plugins.netapp import models

Section = Mapping[str, models.PortModel]

# <<<netapp_ontap_ports:sep(0)>>>
# {
#     "enabled": true,
#     "name": "a0a",
#     "node": {
#         "_links": {"self": {"href": "/api/cluster/nodes/8f2677e2-bda7-11ed-88df-00a098c54c0b"}},
#         "name": "mcc_darz_a-01",
#         "uuid": "8f2677e2-bda7-11ed-88df-00a098c54c0b",
#     },
#     "speed": 0,
#     "state": "up",
#     "type": "lag",
#     "uuid": "35709f28-bdcd-11ed-88df-00a098c54c0b",
# }
# {
#     "enabled": true,
#     "name": "a0a",
#     "node": {
#         "_links": {"self": {"href": "/api/cluster/nodes/1e13de87-bda2-11ed-b8bd-00a098c50e5b"}},
#         "name": "mcc_darz_a-02",
#         "uuid": "1e13de87-bda2-11ed-b8bd-00a098c50e5b",
#     },
#     "speed": 0,
#     "state": "up",
#     "type": "lag",
#     "uuid": "38784d28-bdcd-11ed-b8bd-00a098c50e5b",
# }


def parse_netapp_ontap_ports(string_table: StringTable) -> Section:
    return {
        port_obj.item_name(): port_obj
        for line in string_table
        for port_obj in [models.PortModel.model_validate_json(line[0])]
    }


agent_section_netapp_ontap_ports = AgentSection(
    name="netapp_ontap_ports",
    parse_function=parse_netapp_ontap_ports,
)


def discover_netapp_ontap_ports(
    params: Mapping[str, Container[str]],
    section: Section,
) -> DiscoveryResult:
    ignored_ports = params["ignored_ports"]

    yield from (
        Service(item=item)
        for item, port in section.items()
        if port.state != "down" and port.port_type not in ignored_ports
    )


def check_netapp_ontap_ports(
    item: str,
    section: Section,
) -> CheckResult:
    """
    Operational state of the port. The state is set to 'down' if the operational state of the port is down.
    The state is set to 'up' if the link state of the port is up and the port is healthy.
    The state is set to 'up' if the link state of the port is up and configured to ignore health status.
    The state is 'degraded' if the link state of the port is up, and the port is not healthy.
    """

    if (port := section.get(item)) is None:
        return

    yield Result(
        state={"up": State.OK, "degraded": State.CRIT, "down": State.UNKNOWN}.get(
            port.state, State.UNKNOWN
        ),
        summary=f"Health status: {({'up': 'healthy', 'down': 'unknown', 'degraded': 'not healthy'}.get(port.state))}",
    )

    yield Result(
        state=State.OK,
        summary=f"Operational speed: {port.speed if port.speed is not None else 'undetermined'}",
    )


check_plugin_netapp_api_svms = CheckPlugin(
    name="netapp_ontap_ports",
    service_name="%s",
    discovery_function=discover_netapp_ontap_ports,
    discovery_ruleset_name="discovery_netapp_api_ports_ignored",
    discovery_default_parameters={"ignored_ports": []},
    check_function=check_netapp_ontap_ports,
)
