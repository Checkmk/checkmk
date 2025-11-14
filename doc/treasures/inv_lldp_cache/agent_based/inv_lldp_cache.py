#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
#
# License: GNU General Public License v2
#
# Author: thl-cmk[at]outlook[dot]com
# URL   : https://thl-cmk.hopto.org
# Date  : 2016-04-16
#
# inventory of lldp cache
#
# 2016-05-24: fix for empty capabilities
# 2017-07-03: fixed neighbour port id as MAC address (HPE)
# 2018-01-24: added local interface, removed 'useless' oid's
# 2018-09-04: changes for CMK 1.5.x (inv_tree --> inv_tree_list)
# 2019-03-04: changes for CMK 1.5.x --> if CMK1.5.x capability information is changed to string
# 2020-07-31: added short interface name, code cleanup
# 2021-03-17: rewrite for CMK 2.0
# 2001-03-18: removed disable option from WATO
# 2021-03-22: workaround for oid_end != x.ifIndex.y  (for Cisco UCS FIs / lbarbier[at]arkane-studios[dot]com)
# 2021-03-22: added handling of lldpchassisidsubtype 5 -> network address ipv4/ipv6
# 2021-07-10: made use short interface names configurable via wato
# 2021-07-19: fix for default parameters
# 2021-07-25: fix local_port --> local_port_num
# 2023-01-19: fix using wrong local interface id, switched from IF-MIB::ifName to LLDP-MIB::lldpLocPortId
# 2023-02-16: replaced TypedDic (Neighbour) with Dict, removed Dataclass --> wasn't working in CMK 2.1
# 2023-02-17: moved wato/metrics from ~/local/share/.. to ~/local/lib/... for CMK2.1
# 2023-10-13: refactoring: render ipv4/ipv6/mac address
#             fixed handling sub types for chassis and ports
# 2023-12-21: streamlined LLDP and CDP inventory
# 2024-03-20: added host label nvdct/has_lldp_neighbours:yes if the device has at least one lldp neighbour
# 2024-04-05: drop neighbours without chassis id
#             drop invalid MAC addresses (length != 6)
# 2024-04-07: fixed missing/empty lldp_global in snmp data  (ThX bitwiz@forum.checkmk.com)
#             improved validation if SNMP input data
#             fix crash on empty neighbour_name
# 2024-04-08: stop (early) if interface table can not be created
#             refactoring _render_capabilities
# 2024-04-14: refactoring (match/case), replace hex() by f'{x:02x}', replace (%s) % s by f'{s}'
# 2024-07-09: extended render_mac_address for 00:1A:E8:BC:F8:49, 00-1A-E8-BC-F8-49, 001A.E8BC.F849, 001AE8BCF849
# 2024-07-10: added local sys description, capabilities supported/enabled
# 2024-07-24: made mac address validation more precise
# 2024-07-25: added support for Fortinet port aggregations -> see inline note
#             added MAC address format aabbcc-ddeeff
# 2024-12-06: fixed crash on empty lldp global data
# 2024-12-14: recreate missing local interface info on fortinet switches
# 2024-12-26: added option to accept only one neighbour per local port (to avoid duplicate entries from Cisco Nexus and APs)
#             reenabled missing global lldp data
# 2025-03-23: moved to check API 2
# 2025-05-28: remove debug code to be compatible with CMK2.4

from collections.abc import MutableSequence, Sequence
from dataclasses import dataclass
from ipaddress import ip_address
from re import compile as re_compile
from typing import List, Self

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
    all_of,
)

_TIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%m'

_interface_displayhints = {
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

_lldp_chassis_id_sub_type = {
    0: 'n/a',
    1: 'chassis component',
    2: 'interface alias',
    3: 'port component',
    4: 'mac address',
    5: 'network address',
    6: 'interface name',
    7: 'local',
}

_lldp_port_id_sub_type = {
    0: 'n/a',
    1: 'interface alias',
    2: 'port component',
    3: 'mac address',
    4: 'network address',
    5: 'interface name',
    6: 'agent circuit id',
    7: 'local',
}

_lldp_man_addr_if_sub_type = {
    0: 'n/a',
    1: 'unknown',
    2: 'interface index',
    3: 'system port number',
}


@dataclass(frozen=True)
class LldpGlobal:
    id: str | None
    name: str | None
    description: str | None
    cap_supported: str
    cap_enabled: str

    @classmethod
    def parse(cls, lldp_global_info: Sequence[str]) -> Self | None:
        try:
            chassis_id_type, chassis_id, system_name, sys_description, cap_supported, cap_enabled = lldp_global_info[0]
        except (ValueError, IndexError):
            return None
        else:
            return cls(
                id=_render_chassis_id(chassis_id_type, chassis_id),
                name=system_name,
                description=sys_description,
                cap_supported=_render_capabilities(cap_supported),
                cap_enabled=_render_capabilities(cap_enabled)
            )


@dataclass(frozen=True)
class LldpNeighbour:
    capabilities: str
    capabilities_map_supported: str
    local_port: str
    local_port_index: str
    neighbour_address: str
    neighbour_id: str
    neighbour_name: str
    neighbour_port: str
    port_description: str
    system_description: str


@dataclass(frozen=True)
class Lldp:
    lldp_global: LldpGlobal | None
    lldp_neighbours: List[LldpNeighbour]


def _get_short_if_name(ifname: str) -> str | None:
    """
    returns short interface name from long interface name
    ifname: is the long interface name
    :type ifname: str
    """
    if not ifname:
        return ifname
    for ifname_prefix in _interface_displayhints.keys():
        if ifname.lower().startswith(ifname_prefix.lower()):
            ifname_short = _interface_displayhints[ifname_prefix]
            return ifname.lower().replace(ifname_prefix.lower(), ifname_short, 1)
    return ifname


def _get_interface_name(if_type: str, raw_interface: Sequence[int]) -> str:
    match if_type:
        case '3':  # mac address
            return _render_mac_address(raw_interface)
        case '5', '7':
            return _render_networkaddress(raw_interface)
        case _:
            return ''.join(chr(m) for m in raw_interface)


def _render_mac_address(raw_mac_addr: Sequence[int]) -> str | None:
    """
    Returns a MAC Address fromm Sequence of int
    Args:
        raw_mac_addr: Sequence of int, needs to be of length 6, 12, 14 or 17

    Returns:
        MAC-Address as string or None if raw_mac_addr is not a MAC-address

    >>> print(_render_mac_address([99,160,210,120,34,200]))
    '63:A0:D2:78:22:C8'
    >>> print(_render_mac_address([55,56,58,49,56,58,101,99,58,50,101,58,98,97,58,56,97]))
    '78:18:EC:2E:BA:8A'
    >>> print(_render_mac_address([55,56,45,49,56,45,101,99,45,50,101,45,98,97,45,56,97]))
    '78:18:EC:2E:BA:8A'
    >>> print(_render_mac_address([55,56,49,56,46,101,99,50,101,46,98,97,56,97]))
    '78:18:EC:2E:BA:8A'
    """

    # no need for lower cas a-f -> all upper()
    # mac = re_compile('^(([0-9A-F]{2}:){5}[0-9A-F]{2})|(([0-9A-F]{4}[\\.\\-]){2}[0-9A-F]{4})|([0-9A-F]{12})$')
    mac = re_compile(
        '^'                                        # beginning of line
        '(([0-9A-F]{2}:){5}[0-9A-F]{2})'           # aa:bb:cc:dd:ee:ff
        '|(([0-9A-F]{4}[\\.\\-]){2}[0-9A-F]{4})|'  # or aabb-ccdd-eeff or aabb.ccdd.eeff
        '(([0-9A-F]{6}\\-[0-9A-F]{6}))'            # or aabbcc-ddeeff
        '|([0-9A-F]{12})'                          # or aabbccddeeff
        '$'                                        # end of line
    )

    mac_address = ''
    # create mac from byte list
    if len(raw_mac_addr) == 6:
        mac_address = ''.join(f'{m:02x}' for m in raw_mac_addr).upper()
    # 00:1A:E8:BC:F8:49, 00-1A-E8-BC-F8-49, 001A.E8BC.F849, aabbcc-ddeeff, 001AE8BCF849
    if len(raw_mac_addr) in [17, 14, 13, 12]:
        mac_address = ''.join(chr(m) for m in raw_mac_addr).upper()

    if mac.match(mac_address):  # check if valid mac address
        # change to 0-9A-F format only
        mac_address = mac_address.replace(':', '').replace('-', '').replace('.', '')
        # make MAC addr str
        return ':'.join(mac_address[i:i + 2] for i in range(0, 12, 2))


def _render_ipv4_address(bytes_: Sequence[int]):
    return '.'.join(str(m) for m in bytes_)


def _render_ipv6_address(bytes_: Sequence[int]):
    # print(bytes_)
    hex_bytes = [f'{byte:02x}' for byte in bytes_]
    address = ':'.join([''.join([hex_bytes[i], hex_bytes[i + 1]]) for i in range(0, len(hex_bytes), 2)])
    return ip_address(address).compressed


def _render_networkaddress(bytes_: Sequence[int]):
    match bytes_[0]:
        case 1:  # ipv4 address
            return _render_ipv4_address(bytes_[1:])
        case 2:  # ipv6 address
            return _render_ipv6_address(bytes_[1:])
        case _:  # all other
            return ''.join(chr(m) for m in bytes_)


def _render_capabilities(raw_capabilities: str) -> str | None:
    lldp_capabilities = {
        0: '',
        1: 'other',
        2: 'Repeater',
        4: 'Bridge',
        8: 'WLAN AP',
        16: 'Router',
        32: 'Phone',
        64: 'DOCSIS cable device',
        128: 'Station only',
    }
    if len(raw_capabilities) == 0:
        return

    raw_capabilities = int(ord(raw_capabilities[0]))

    capabilities = [
        value for capability, value in lldp_capabilities.items() if lldp_capabilities.get(raw_capabilities & capability)
    ]
    capabilities.sort()
    return ', '.join(capabilities)


def _render_chassis_id(chassis_id_sub_type: str, chassis_id: str) -> str:
    match chassis_id_sub_type:
        case '4':  # mac address
            return _render_mac_address(chassis_id)
        case '5':  # network address
            return _render_networkaddress(chassis_id)
        case _:  # all other
            return ''.join(chr(m) for m in chassis_id)


def parse_inv_lldp_cache(string_table: List[StringByteTable]) -> Lldp | None:
    try:
        lldp_info, if_info, lldp_global, lldp_mgmt_addresses = string_table
    except ValueError:
        return None

    try:
        interfaces = {
            if_index: {'if_sub_type': if_sub_type, 'if_name': if_name}
            for if_index, if_sub_type, if_name in if_info
        }
    except ValueError:
        return None

    try:
        mgmt_addresses = [oid_end for oid_end, lldp_rem_man_addr_if_subtype in lldp_mgmt_addresses]
    except ValueError:
        return None

    neighbours = []
    for entry in lldp_info:
        try:
            oid_end, chassis_id_sub_type, chassis_id, port_id_sub_type, port_id, port_description, \
                neighbour_name, system_description, capabilities_map_supported, cache_capabilities = entry
        except ValueError:
            continue

        chassis_id = _render_chassis_id(chassis_id_sub_type, chassis_id)

        # skip neighbours without chassis id/name
        if not chassis_id and not neighbour_name:
            continue

        neighbour_address = ''
        for mgmt_address in mgmt_addresses:
            if mgmt_address.startswith(oid_end):
                neighbour_address = mgmt_address.replace(oid_end, '', 1).strip('.')
                match neighbour_address.split('.')[0]:
                    case '1':  # ipv4 address
                        neighbour_address = neighbour_address[4:]
                    case '2':  # ipv6 address
                        neighbour_address = _render_ipv6_address([int(k) for k in neighbour_address.split('.')[2:]])
                    case '6':  # mac address
                        neighbour_address = _render_mac_address([int(k) for k in neighbour_address.split('.')[2:]])
                    case '7':  # string
                        neighbour_address = ''.join(chr(int(m)) for m in neighbour_address.split('.')[2:])
                    case _:
                        pass
                break

        try:
            local_if_index = oid_end.split('.')[1]
        except IndexError:
            local_if_index = oid_end.split('.')[0]

        try:
            interface = interfaces[local_if_index]
        except KeyError:
            interface = None

        neighbours.append(LldpNeighbour(
            capabilities=_render_capabilities(cache_capabilities),
            capabilities_map_supported=_render_capabilities(capabilities_map_supported),
            local_port=_get_interface_name(interface['if_sub_type'], interface['if_name']) if interface else None,
            local_port_index=local_if_index,
            neighbour_address=neighbour_address,
            neighbour_id=chassis_id,
            neighbour_name=neighbour_name if neighbour_name else chassis_id,
            neighbour_port=_get_interface_name(port_id_sub_type, port_id),
            port_description=port_description,
            system_description=system_description,
        ))
    return Lldp(
        lldp_global=LldpGlobal.parse(lldp_global),
        lldp_neighbours=neighbours
    )


def host_label_inv_lldp_cache(section: Lldp) -> HostLabelGenerator:
    """
    Labels:
        nvdct/has_lldp_neighbours:
            This label is set to "yes" for all devices with at least one LLDP neighbour
        nvdct/lldo_local_id:
            This label is set to the local LLDP id (chassis id)
    """
    if len(section.lldp_neighbours) > 0:
        yield HostLabel(name="nvdct/has_lldp_neighbours", value="yes")

    # try:
    #     yield HostLabel(name="nvdct/lldp_local_id", value=section.lldp_global.id.replace(':', '_'))
    # except AttributeError:
    #    pass


def inventory_lldp_cache(params, section: Lldp) -> InventoryResult:
    path = ['networking', 'lldp_cache']
    if section.lldp_global:
        yield Attributes(
            path=path,
            inventory_attributes={
                **({"local_id": section.lldp_global.id} if section.lldp_global.id else {}),
                **({"local_name": section.lldp_global.name} if section.lldp_global.name else {}),
                **({"local_description": section.lldp_global.description} if section.lldp_global.description else {}),
                **({"local_cap_supported": section.lldp_global.cap_supported} if section.lldp_global.cap_supported else {}),
                **({"local_cap_enabled": section.lldp_global.cap_enabled} if section.lldp_global.cap_enabled else {}),
            }
        )

    path = path + ['neighbours']
    used_local_port_index: MutableSequence[str] = []

    for neighbour in section.lldp_neighbours:
        if params.get('one_neighbour_per_port') and neighbour.local_port_index in used_local_port_index:
            continue
        used_local_port_index.append(neighbour.local_port_index)

        neighbour_name = neighbour.neighbour_name
        if params.get('remove_domain'):
            if params.get('domain_name', ''):
                neighbour_name = neighbour_name.replace(params.get('domain_name', ''), '')
            else:
                try:
                    neighbour_name = neighbour_name.split('.')[0]
                except AttributeError:
                    pass

        neighbour_port = neighbour.neighbour_port
        local_port = neighbour.local_port
        if params.get('use_short_if_name'):
            neighbour_port = _get_short_if_name(neighbour_port)
            local_port = _get_short_if_name(local_port)

        key_columns = {
            # 'neighbour_id': neighbour.neighbour_id,
            'local_port': local_port,
            'neighbour_name': neighbour_name,
            'neighbour_port': neighbour_port,
        }

        inventory_columns = {}

        for key, value in [
            # ('neighbour_name', neighbour_name),
            ('capabilities', neighbour.capabilities),
            ('capabilities_map_supported', neighbour.capabilities_map_supported),
            ('neighbour_address', neighbour.neighbour_address),
            ('neighbour_id', neighbour.neighbour_id),
            ('port_description', neighbour.port_description),
            ('system_description', neighbour.system_description),
        ]:
            if key not in params.get('removecolumns', []) and value:
                inventory_columns[key] = value

        yield TableRow(
            path=path,
            key_columns=key_columns,
            inventory_columns=inventory_columns
        )


lldp_rem_entry = SNMPTree(
    base='.1.0.8802.1.1.2.1.4.1.1',  # LLDP-MIB::lldpRemEntry
    oids=[
        OIDEnd(),  #
        '4',  # lldpRemChassisIdSubtype
        OIDBytes('5'),  # lldpRemChassisId
        '6',  # lldpRemPortIdSubtype
        OIDBytes('7'),  # lldpRemPortId
        '8',  # lldpRemPortDesc
        '9',  # lldpRemSysName
        '10',  # lldpRemSysDesc
        '11',  # lldpRemSysCapSupported
        '12',  # lldpRemSysCapEnabled
    ]
)

lldp_local_port_entry = SNMPTree(
    base='.1.0.8802.1.1.2.1.3.7.1',  # LLDP-MIB::lldpLocPortEntry
    oids=[
        OIDEnd(),  # interface index
        '2',  # lldpLocPortIdSubtype
        OIDBytes('3'),  # lldpLocPortId
    ]
)

lldp_local_info = SNMPTree(
    base='.1.0.8802.1.1.2.1.3',  # LLDP-MIB::localInfo
    oids=[
        '1',  # lldpLocChassisIdSubtype
        OIDBytes('2'),  # lldpLocChassisId
        '3',  # lldpLocSysName
        '4',  # lldpLocSysDesc
        '5',  # lldpLocSysCapSupported
        '6',  # lldpLocSysCapEnabled
    ]
)

lldp_rem_man_addr_entry = SNMPTree(
    base='.1.0.8802.1.1.2.1.4.2.1',  # LLDP-MIB::lldpRemManAddrEntry
    oids=[
        OIDEnd(),  # type.length.address
        # '1',  # lldpRemManAddrSubtype
        # OIDBytes('2'),  # lldpRemManAddr
        '3',  # lldpRemManAddrIfSubtype
    ]
)

snmp_section_inv_lldp_cache = SNMPSection(
    name='inv_lldp_cache',
    # parsed_section_name='inv_lldp_cache',
    host_label_function=host_label_inv_lldp_cache,
    parse_function=parse_inv_lldp_cache,
    fetch=[
        lldp_rem_entry,
        lldp_local_port_entry,
        lldp_local_info,
        lldp_rem_man_addr_entry,
    ],
    detect=exists('.1.0.8802.1.1.2.1.4.1.1.4.*'),  #
)

inventory_plugin_inv_lldp_cache = InventoryPlugin(
    name='inv_lldp_cache',
    inventory_function=inventory_lldp_cache,
    inventory_default_parameters={},
    inventory_ruleset_name='inv_lldp_cache',
)


#
# tweak for fortinet port aggregation
#
# the correct local port might be wrong, as we only know what ports in an aggregation but
# not what port is exactly connected to which port (can be any on from the list of ports) :-(
#

def parse_inv_lldp_cache_fortinet(string_table: List[StringByteTable]) -> Lldp | None:
    try:
        lldp_info, if_info, lldp_global, lldp_mgmt_addresses, if_name, trunk_member = string_table
    except ValueError:
        return None

    map_if_name2idx = {name: idx for idx, name in if_name}
    map_if_idx2name = {idx: name for idx, name in if_name}

    list_trunks = [trunk for trunk in trunk_member[0][0].split('::') if trunk]
    map_trunk2member = {}
    for entry in list_trunks:
        trunk_id, members = entry.split(':')
        members = [port for port in members.split(' ') if port]
        map_trunk2member[trunk_id.strip()] = members

    if not if_info:  # try to recreate missing if_info from if_name and trunk member
        if_info = []
        for index, name  in if_name:
            if name not in map_trunk2member:
                if_info += [[index, '5', [ord(x) for x in name]]]
        for ports in map_trunk2member.values():
            if_info += [[map_if_name2idx[port], '5', [ord(x) for x in port]] for port in ports]

    try:
        interfaces = {
            if_index: {'if_sub_type': if_sub_type, 'if_name': if_name}
            for if_index, if_sub_type, if_name in if_info
        }
    except ValueError:
        return None

    for entry in lldp_info:
        try:
            oid_end, chassis_id_sub_type, chassis_id, port_id_sub_type, port_id, port_description, \
                neighbour_name, system_description, capabilities_map_supported, cache_capabilities = entry
        except ValueError:
            continue

        try:
            local_if_index = oid_end.split('.')[1]
        except IndexError:
            local_if_index = oid_end.split('.')[0]

        try:
            _interface = interfaces[local_if_index]
        except KeyError:
            port = map_trunk2member[map_if_idx2name[local_if_index]][0]
            entry[0] = entry[0].replace(f'.{local_if_index}.', f'.{map_if_name2idx[port]}.')
            map_trunk2member[map_if_idx2name[local_if_index]].remove(port)

    return parse_inv_lldp_cache([lldp_info, if_info, lldp_global, lldp_mgmt_addresses])


inv_if_name = SNMPTree(
    base='.1.3.6.1.2.1.31.1.1.1',  # IF-MIB::ifXTable
    oids=[
        OIDEnd(),  # ifIndex
        '1',  # ifName
    ]
)

fortinet_trunk_member = SNMPTree(
    base='.1.3.6.1.4.1.12356.106.3',  # FORTINET-FORTISWITCH-MIB::fsTrunkMemPrefix
    oids=[
        '1'  # fsTrunkMember
    ]
)

snmp_section_inv_lldp_cache_fortinet = SNMPSection(
    name='inv_lldp_cache_fortinet',
    parsed_section_name='inv_lldp_cache',
    supersedes=['inv_lldp_cache'],
    host_label_function=host_label_inv_lldp_cache,
    parse_function=parse_inv_lldp_cache_fortinet,
    fetch=[
        lldp_rem_entry,
        lldp_local_port_entry,
        lldp_local_info,
        lldp_rem_man_addr_entry,
        inv_if_name,
        fortinet_trunk_member,
    ],
    detect=all_of(
        exists('.1.0.8802.1.1.2.1.4.1.1.4.*'),
        exists('.1.3.6.1.4.1.12356.106.3.1.*'),
        exists('.1.3.6.1.2.1.31.1.1.1.1.*'),
    ),
)
