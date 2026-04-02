#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
# Original author: thl-cmk[at]outlook[dot]com

# Pydantic requires the property to be under computed_field to work.
# mypy: disable-error-code="prop-decorator"

# TODO: create service label cmk/meraki/uplink:yes/no

import json
from collections.abc import Mapping
from typing import Final, Literal, NotRequired, TypedDict

from pydantic import BaseModel, computed_field, Field

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    HostLabel,
    HostLabelGenerator,
    InventoryPlugin,
    InventoryResult,
    render,
    Result,
    Service,
    State,
    StringTable,
    TableRow,
)
from cmk.plugins.cisco_meraki.lib.type_defs import PossiblyMissing

_ETHERNET_INTERFACE_PORT_TYPE: Final = 6


type Section = Mapping[str, SwitchPortsStatus]

Status = Literal["up", "down", "unknown"]


class CDP(BaseModel, frozen=True):
    port_id: str = Field(alias="portId")

    address: str | None = None
    capabilities: str | None = None
    device_id: str | None = Field(default=None, alias="deviceId")
    platform: str | None = None
    version: str | None = None
    native_vlan: int | None = Field(default=None, alias="nativeVlan")


class LLDP(BaseModel, frozen=True):
    port_id: str = Field(alias="portId")

    system_name: str | None = Field(default=None, alias="systemName")
    system_capabilities: str | None = Field(default=None, alias="systemCapabilities")
    chassis_id: str | None = Field(default=None, alias="chassisId")
    management_address: str | None = Field(default=None, alias="managementAddress")
    port_description: str | None = Field(default=None, alias="portDescription")
    system_description: str | None = Field(default=None, alias="systemDescription")


class SecurePort(BaseModel, frozen=True):
    enabled: bool


class SpanningTree(BaseModel, frozen=True):
    statuses: list[str]


class UsageInKbps(BaseModel, frozen=True):
    recv: float
    sent: float
    total: float


class SwitchPortsStatus(BaseModel, frozen=True):
    client_count: int = Field(alias="clientCount")
    duplex: str
    enabled: bool
    errors: list[str]
    is_uplink: bool = Field(alias="isUplink")
    raw_port_id: int | str = Field(alias="portId")
    speed: str
    status: str
    warnings: list[str]

    power_usage_in_wh: float | None = Field(default=None, alias="powerUsageInWh")

    cdp: PossiblyMissing[CDP] = None
    lldp: PossiblyMissing[LLDP] = None
    secure_port: PossiblyMissing[SecurePort] = Field(default=None, alias="securePort")
    spanning_tree: PossiblyMissing[SpanningTree] = Field(default=None, alias="spanningTree")
    traffic_in_kbps: PossiblyMissing[UsageInKbps] = Field(default=None, alias="trafficInKbps")

    @property
    def port_id(self) -> int:
        return int(self.raw_port_id)

    @computed_field
    @property
    def has_valid_port_id(self) -> bool:
        match self.raw_port_id:
            case int():
                return True
            case str(port_id) if port_id.isdigit():
                return True
            case _:
                return False

    @computed_field
    @property
    def admin_status(self) -> int:
        return 1 if self.enabled else 2

    @computed_field
    @property
    def admin_state(self) -> Status:
        return "up" if self.enabled else "down"

    @computed_field
    @property
    def oper_status(self) -> int | None:
        match self.status.lower():
            case "connected":
                return 1
            case "disconnected":
                return 2
            case _:
                return None

    @computed_field
    @property
    def oper_state(self) -> Status:
        match self.status.lower():
            case "connected":
                return "up"
            case "disconnected":
                return "down"
            case _:
                return "unknown"

    @computed_field
    @property
    def speed_summary(self) -> str:
        return self.speed if self.speed else "unknown"

    @computed_field
    @property
    def speed_as_int(self) -> int | None:
        if not self.speed:
            return None

        raw_value, unit = self.speed.split()  # "10 Gbps" => ("10", "Gbps")
        value = float(raw_value.replace(",", "."))  # handle comma decimal point

        match unit.lower()[0]:
            case "k":  # kilobit per second
                return int(value + 1e3)
            case "m":  # megabit per second
                return int(value * 1e6)
            case "g":  # gigabit per second
                return int(value * 1e9)
            case "t":  # terabit per second
                return int(value * 1e12)
            case _:
                return None

    @computed_field
    @property
    def name(self) -> str:
        return f"Port {self.port_id}"


def parse_switch_ports_statuses(string_table: StringTable) -> Section:
    # NOTE: made this return a dictionary because the original implementation used the early access
    # endpoint from Meraki to get multiple ports from the organization SDK. For right now, we'll
    # just return the single port status, but we may in the future fetch the ports from the
    # organization resource:
    # https://developer.cisco.com/meraki/api-v1/get-organization-switch-ports-statuses-by-switch/
    match string_table:
        case [[payload]] if payload:
            statuses = (SwitchPortsStatus.model_validate(data) for data in json.loads(payload))
            return {
                str(switch_port.port_id): switch_port
                for switch_port in statuses
                if switch_port.has_valid_port_id
            }
        case _:
            return {}


def host_label_meraki_switch_ports_statuses(section: Section) -> HostLabelGenerator:
    """Host label function

    Labels:
        cmk/meraki/has_lldp_neighbors:
            This label is set to "yes" for all hosts with LLDP neighbors
    """
    # NOTE: only setting LLDP label as Meraki CDP data are not useful for NVDCT.
    for port in section.values():
        if port.lldp:
            yield HostLabel(name="cmk/meraki/has_lldp_neighbors", value="yes")


agent_section_cisco_meraki_org_switch_ports_statuses = AgentSection(
    name="cisco_meraki_org_switch_ports_statuses",
    parse_function=parse_switch_ports_statuses,
    host_label_function=host_label_meraki_switch_ports_statuses,
)


class DiscoveryParams(TypedDict):
    admin_port_states: list[str]
    operational_port_states: list[str]


def discover_switch_ports_statuses(params: DiscoveryParams, section: Section) -> DiscoveryResult:
    for item, port in section.items():
        if (
            port.admin_state in params["admin_port_states"]
            and port.oper_state in params["operational_port_states"]
        ):
            yield Service(
                item=item,
                parameters={
                    "admin_state": port.admin_state,
                    "operational_state": port.oper_state,
                    "speed": port.speed_summary,
                },
            )


def render_network_bandwidth_bits(value: float) -> str:
    return render.networkbandwidth(value / 8)


def _state_has_changed(is_state: str | None, was_state: str | None) -> bool:
    match (is_state, was_state):
        case (str(), None):
            return True
        case (current, prior) if current == prior:
            return False
        case _:
            return True


class CheckParams(TypedDict):
    state_admin_change: int
    state_disabled: int
    state_not_connected: int
    state_not_full_duplex: int
    state_op_change: int
    state_speed_change: int

    # Information persisted during service discovery.
    admin_state: NotRequired[Status]
    operational_state: NotRequired[Status]
    speed: NotRequired[str]


def check_switch_ports_statuses(item: str, params: CheckParams, section: Section) -> CheckResult:
    if (port := section.get(item)) is None:
        return

    prior_admin_state = params.get("admin_state", "unknown")
    prior_oper_state = params.get("operational_state", "unknown")
    prior_speed = params.get("speed", "unknown")

    if port.admin_state == "down":
        yield Result(
            state=State(params["state_disabled"]),
            summary=f"(admin {port.admin_state})",
            details=f"Admin status: {port.admin_state}",
        )
    else:
        yield Result(state=State.OK, notice=f"Admin status: {port.admin_state}")

    if _state_has_changed(port.admin_state, prior_admin_state):
        yield Result(
            state=State(params["state_admin_change"]),
            notice=f"changed admin {prior_admin_state} -> {port.admin_state}",
        )

    # If admin status is down, there is no need to continue.
    if port.admin_state == "down":
        return

    match port.oper_state:
        case "down":
            oper_state = params["state_not_connected"]
        case "up":
            oper_state = State.OK.value
        case _:
            oper_state = State.UNKNOWN.value

    yield Result(
        state=State(oper_state),
        summary=f"({port.oper_state})",
        details=f"Operational status: {port.oper_state}",
    )

    if _state_has_changed(port.oper_state, prior_oper_state):
        yield Result(
            state=State(params["state_op_change"]),
            summary=f"changed {prior_oper_state} -> {port.oper_state}",
        )

    # If operational state is down or unknown, there is no need to continue.
    if port.oper_state in {"down", "unknown"}:
        return

    yield Result(
        state=State.OK if port.speed else State.UNKNOWN,
        summary=f"Speed: {port.speed_summary}",
    )

    if _state_has_changed(port.speed_summary, prior_speed):
        yield Result(
            state=State(params["state_speed_change"]),
            summary=f"changed {prior_speed} -> {port.speed_summary}",
        )

    if port.traffic_in_kbps:
        yield from check_levels(
            value=port.traffic_in_kbps.recv,  # Bits
            label="In",
            metric_name="if_in_bps",
            render_func=render_network_bandwidth_bits,  # Bytes
        )
        yield from check_levels(
            value=port.traffic_in_kbps.sent,  # Bits
            label="Out",
            metric_name="if_out_bps",
            render_func=render_network_bandwidth_bits,  # Bytes
        )

    if port.duplex.lower() == "full":  # check duplex state
        yield Result(state=State.OK, notice=f"Duplex: {port.duplex}")
    else:
        yield Result(state=State(params["state_not_full_duplex"]), notice=f"Duplex: {port.duplex}")

    yield Result(state=State.OK, notice=f"Clients: {port.client_count}")

    if port.is_uplink:
        yield Result(state=State.OK, summary="Uplink", details="Uplink: yes")
    else:
        yield Result(state=State.OK, notice="Uplink: no")

    if port.power_usage_in_wh:
        yield Result(state=State.OK, summary=f"Power usage: {port.power_usage_in_wh} Wh")

    if port.spanning_tree:
        for status in port.spanning_tree.statuses:
            yield Result(state=State.OK, notice=f"Spanning tree status: {status}")

    for warning in port.warnings:
        yield Result(state=State.WARN, notice=f"{warning}")

    for error in port.errors:
        if error not in {"Port disconnected", "Port disabled"}:
            yield Result(state=State.CRIT, notice=f"{error}")

    if port.secure_port and port.secure_port.enabled:
        yield Result(state=State.OK, summary="Secure port: enabled")


check_plugin_cisco_meraki_org_switch_ports_statuses = CheckPlugin(
    name="cisco_meraki_org_switch_ports_statuses",
    service_name="Interface %s",
    discovery_function=discover_switch_ports_statuses,
    check_function=check_switch_ports_statuses,
    check_default_parameters=CheckParams(
        state_admin_change=State.WARN.value,
        state_disabled=State.OK.value,
        state_not_connected=State.OK.value,
        state_not_full_duplex=State.WARN.value,
        state_op_change=State.WARN.value,
        state_speed_change=State.WARN.value,
    ),
    check_ruleset_name="cisco_meraki_switch_ports_statuses",
    discovery_ruleset_name="discovery_cisco_meraki_switch_ports_statuses",
    discovery_default_parameters={
        "admin_port_states": ["up", "down"],
        "operational_port_states": ["up", "down"],
    },
)


def inventorize_meraki_interfaces(section: Section) -> InventoryResult:
    for port in section.values():
        yield TableRow(
            path=["networking", "interfaces"],
            key_columns={"index": port.port_id},
            inventory_columns={
                "name": port.name,
                "admin_status": port.admin_status,
                **({"oper_status": port.oper_status} if port.oper_status else {}),
                **({"speed": port.speed_as_int} if port.speed_as_int else {}),
                "port_type": _ETHERNET_INTERFACE_PORT_TYPE,
            },
        )


inventory_plugin_inv_meraki_interfaces = InventoryPlugin(
    name="inv_meraki_interfaces",
    sections=["cisco_meraki_org_switch_ports_statuses"],
    inventory_function=inventorize_meraki_interfaces,
)


def inventorize_meraki_cdp_cache(section: Section) -> InventoryResult:
    path = ["networking", "cdp_cache", "neighbors"]

    for port in section.values():
        if port.cdp:
            yield TableRow(
                path=path,
                key_columns={
                    "local_port": str(port.port_id),
                    # TODO: why include this if it's always empty?
                    "neighbor_name": "",
                    "neighbor_port": port.cdp.port_id,
                },
                inventory_columns={
                    **({"capabilities": port.cdp.capabilities} if port.cdp.capabilities else {}),
                    **({"native_vlan": port.cdp.native_vlan} if port.cdp.native_vlan else {}),
                    **({"neighbor_address": port.cdp.address} if port.cdp.address else {}),
                    **({"neighbor_id": port.cdp.device_id} if port.cdp.device_id else {}),
                    **({"platform": port.cdp.platform} if port.cdp.platform else {}),
                    **({"version": port.cdp.version} if port.cdp.version else {}),
                },
            )


inventory_plugin_inv_meraki_cdp_cache = InventoryPlugin(
    name="inv_meraki_cdp_cache",
    sections=["cisco_meraki_org_switch_ports_statuses"],
    inventory_function=inventorize_meraki_cdp_cache,
)


def inventorize_meraki_lldp_cache(section: Section) -> InventoryResult:
    path = ["networking", "lldp_cache", "neighbors"]

    for port in section.values():
        if port.lldp:
            yield TableRow(
                path=path,
                key_columns={
                    "local_port": str(port.port_id),
                    "neighbor_name": port.lldp.system_name,
                    "neighbor_port": port.lldp.port_id,
                },
                inventory_columns={
                    **(
                        {"capabilities": port.lldp.system_capabilities}
                        if port.lldp.system_capabilities
                        else {}
                    ),
                    **(
                        {"neighbor_address": port.lldp.management_address}
                        if port.lldp.management_address
                        else {}
                    ),
                    **({"neighbor_id": port.lldp.chassis_id} if port.lldp.chassis_id else {}),
                    **(
                        {"port_description": port.lldp.port_description}
                        if port.lldp.port_description
                        else {}
                    ),
                    **(
                        {"system_description": port.lldp.system_description}
                        if port.lldp.system_description
                        else {}
                    ),
                },
            )


inventory_plugin_inv_meraki_lldp_cache = InventoryPlugin(
    name="inv_meraki_lldp_cache",
    sections=["cisco_meraki_org_switch_ports_statuses"],
    inventory_function=inventorize_meraki_lldp_cache,
)
