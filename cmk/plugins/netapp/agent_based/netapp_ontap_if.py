#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping, MutableMapping, Sequence
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Result,
    RuleSetType,
    State,
    StringTable,
)
from cmk.plugins.lib import interfaces
from cmk.plugins.lib.netapp_api import (
    check_netapp_interfaces,
    IfSection,
    MACList,
    merge_if_sections,
)
from cmk.plugins.netapp import models
from cmk.plugins.netapp.agent_based.netapp_ontap_ports import Section as PortsSection

InterfacesSection = Mapping[str, models.IpInterfaceModel]
InterfacesCountersSection = Mapping[str, models.InterfaceCounters]


def parse_netapp_interfaces(string_table: StringTable) -> InterfacesSection:
    return {
        interface_obj.name: interface_obj
        for line in string_table
        for interface_obj in [models.IpInterfaceModel.model_validate_json(line[0])]
    }


agent_section_netapp_interfaces = AgentSection(
    name="netapp_ontap_if",
    parse_function=parse_netapp_interfaces,
)


def parse_netapp_interfaces_counters(
    string_table: StringTable,
) -> InterfacesCountersSection:
    return {
        counter_obj.id: counter_obj
        for line in string_table
        for counter_obj in [models.InterfaceCounters.model_validate_json(line[0])]
    }


agent_section_netapp_interfacescounters = AgentSection(
    name="netapp_ontap_if_counters",
    parse_function=parse_netapp_interfaces_counters,
)


def _get_failover_home_port(
    ports_section: PortsSection, interface: Mapping[str, Any]
) -> str | None:
    # compute eventual failover port in case of home_port_only failover policy
    for port in ports_section.values():
        if interface["home-port"] == port.name and interface["home-node"] == port.node_name:
            return f"{port.node_name}|{port.name}|{port.state}"

    return None


def _merge_interface_port(ports_section: PortsSection, interface: dict[str, Any]) -> dict:
    for port in ports_section.values():
        if interface["port_name"] == port.name and interface["node_name"] == port.node_name:
            port_data = port.serialize()

            return interface | port_data

    return interface


def _merge_interface_counters(
    counters: models.InterfaceCounters | None, interface: dict[str, Any]
) -> dict:
    if counters:
        return interface | counters.model_dump()
    return interface


def _merge_if_counters_sections(
    section_netapp_ontap_if: InterfacesSection,
    section_netapp_ontap_ports: PortsSection,
    section_netapp_ontap_if_counters: InterfacesCountersSection | None,
) -> tuple[IfSection, str | None]:
    """
    1 interface -> 1 port

    Failover rules as per my understanding:
    - if failover (policy) is 'default' or 'broadcast_domain_only' in case of port failure
      the failover ports are the ports of the broadcast_domain of the failing port
    - if failover (policy) is 'home_node_only' in case of port failure
      the failover ports are the port(s) of the broadcast_domain which are on the home node
    - if failover (policy) is 'home_port_only' in case of port failure
      the failover ports is the home_port
    Cfr: https://docs.netapp.com/us-en/ontap-restmap-9131//net.html#net-port-broadcast-domain-get

    """

    if_mac_list: dict[str, MACList] = {}
    virtual_interfaces = []

    # collect broadcast ports for broadcast_domain and node
    broadcast_domains_ports: MutableMapping[str, set[str]] = {}
    node_ports: MutableMapping[str, set[str]] = {}
    for port in section_netapp_ontap_ports.values():
        if not port.broadcast_domain:
            continue
        broadcast_domains_ports.setdefault(port.broadcast_domain, set()).add(
            f"{port.node_name}|{port.name}|{port.state}"
        )
        node_ports.setdefault(port.node_name, set()).add(
            f"{port.node_name}|{port.name}|{port.state}"
        )

    if section_netapp_ontap_if_counters:
        # map nodename:interfacename -> counter_id
        interface_to_counter = {
            key[: key.rfind(":")]: key for key in section_netapp_ontap_if_counters.keys()
        }

    interfaces_data_section = {key: val.serialize() for key, val in section_netapp_ontap_if.items()}

    for interface_name, interface in interfaces_data_section.items():
        failover_home_port = _get_failover_home_port(section_netapp_ontap_ports, interface)
        interface = _merge_interface_port(section_netapp_ontap_ports, interface)

        if section_netapp_ontap_if_counters:
            counters = section_netapp_ontap_if_counters.get(
                interface_to_counter.get(f"{interface['node_name']}:{interface['name']}", "")
            )
            interface = _merge_interface_counters(counters, interface)

        # update the section with merged info
        interfaces_data_section[interface_name] = interface

        computed_state = None
        if port_state := interface.get("port_state"):
            computed_state = "1" if port_state == "up" else "2"
        elif interface_state := interface.get("interface_state"):
            computed_state = "1" if interface_state == "up" else "2"

        # ! if the port type is not physical, than is virtual?!?!?!?
        if interface.get("port_type") != "physical":
            virtual_interfaces.append(interface_name)

        computed_speed = 0
        if interface.get("port_speed"):
            computed_speed = interface["port_speed"] * 1000 * 1000

        interface["state"] = computed_state
        interface["speed"] = computed_speed

        if interface.get("mac-address"):
            if_mac_list.setdefault(interface["mac-address"], [])
            if_mac_list[interface["mac-address"]].append((interface_name, computed_state))

        failover_policy_alert = None
        failover_policy = interface.get("failover")
        fail_ports: set = broadcast_domains_ports.get(interface.get("broadcast_domain", ""), set())
        match failover_policy:
            case "default" | "broadcast_domain_only":
                interface["failover_ports"] = ";".join(el for el in fail_ports)
            case "home_node_only":
                interface["failover_ports"] = ";".join(
                    el for el in fail_ports if el.split("|")[0] == interface["home-node"]
                )
            case "home_port_only":
                interface["failover_ports"] = failover_home_port
            case _:
                failover_policy_alert = failover_policy

    return (
        merge_if_sections(interfaces_data_section, if_mac_list, virtual_interfaces),
        failover_policy_alert,
    )


def discover_netapp_ontap_if(
    params: Sequence[Mapping[str, Any]],
    section_netapp_ontap_if: InterfacesSection | None,
    section_netapp_ontap_if_counters: InterfacesCountersSection | None,
    section_netapp_ontap_ports: PortsSection | None,
) -> DiscoveryResult:
    if not section_netapp_ontap_if or not section_netapp_ontap_ports:
        return

    (interfaces_section, _), _ = _merge_if_counters_sections(
        section_netapp_ontap_if,
        section_netapp_ontap_ports,
        section_netapp_ontap_if_counters,
    )

    yield from interfaces.discover_interfaces(
        params,
        interfaces_section,
    )


def check_netapp_ontap_if(
    item: str,
    params: Mapping[str, Any],
    section_netapp_ontap_if: InterfacesSection | None,
    section_netapp_ontap_if_counters: InterfacesCountersSection | None,
    section_netapp_ontap_ports: PortsSection | None,
) -> CheckResult:
    if not section_netapp_ontap_if or not section_netapp_ontap_ports:
        return

    (interfaces_section, extra_info), failover_policy_alert = _merge_if_counters_sections(
        section_netapp_ontap_if,
        section_netapp_ontap_ports,
        section_netapp_ontap_if_counters,
    )

    if failover_policy_alert is not None:
        yield Result(
            state=State.UNKNOWN,
            summary=f"Failover policy: {failover_policy_alert}.",
        )

    yield from check_netapp_interfaces(
        item, params, (interfaces_section, extra_info), get_value_store()
    )


check_plugin_netapp_ontap_if = CheckPlugin(
    name="netapp_ontap_if",
    service_name="Interface %s",
    sections=["netapp_ontap_if", "netapp_ontap_if_counters", "netapp_ontap_ports"],
    discovery_ruleset_name="inventory_if_rules",
    discovery_ruleset_type=RuleSetType.ALL,
    discovery_default_parameters=dict(interfaces.DISCOVERY_DEFAULT_PARAMETERS),
    discovery_function=discover_netapp_ontap_if,
    check_ruleset_name="interfaces",
    check_default_parameters=interfaces.CHECK_DEFAULT_PARAMETERS,
    check_function=check_netapp_ontap_if,
)
