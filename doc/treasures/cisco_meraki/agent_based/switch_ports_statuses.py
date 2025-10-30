#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
# Original author: thl-cmk[at]outlook[dot]com


# ToDo: create service label cmk/meraki/uplink:yes/no

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    InventoryPlugin,
    InventoryResult,
    Result,
    Service,
    State,
    StringTable,
    TableRow,
    check_levels,
    render,
    HostLabelGenerator,
    HostLabel,
)

from cmk_addons.plugins.meraki.lib.utils import get_float, get_int, load_json


@dataclass(frozen=True)
class SwitchSecurePort:
    active: bool | None
    authentication_status: str | None
    configOverrides: Mapping[any] | None
    enabled: bool | None

    __secure_port =  {
        "active": False,
        "authenticationStatus": "Disabled",
        "configOverrides": {},
        "enabled": False,
    }

    @classmethod
    def parse(cls, secure_port: Mapping[str, any] | None):
        return cls(
            active=bool(secure_port['active']) if secure_port.get('active') is not None else None,
            authentication_status=str(secure_port['authenticationStatus']) if secure_port.get(
                'authenticationStatus') is not None else None,
            configOverrides=secure_port['configOverrides'] if secure_port.get('configOverrides') is not None else None,
            enabled=bool(secure_port['enabled']) if secure_port.get('enabled') is not None else None,
        ) if secure_port else None


@dataclass(frozen=True)
class SwitchPortCDP:
    address: str | None
    capabilities: str | None
    device_id: str | None
    device_port: str | None
    platform: str | None
    version: str | None
    native_vlan: str | None

    __cdp = {
        "address": "172.24.10.1",
        "capabilities": "Switch",
        "deviceId": "149f43b14530",
        "nativeVlan": 10,
        "platform": "MS250-48FP",
        "portId": "Port 49",
        "version": "1",
    }

    @classmethod
    def parse(cls, cdp: Mapping[str, str] | None):
        return cls(
            address=str(cdp['address']) if cdp.get('address') is not None else None,
            capabilities=str(cdp['capabilities']) if cdp.get('capabilities') is not None else None,
            device_id=str(cdp['deviceId']) if cdp.get('deviceId') is not None else None,
            device_port=str(cdp['portId']) if cdp.get('portId') is not None else None,
            native_vlan=str(cdp['nativeVlan']) if cdp.get('nativeVlan') is not None else None,
            platform=str(cdp['platform']) if cdp.get('platform') is not None else None,
            version=str(cdp['version']) if cdp.get('version') is not None else None,
        ) if cdp else None


@dataclass(frozen=True)
class SwitchPortLLDP:
    cache_capabilities: str | None
    chassis_id: str | None
    management_address: str | None
    port_description: str | None
    port_id: str | None
    system_description: str | None
    system_name: str | None

    __lldp = {
        "chassisId": "14:9f:43:b1:45:30",
        "managementAddress": "172.24.10.1",
        "managementVlan": 10,
        "portDescription": "Port 49",
        "portId": "49",
        "portVlan": 10,
        "systemCapabilities": "S-VLAN Component of a VLAN Bridge",
        "systemDescription": "Meraki MS250-48FP Cloud Managed PoE Switch",
        "systemName": "Meraki MS250-48FP - DV1-R005",
    }

    @classmethod
    def parse(cls, lldp: Mapping[str, str] | None):
        return cls(
            cache_capabilities=str(lldp['systemCapabilities']) if lldp.get('systemCapabilities') is not None else None,
            chassis_id=str(lldp['chassisId']) if lldp.get('chassisId') is not None else None,
            management_address=str(lldp['managementAddress']) if lldp.get('managementAddress') is not None else None,
            port_description=str(lldp['portDescription']) if lldp.get('portDescription') is not None else None,
            port_id=str(lldp['portId']) if lldp.get('portId') is not None else None,
            system_description=str(lldp['systemDescription']) if lldp.get('systemDescription') is not None else None,
            system_name=str(lldp['systemName']) if lldp.get('systemName') is not None else None,
        ) if lldp else None


@dataclass(frozen=True)
class SwitchPortUsage:
    recv: float
    sent: float
    total: float

    @classmethod
    def parse(cls, usage: Mapping[str, float] | None):
        """
        Usage in KiloBits -> changed to Bits.
        Args:
            usage: Mapping with the keys 'total', 'sent', 'recv', the values are all int.
                   I.e. {"total": 1944476, "sent": 1099104, "recv": 845372}

        Returns:

        """
        return cls(
            recv=get_float(usage.get('recv')) * 1000,
            sent=get_float(usage.get('sent')) * 1000,
            total=get_float(usage.get('total')) * 1000,
        ) if usage else None


@dataclass(frozen=True)
class SwitchPortTraffic:
    total: float  # The average speed of the data sent and received (in kilobits-per-second).
    sent: float  # The average speed of the data sent (in kilobits-per-second).
    recv: float  # The average speed of the data received (in kilobits-per-second).

    @classmethod
    def parse(cls, traffic: Mapping[str, float] | None):
        """
        A breakdown of the average speed of data that has passed through this port during the timespan.

        input traffic values are  KiloBts/s. Output values are changed to Bits/s
        Args:
            traffic: Mapping with the keys 'total', 'sent', 'recv', the values are all float.
                     I.e. {"total": 184.4, "sent": 104.2, "recv": 80.2}

        Returns:
        """

        return cls(
            recv=get_float(traffic.get('recv')) * 1000,
            sent=get_float(traffic.get('sent')) * 1000,
            total=get_float(traffic.get('total')) * 1000,
        ) if traffic else None


@dataclass(frozen=True)
class SwitchPortSpanningTree:
    status: Sequence[str]

    @classmethod
    def parse(cls, spanning_tree: Mapping[str, Sequence[str]]):
        """
        {"statuses": ["Forwarding", "Is edge", "Is peer-to-peer"]}
        {"statuses": []}
        Args:
            spanning_tree:

        Returns:

        """

        if isinstance(spanning_tree, dict):
            return cls(
                status=[str(status) for status in spanning_tree.get('statuses', [])]
            )


def parse_admin_state(admin_state: bool | None) -> str | None:
    state_map = {
        True: 1,
        False: 2,
    }
    return state_map.get(admin_state)


def parse_operational_state(operational_state: str | None) -> str | None:
    state_map = {
        'connected': 1,
        'disconnected': 2,
    }
    if isinstance(operational_state, str):
        return state_map.get(operational_state.lower())


@dataclass(frozen=True)
class SwitchPort:
    port_id: int  # needs to bee always there
    admin_state: int | None
    cdp: SwitchPortCDP | None
    client_count: int | None
    duplex: str | None
    errors: Sequence[str] | None
    is_up_link: bool | None
    lldp: SwitchPortLLDP | None
    operational_state: int | None
    power_usage_in_wh: float | None
    secure_port: SwitchSecurePort | None
    spanning_tree: SwitchPortSpanningTree | None
    speed: str | None
    traffic: SwitchPortTraffic | None
    usage: SwitchPortUsage | None
    warnings: Sequence[str]
    # syntetic settings
    # alias: str | None
    # description: str | None
    port_type: int | None
    name: str | None

    @classmethod
    def parse(cls, port: Mapping[str, object]):
        return cls(
            port_id=int(port['portId']),  # needs to be always there
            admin_state=parse_admin_state(port.get('enabled')),
            cdp=SwitchPortCDP.parse(port.get('cdp')),
            client_count=get_int(port.get('clientCount')),
            duplex=str(port['duplex']) if port.get('duplex') is not None else None,
            errors=port['errors'] if port.get('errors') is not None else None,
            is_up_link=bool(port['isUplink']) if port.get('isUplink') is not None else None,
            lldp=SwitchPortLLDP.parse(port.get('lldp')),
            operational_state=parse_operational_state(port.get('status')),
            power_usage_in_wh=get_float(port.get('powerUsageInWh')),
            secure_port=SwitchSecurePort.parse(port.get('securePort')),
            spanning_tree=SwitchPortSpanningTree.parse(port.get('spanningTree')),
            speed=str(port['speed']) if port.get('speed') is not None else None,
            traffic=SwitchPortTraffic.parse((port.get('trafficInKbps'))),
            usage=SwitchPortUsage.parse(port.get('usageInKb')),
            warnings=port['warnings'] if port.get('warnings') is not None else None,
            # synthetic settings
            # alias=f'Port {port["portId"]}' if port.get('portId') is not None else None,
            # description=f'Port {port["portId"]}' if port.get('portId') is not None else None,
            port_type=6,
            name=f'Port {port["portId"]}' if port.get('portId') is not None else None,
        )


def host_label_meraki_switch_ports_statuses(section: Mapping[str, SwitchPort]) -> HostLabelGenerator:
    """Host label function
    Labels:
        "nvdct/has_lldp_neighbours":
            This label is set to "yes" for all hosts with LLDP neighbours
    """
    for port in section.values():
        if port.lldp:
            yield HostLabel(name="nvdct/has_lldp_neighbours", value="yes")
            break
    # only set LLDP label, Meraki CDP data are not usefully for NVDCT


def parse_switch_ports_statuses(string_table: StringTable) -> Mapping[str, SwitchPort] | None:
    json_data = load_json(string_table)
    json_data = json_data[0]
    # for Early Access MerakiGetOrganizationSwitchPortsStatusesBySwitch
    if isinstance(json_data, dict) and 'ports' in json_data.keys():
        json_data = json_data['ports']

    return {port["portId"]: SwitchPort.parse(port) for port in json_data if port.get('portId', '').isdigit()}


agent_section_cisco_meraki_org_switch_ports_statuses = AgentSection(
    name="cisco_meraki_org_switch_ports_statuses",
    parse_function=parse_switch_ports_statuses,
    host_label_function=host_label_meraki_switch_ports_statuses,
)


def discover_switch_ports_statuses(params: Mapping[str, object], section: Mapping[str, SwitchPort]) -> DiscoveryResult:
    state_map = {
        1: 'up',
        2: 'down',
    }
    admin_port_states = params['admin_port_states']
    operational_port_states = params['operational_port_states']

    for item, port in section.items():
        if state_map.get(port.admin_state) in admin_port_states and \
                state_map.get(port.operational_state) in operational_port_states:
            yield Service(
                item=item,
                parameters={
                    'admin_state': port.admin_state,
                    'operational_state': port.operational_state,
                    'speed': port.speed,
                }
            )


def render_network_bandwidth_bits(value: float) -> str:
    return render.networkbandwidth(value/8)


def check_switch_ports_statuses(item: str, params: Mapping[str, any], section: Mapping[str, SwitchPort]) -> CheckResult:
    state_map = {
        1: 'up',
        2: 'down',
    }

    is_up_link = {
        True: 'yes',
        False: 'no',
    }

    def has_changed (is_state: int | str | None, was_state: int | str | None) -> bool:
        if not is_state or not was_state:
            # ignore if state is None -> meaning this change is expected. OP state down -> op -> speed None -> xxx
            return False

        if is_state == was_state:
            return False

        return True

    if (port := section.get(item)) is None:
        return

    if port.admin_state == 2:
        yield Result(
            state=State(params['state_disabled']),
            summary=f'(admin {state_map.get(port.admin_state)})',
            details=f'Admin status: {state_map.get(port.admin_state)}',
        )
    else:
        yield Result(state=State.OK, notice=f'Admin status: {state_map.get(port.admin_state)}')

    if has_changed(port.admin_state, params['admin_state']):
        message = f'changed admin {state_map.get(params["admin_state"])} -> {state_map.get(port.admin_state)}'
        yield Result(state=State(params['state_admin_change']), notice=message)

    if port.admin_state == 2:  # down
        return

    if port.operational_state == 2:
        yield Result(
            state=State(params['state_not_connected']),
            summary=f'({state_map.get(port.operational_state)})',
            details=f'Operational status: {state_map.get(port.operational_state)}'
        )
    else:
        yield Result(
            state=State.OK,
            summary=f'({state_map.get(port.operational_state)})',
            details=f'Operational status: {state_map.get(port.operational_state)}'
        )

    if has_changed(port.operational_state, params['operational_state']):
        message = f'changed {state_map.get(params["operational_state"])} -> {state_map.get(port.operational_state)}'
        yield Result(state=State(params['state_op_change']), summary=message)

    if port.operational_state == 2:
        return

    yield Result(state=State.OK, summary=f'Speed: {port.speed}')

    if has_changed(port.speed, params['speed']):
        message = f'changed {params["speed"]} -> {port.speed}'
        yield Result(state=State(params['state_speed_change']), summary=message)


    if params.get('show_traffic') and port.traffic:
        yield from check_levels(
            value=port.traffic.recv,  # Bits
            label='In',
            metric_name='if_in_bps',
            render_func=render_network_bandwidth_bits,  # Bytes
            # notice_only=True,
        )
        yield from check_levels(
            value=port.traffic.sent,  # Bits
            label='Out',
            metric_name='if_out_bps',
            render_func=render_network_bandwidth_bits,  # Bytes
            # notice_only=True,
        )

        if port.duplex.lower() == 'full':  # check duplex state
            yield Result(state=State.OK, notice=f'Duplex: {port.duplex}')
        else:
            yield Result(state=State(params['state_not_full_duplex']), notice=f'Duplex: {port.duplex}')
        yield Result(state=State.OK, notice=f'Clients: {port.client_count}')

    if port.is_up_link:
        yield Result(state=State.OK, summary='UP-Link', details=f'UP-Link: {is_up_link[bool(port.is_up_link)]}')
    else:
        yield Result(state=State.OK, notice=f'UP-Link: {is_up_link[port.is_up_link]}')

    if port.power_usage_in_wh:
        yield Result(state=State.OK, summary=f'Power usage: {port.power_usage_in_wh} Wh')

    if port.spanning_tree:
        for status in port.spanning_tree.status:
            yield Result(state=State.OK, notice=f'Spanning-tree status: {status}')

    for warning in port.warnings:
        yield Result(state=State.WARN, notice=f'{warning}')
    for error in port.errors:
        if error not in ['Port disconnected', 'Port disabled']:
            yield Result(state=State.CRIT, notice=f'{error}')

    if port.secure_port and port.secure_port.enabled:
        yield Result(state=State.UNKNOWN, summary=f'Secure Port enabled', details=f'Secure Port: {port.secure_port}')


check_plugin_cisco_meraki_org_switch_ports_statuses = CheckPlugin(
    name='cisco_meraki_org_switch_ports_statuses',
    service_name='Interface %s',
    discovery_function=discover_switch_ports_statuses,
    check_function=check_switch_ports_statuses,
    check_default_parameters={
        'state_disabled': 0,
        'state_not_connected': 0,
        'state_not_full_duplex': 1,
        'state_speed_change': 1,
        'state_admin_change': 1,
        'state_op_change': 1,
    },
    check_ruleset_name='cisco_meraki_switch_ports_statuses',
    discovery_ruleset_name='discovery_cisco_meraki_switch_ports_statuses',
    discovery_default_parameters={
        'admin_port_states': ['up', 'down'],
        'operational_port_states': ['up', 'down'],
    }
)


def inventory_meraki_interfaces(section: Mapping[str, SwitchPort]) -> InventoryResult:
    for port in section.values():
        yield TableRow(
            path=['networking', 'interfaces'],
            key_columns={
                "index": port.port_id,
            },
            inventory_columns={
                # **({'alias': port.alias} if port.alias else {}),
                # **({'description': port.description} if port.description else {}),
                **({'name': port.name} if port.name else {}),
                **({'admin_status': port.admin_state} if port.admin_state else {}),
                **({'oper_status': port.operational_state} if port.operational_state else {}),
                **({'speed': port.speed} if port.speed else {}),
                **({'port_type': port.port_type} if port.port_type else {}),
            },
        )


inventory_plugin_inv_meraki_interfaces = InventoryPlugin(
    name='inv_meraki_interfaces',
    sections=['cisco_meraki_org_switch_ports_statuses'],
    inventory_function=inventory_meraki_interfaces,
)


def inventory_meraki_cdp_cache(section: Mapping[str, SwitchPort]) -> InventoryResult:
    path = ['networking', 'cdp_cache', 'neighbours']

    for port in section.values():
        if cdp := port.cdp:
            key_columns = {
                'local_port': port.port_id,
                'neighbour_name': '',
                'neighbour_port': cdp.device_port,
            }
            neighbour = {
                **({'capabilities': cdp.capabilities} if cdp.capabilities else {}),
                **({'native_vlan': cdp.native_vlan} if cdp.native_vlan else {}),
                **({'neighbour_address': cdp.address} if cdp.address else {}),
                **({'neighbour_id': cdp.device_id} if cdp.device_id else {}),
                **({'platform': cdp.platform} if cdp.platform else {}),
                **({'version': cdp.version} if cdp.version else {}),
            }
            yield TableRow(
                path=path,
                key_columns=key_columns,
                inventory_columns=neighbour
            )


inventory_plugin_inv_meraki_cdp_cache = InventoryPlugin(
    name='inv_meraki_cdp_cache',
    sections=['cisco_meraki_org_switch_ports_statuses'],
    inventory_function=inventory_meraki_cdp_cache,
)


def inventory_meraki_lldp_cache(section: Mapping[str, SwitchPort]) -> InventoryResult:
    path = ['networking', 'lldp_cache', 'neighbours']

    for port in section.values():
        if lldp := port.lldp:
            key_columns = {
                'local_port': str(port.port_id),
                'neighbour_name': lldp.system_name,
                'neighbour_port': lldp.port_id,
            }
            neighbour = {
                **({'capabilities': lldp.cache_capabilities} if lldp.cache_capabilities else {}),
                **({'neighbour_address': lldp.management_address} if lldp.management_address else {}),
                **({'neighbour_id': lldp.chassis_id} if lldp.chassis_id else {}),
                **({'port_description': lldp.port_description} if lldp.port_description else {}),
                **({'system_description': lldp.system_description} if lldp.system_description else {}),
            }
            yield TableRow(
                path=path,
                key_columns=key_columns,
                inventory_columns=neighbour
            )


inventory_plugin_inv_meraki_lldp_cache = InventoryPlugin(
    name='inv_meraki_lldp_cache',
    sections=['cisco_meraki_org_switch_ports_statuses'],
    inventory_function=inventory_meraki_lldp_cache,
)
