#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# License: GNU General Public License v2
#
# Author: thl-cmk[at]outlook[dot]com
# URL   : https://thl-cmk.hopto.org
# Date  : 2016-04-08
# File  : cmk_addons/plugins/inventory/agent_based/inv_cdp_cache.py

# inventory of cdp cache

# 2016-08-22: removed index column
# 2017-07-01: fixed device ID as MAC address (HPE)
# 2018-01-24: added local port info, remove 'useless' oid's
# 2018-09-04: changes for CMK 1.5.x (inv_tree --> inv_tree_list)
# 2020-03-15: added support for CMK1.6x
# 2020-07-31: added short interface names, code cleanup
# 2021-03-16: rewrite for cmk 2.0
# 2001-03-18: removed disable option from WATO, now builtin in cmk
# 2021-06-14: fixed cdp capabilities (OIDBytes/binascii) thanks to andreas[dot]doehler[at]gmail[dot]com
# 2021-07-10: made use short interface names configurable via wato
#             fixed cdcapabilities for "b''" on Cisco WLC
# 2021-07-19: fix for default parameters
# 2023-02-17: moved wato/metrics from ~/local/share/.. to ~/local/lib/... for CMK2.1
# 2023-06-14: moved wato file to check_parameters sub directory
# 2023-10-13: changed if_name to_if description, need long version for network topology
# 2023-12-21: streamlined LLDP and CDP inventory
# 2024-03-20: added host label nvdct/has_cdp_neighbours:yes if the device has at least one cdp neighbour
# 2024-04-05: fixed incomplete global cdp data (Meraki)
# 2024-04-07: fixed missing/empty global cdp data
#             improved validation if SNMP input data
#             fix crash on empty neighbour_name
# 2024-04-08: stop (early) if interface table can not be created
#             refactoring parse function
#             moved neighbour address to non-key columns
# 2024-04-14: refactoring _get_address (match/case)
#             refactoring _render_mac_address ( remove hex() )
# 2025-03-23: moved to check API 2
# 2025-05-28: remove debug to be compatible with CMK2.4
# 2025-10-18: removed: last_change to avoid changes in HW/SW-Inventory (counter don't work anyway) to avoid continues inventory changes

# ToDo: add fallback if there is no if_name to if_description -> if_alias

from binascii import hexlify
from collections.abc import Sequence
from dataclasses import dataclass
from ipaddress import AddressValueError, IPv4Address
from re import compile as re_compile, match as re_match

from cmk.agent_based.v2 import (
    Attributes,
    HostLabel,
    HostLabelGenerator,
    InventoryPlugin,
    InventoryResult,
    OIDBytes,
    OIDEnd,
    SNMPSection,
    SNMPTree,
    StringByteTable,
    TableRow,
    exists,
)

_INTERFACE_DISPLAY_HINTS = {
    'ethernet': 'eth',
    'fastethernet': 'Fa',
    'gigabitethernet': 'Gi',
    'tengigabitethernet': 'Te',
    'fortygigabitethernet': 'Fo',
    'hundredgigabitethernet': 'Hu',
    'port-channel': 'Po',
    'tunnel': 'Tu',
    'loopback': 'Lo',
    'cellular': 'Cel',
    'vlan': 'Vlan',
    'management': 'Ma',
}


@dataclass(frozen=True)
class CdpGlobal:
    enabled: str | None
    hold_time: int | None
    local_id: str | None
    message_interval: int | None


@dataclass(frozen=True)
class CdpNeighbour:
    # key columns
    neighbour_id: str
    neighbour_port: str
    local_port: str
    # non-key columns
    address: str | None
    capabilities: str | None
    duplex: str | None
    native_vlan: str | None
    platform: str | None
    platform_details: str | None
    power_consumption: str | None
    vtp_mgmt_domain: str | None


@dataclass(frozen=True)
class Cdp:
    cdp_global: CdpGlobal | None
    cdp_neighbours: Sequence[CdpNeighbour]


def _get_short_if_name(if_name: str) -> str:
    """
    returns short interface name from long interface name
    if_name: is the long interface name
    :type if_name: str
    """

    for if_name_prefix in _INTERFACE_DISPLAY_HINTS.keys():
        if if_name.lower().startswith(if_name_prefix.lower()):
            if_name_short = _INTERFACE_DISPLAY_HINTS[if_name_prefix]
            return if_name.lower().replace(if_name_prefix.lower(), if_name_short, 1)
    return if_name


def _get_cdp_duplex(st: str) -> str | None:
    names = {
        '0': 'N/A',
        '1': 'unknown',
        '2': 'half duplex',
        '3': 'full duplex',
    }
    return names.get(st)


def _render_ip_address(bytestring) -> str | None:
    if len(bytestring) == 14:  # "0A 0D FC 15 "  -> some Nexus
        ip_address = bytestring.strip('"').strip(' ').split(' ')
        if len(ip_address) == 4:
            ip_address = '.'.join([f'{int(m, 16)}' for m in ip_address])
    else:
        ip_address = '.'.join([f'{ord(m)}' for m in bytestring])
    try:
        return IPv4Address(ip_address).exploded
    except AddressValueError:
        # maybe I let it crash here on purpose with bad data
        pass


def _render_mac_address(bytestring) -> str | None:
    if mac_address := _sanitize_mac(''.join([f'{ord(m):02x}' for m in bytestring])):
        return mac_address
    # try encode().hex()
    if mac_address := _sanitize_mac(bytestring.encode().hex()):
        return mac_address


def _sanitize_mac(mac: str) -> str | None:
    """
    Returns mac address from string in the format AA:BB:CC:DD:EE:FF
    Valid input MAC formats are (upper case is also ok)
    aa:bb:cc:dd:ee:ff
    aabb-ccdd-eeff
    aabbcc-ddeeff
    aabbccddeeff
    :type mac: str
    """
    re_mac_pattern = (
        '^'  # beginning of line
        '(([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2})'  # aa:bb:cc:dd:ee:ff
        '|(([0-9a-fA-F]{4}[\\.\\-]){2}[0-9a-fA-F]{4})|'  # or aabb-ccdd-eeff
        '(([0-9a-fA-F]{6}\\-[0-9a-fA-F]{6}))'  # or aabbcc-ddeeff
        '|([0-9a-fA-F]{12})'  # or aabbccddeeff
        '$'  # end of line
    )
    re_mac_pattern = re_compile(re_mac_pattern)
    if re_match(re_mac_pattern, mac):
        temp = mac.replace(':', '').replace('-', '').replace('.', '').upper()
        temp = ':'.join([temp[i] + temp[i + 1] for i in range(0, 12, 2)])
        return temp


def _get_capabilities(raw_capabilities) -> str | None:
    cdp_capabilities = {
        0: '',
        1: 'L3',  # router
        2: 'TB',  # transparent bridge
        4: 'SB',  # source route bridge
        8: 'L2',  # switch
        16: 'Host',
        32: 'IGMP',  # IGMP snooping
        64: 'Repeater',
        128: 'Phone',  #
        256: 'Remote',  #
        512: 'CVTA',  #
        1024: 'Two-port Mac Relay',  #
    }

    byte_string = hexlify(bytearray(raw_capabilities))
    try:
        raw_capabilities = int(byte_string, 16)
    except ValueError:
        return None

    capabilities = [
        value for capability, value in cdp_capabilities.items() if cdp_capabilities.get(raw_capabilities & capability)
    ]
    if capabilities:
        capabilities.sort()
        return ', '.join(capabilities)


def _is_ascii(str_to_test: str) -> bool:
    try:
        _test = str_to_test.encode().decode('ascii')
    except UnicodeDecodeError:
        return False
    return True


def _get_address(address_type: str, raw_address: str) -> str | None:
    match address_type:
        case '1':  # ip address
            if (address := _render_ip_address(raw_address)) is not None:
                return address
        case '65535':  # unknown (HPE stack MAC address)
            if (address := _render_mac_address(raw_address)) is not None:
                return address
        case _:
            # maybe I let it crash on purpose with bad data
            pass


def _get_device_id(raw_device_id: str) -> str | None:
    if not _is_ascii(raw_device_id):
        if (device_id := _render_mac_address(raw_device_id)) is not None:
            return device_id
        if (device_id := _render_ip_address(raw_device_id)) is not None:
            return device_id
        return None

    if len(raw_device_id) in [12, 13, 14, 17]:
        if (device_id := _sanitize_mac(raw_device_id)) is not None:
            return device_id

    if len(raw_device_id) == 6:
        if (device_id := _render_mac_address(raw_device_id)) is not None:
            return device_id
    return raw_device_id


def _get_device_port(raw_device_port: str) -> str | None:
    if not _is_ascii(raw_device_port):
        if (device_port := _render_mac_address(raw_device_port)) is not None:
            return device_port
        if (device_port := _render_ip_address(raw_device_port)) is not None:
            return device_port

    return raw_device_port


def parse_inv_cdp_cache(string_table: Sequence[StringByteTable]) -> Cdp | None:
    try:
        cdp_info, cdp_global, if_info = string_table
    except ValueError:
        return None

    try:
        interface_by_index = {if_index: if_name for if_index, if_name in if_info}
    except ValueError:
        return None

    try:
        cdp_run, cdp_message_interval, cdp_hold_time, local_device_id = cdp_global[0]
    except (ValueError, IndexError):
        global_info = None
    else:
        _cdp_run = {
            '0': 'no',
            '1': 'yes',
        }

        global_info = CdpGlobal(
            enabled=_cdp_run.get(cdp_run),
            message_interval=int(cdp_message_interval) if cdp_message_interval.isdigit() else None,
            hold_time=int(cdp_hold_time) if cdp_hold_time.isdigit() else None,
            local_id=str(local_device_id) if local_device_id else None,
        )

    neighbours = []

    for entry in cdp_info:
        try:
            oid_end, address_type, address, platform_details, device_id, device_port, platform, \
                capabilities, vtp_mgmt_domain, native_vlan, duplex, power_consumption = entry
        except ValueError:
            continue

        # skip neighbour if one of the key columns is None
        if (neighbour_id := _get_device_id(device_id)) is None:
            continue
        if (neighbour_port := _get_device_port(device_port)) is None:
            continue
        if_index = oid_end.split('.')[0]
        if (local_port := interface_by_index.get(if_index, if_index)) is None:
            continue

        neighbours.append(CdpNeighbour(
            address=_get_address(address_type, address),
            platform_details=str(platform_details) if platform_details else None,
            neighbour_id=neighbour_id,
            neighbour_port=neighbour_port,
            local_port=local_port,
            platform=str(platform) if platform else None,
            capabilities=_get_capabilities(capabilities),
            vtp_mgmt_domain=str(vtp_mgmt_domain) if vtp_mgmt_domain else None,
            native_vlan=str(native_vlan) if str(native_vlan) else None,
            duplex=_get_cdp_duplex(duplex),
            power_consumption=str(power_consumption) if str(power_consumption) else None,
        ))

    return Cdp(
        cdp_global=global_info,
        cdp_neighbours=neighbours
    )


def host_label_inv_cdp_cache(section: Cdp) -> HostLabelGenerator:
    if len(section.cdp_neighbours) > 0:
        yield HostLabel(name="nvdct/has_cdp_neighbours", value="yes")


def inventory_cdp_cache(params, section: Cdp) -> InventoryResult:
    path = ['networking', 'cdp_cache']

    if section.cdp_global:
        yield Attributes(
            path=path,
            inventory_attributes={
                **({"enabled": section.cdp_global.enabled} if section.cdp_global.enabled else {}),
                **(
                    {"message_interval": section.cdp_global.message_interval}
                    if section.cdp_global.message_interval else {}
                ),
                **({"hold_time": section.cdp_global.hold_time} if section.cdp_global.hold_time else {}),
                **({"local_name": section.cdp_global.local_id} if section.cdp_global.local_id else {}),
            }
        )

    path = path + ['neighbours']
    for neighbour in section.cdp_neighbours:

        neighbour_id = str(neighbour.neighbour_id)
        if params.get('remove_domain'):
            if params.get('domain_name'):
                neighbour_id = neighbour_id.replace(params['domain_name'], '')
            else:
                neighbour_id = neighbour_id.split('.')[0]

        neighbour_port = neighbour.neighbour_port
        local_port = neighbour.local_port
        if params.get('use_short_if_name'):
            neighbour_port = _get_short_if_name(neighbour_port)
            local_port = _get_short_if_name(local_port)

        key_columns = {
            'neighbour_name': neighbour_id,
            'neighbour_port': neighbour_port,
            'local_port': local_port,
        }

        inventory_columns = {}
        for key, value in [
            ('neighbour_address', neighbour.address),
            ('platform_details', neighbour.platform_details),
            ('platform', neighbour.platform),
            ('capabilities', neighbour.capabilities),
            ('vtp_mgmt_domain', neighbour.vtp_mgmt_domain),
            ('native_vlan', neighbour.native_vlan),
            ('duplex', neighbour.duplex),
            ('power_consumption', neighbour.power_consumption),
        ]:
            if key not in params.get('removecolumns', []) and value is not None:
                inventory_columns[key] = value

        yield TableRow(
            path=path,
            key_columns=key_columns,
            inventory_columns=inventory_columns,
        )


snmp_section_inv_cdp_cache = SNMPSection(
    name='inv_cdp_cache',
    parse_function=parse_inv_cdp_cache,
    host_label_function=host_label_inv_cdp_cache,
    fetch=[
        SNMPTree(
            base='.1.3.6.1.4.1.9.9.23.1.2.1.1',  # CISCO-CDP-MIB::cdpCacheEntry
            oids=[
                OIDEnd(),  # ifIndex.neighbour-index-on-interface
                '3',  # cdpCacheAddressType
                '4',  # cdpCacheAddress
                '5',  # cdpCacheVersion   # is not version but platform details
                '6',  # cdpCacheDeviceId
                '7',  # cdpCacheDevicePort
                '8',  # cdpCachePlatform
                OIDBytes('9'),  # cdpCacheCapabilities
                '10',  # cdpCacheVTPMgmtDomain
                '11',  # cdpCacheNativeVLAN
                '12',  # cdpCacheDuplex
                '15',  # cdpCachePowerConsumption
                # '24',  # cdpCacheLastChange
            ]
        ),
        SNMPTree(
            base='.1.3.6.1.4.1.9.9.23.1.3',  # CISCO-CDP-MIB::cdpGlobal
            oids=[
                '1',  # cdpGlobalRun
                '2',  # cdpGlobalMessageInterval
                '3',  # cdpGlobalHoldTime
                '4',  # cdpGlobalDeviceId
                # '5',  # cdpGlobalLastChange
                # '6',  # cdpGlobalDeviceIdFormatCpb
                # '7',  # cdpGlobalDeviceIdFormat
            ]
        ),
        SNMPTree(
            base='.1.3.6.1.2.1.31.1.1.1',  # IF-MIB::ifXEntry
            oids=[
                OIDEnd(),  # ifIndex
                '1',  # ifName
            ]),
    ],
    detect=exists('.1.3.6.1.4.1.9.9.23.1.2.1.1.*'),  # CISCO-CDP-MIB::cdpCacheEntry
)

inventory_plugin_inv_cdp_cache = InventoryPlugin(
    name='inv_cdp_cache',
    inventory_function=inventory_cdp_cache,
    inventory_default_parameters={},
    inventory_ruleset_name='inv_cdp_cache',
)
