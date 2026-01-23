# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
# Original author: thl-cmk[at]outlook[dot]com


from collections.abc import MutableSequence, Sequence
from ipaddress import ip_address
from re import compile as re_compile
from typing import NotRequired, Self, TypedDict

from pydantic import BaseModel

from cmk.agent_based.v2 import (
    all_of,
    Attributes,
    exists,
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
)
from cmk.plugins.network.agent_based.lib import DETECT_FORTINET, get_short_if_name


class InventoryParams(TypedDict):
    remove_domain: NotRequired[bool]
    domain_name: NotRequired[str]
    use_short_if_name: NotRequired[bool]
    remove_columns: NotRequired[Sequence[str]]


class LldpGlobal(BaseModel, frozen=True):
    id: str | None
    name: str | None
    description: str | None
    cap_supported: str | None
    cap_enabled: str | None

    @classmethod
    def parse(cls, lldp_global_info: list[list[str | list[int]]]) -> Self | None:
        try:
            (
                chassis_id_type,
                chassis_id,
                system_name,
                sys_description,
                cap_supported,
                cap_enabled,
            ) = lldp_global_info[0]
        except (ValueError, IndexError):
            return None
        else:
            return cls(
                id=_render_chassis_id(str(chassis_id_type), chassis_id),
                name=str(system_name),
                description=str(sys_description),
                cap_supported=_render_capabilities(cap_supported),
                cap_enabled=_render_capabilities(cap_enabled),
            )


class LldpNeighbor(BaseModel, frozen=True):
    capabilities: str | None
    capabilities_map_supported: str | None
    local_port: str | None
    local_port_index: str
    neighbor_address: str
    neighbor_id: str | None
    neighbor_name: str
    neighbor_port: str
    port_description: str
    system_description: str


class Lldp(BaseModel, frozen=True):
    lldp_global: LldpGlobal | None
    lldp_neighbors: list[LldpNeighbor]


def _get_interface_name(if_type: str, raw_interface: Sequence[int] | str) -> str | None:
    if isinstance(raw_interface, str):
        raw_interface = [ord(c) for c in raw_interface]
    match if_type:
        case "3":  # mac address
            return _render_mac_address(raw_interface)
        case "5" | "7":
            return _render_networkaddress(raw_interface)
        case _:
            return "".join(chr(m) for m in raw_interface)


def _render_mac_address(raw_mac_addr: Sequence[int]) -> str | None:
    """
    Returns a MAC Address from Sequence of int
    Args:
        raw_mac_addr: Sequence of int, needs to be of length 6, 12, 14 or 17
    Returns:
        MAC-Address as string or None if raw_mac_addr is not a MAC-address
    >>> _render_mac_address([99,160,210,120,34,200])
    '63:A0:D2:78:22:C8'
    >>> _render_mac_address([55,56,58,49,56,58,101,99,58,50,101,58,98,97,58,56,97])
    '78:18:EC:2E:BA:8A'
    >>> _render_mac_address([55,56,49,56,46,101,99,50,101,46,98,97,56,97])
    '78:18:EC:2E:BA:8A'
    """

    mac = re_compile(
        "^"  # beginning of line
        "(([0-9A-F]{2}:){5}[0-9A-F]{2})"  # aa:bb:cc:dd:ee:ff
        "|(([0-9A-F]{4}[\\.\\-]){2}[0-9A-F]{4})|"  # or aabb-ccdd-eeff or aabb.ccdd.eeff
        "(([0-9A-F]{6}\\-[0-9A-F]{6}))"  # or aabbcc-ddeeff
        "|([0-9A-F]{12})"  # or aabbccddeeff
        "$"  # end of line
    )

    mac_address = ""
    # create mac from byte list
    if len(raw_mac_addr) == 6:
        mac_address = "".join(f"{m:02x}" for m in raw_mac_addr).upper()
    # 00:1A:E8:BC:F8:49, 00-1A-E8-BC-F8-49, 001A.E8BC.F849, aabbcc-ddeeff, 001AE8BCF849
    if len(raw_mac_addr) in [17, 14, 13, 12]:
        mac_address = "".join(chr(m) for m in raw_mac_addr).upper()

    if mac.match(mac_address):  # check if valid mac address
        # change to 0-9A-F format only
        mac_address = mac_address.replace(":", "").replace("-", "").replace(".", "")
        # make MAC addr str
        return ":".join(mac_address[i : i + 2] for i in range(0, 12, 2))

    return None


def _render_ipv4_address(bytes_: Sequence[int]) -> str:
    return ".".join(str(m) for m in bytes_)


def _render_ipv6_address(bytes_: Sequence[int]) -> str:
    # print(bytes_)
    hex_bytes = [f"{byte:02x}" for byte in bytes_]
    address = ":".join(
        ["".join([hex_bytes[i], hex_bytes[i + 1]]) for i in range(0, len(hex_bytes), 2)]
    )
    return ip_address(address).compressed


def _render_networkaddress(bytes_: Sequence[int]) -> str:
    match bytes_[0]:
        case 1:  # ipv4 address
            return _render_ipv4_address(bytes_[1:])
        case 2:  # ipv6 address
            return _render_ipv6_address(bytes_[1:])
        case _:  # all other
            return "".join(chr(m) for m in bytes_)


def _render_capabilities(raw_capabilities: str | list[int]) -> str | None:
    lldp_capabilities = {
        0: "",
        1: "other",
        2: "Repeater",
        4: "Bridge",
        8: "WLAN AP",
        16: "Router",
        32: "Phone",
        64: "DOCSIS cable device",
        128: "Station only",
    }
    if not raw_capabilities or len(raw_capabilities) == 0:
        return None

    raw_cap_value = 0
    if isinstance(raw_capabilities, str):
        # Use ord on the first character if it's a string
        raw_cap_value = ord(raw_capabilities[0])
    elif isinstance(raw_capabilities[0], int):
        # Use the first int directly if it's a list of ints
        raw_cap_value = raw_capabilities[0]

    capabilities = [
        value
        for capability, value in lldp_capabilities.items()
        if value and (raw_cap_value & capability)
    ]
    capabilities.sort()
    return ", ".join(capabilities)


def _render_chassis_id(chassis_id_sub_type: str, chassis_id: list[int] | str) -> str | None:
    if isinstance(chassis_id, str):
        return None

    match chassis_id_sub_type:
        case "4" | "7":  # mac address
            return _render_mac_address(chassis_id)
        case "5":  # network address
            return _render_networkaddress(chassis_id)
        case _:  # all other
            return "".join(chr(m) for m in chassis_id)


def parse_lldp_cache(string_table: Sequence[StringByteTable]) -> Lldp | None:
    try:
        lldp_info, if_info, lldp_global, lldp_mgmt_addresses = string_table
    except ValueError:
        return None

    try:
        interfaces = {
            if_index: {"if_sub_type": if_sub_type, "if_name": if_name}
            for if_index, if_sub_type, if_name in if_info
        }
    except ValueError:
        return None

    try:
        mgmt_addresses = [oid_end for oid_end, lldp_rem_man_addr_if_subtype in lldp_mgmt_addresses]
    except ValueError:
        return None

    neighbors = []
    for entry in lldp_info:
        try:
            (
                oid_end,
                chassis_id_sub_type,
                chassis_id_raw,
                port_id_sub_type,
                port_id,
                port_description,
                neighbor_name,
                system_description,
                capabilities_map_supported,
                cache_capabilities,
            ) = entry
        except ValueError:
            continue

        chassis_id = _render_chassis_id(str(chassis_id_sub_type), chassis_id_raw)

        # skip neighbors without chassis id/name
        if not chassis_id and not neighbor_name:
            continue

        neighbor_address = ""
        for mgmt_address in mgmt_addresses:
            if str(mgmt_address).startswith(str(oid_end)):
                neighbor_address = str(mgmt_address).replace(str(oid_end), "", 1).strip(".")
                match neighbor_address.split(".")[0]:
                    case "1":  # ipv4 address
                        neighbor_address = neighbor_address[4:]
                    case "2":  # ipv6 address
                        neighbor_address = _render_ipv6_address(
                            [int(k) for k in neighbor_address.split(".")[2:]]
                        )
                    case "6":  # mac address
                        mac_addr = _render_mac_address(
                            [int(k) for k in neighbor_address.split(".")[2:]]
                        )
                        neighbor_address = mac_addr or ""
                    case "7":  # string
                        neighbor_address = "".join(
                            chr(int(m)) for m in neighbor_address.split(".")[2:]
                        )
                    case _:
                        pass
                break

        try:
            local_if_index = str(oid_end).split(".")[1]
        except IndexError:
            local_if_index = str(oid_end).split(".")[0]

        try:
            interface = interfaces[local_if_index]
        except KeyError:
            interface = None

        neighbors.append(
            LldpNeighbor(
                capabilities=_render_capabilities(cache_capabilities),
                capabilities_map_supported=_render_capabilities(capabilities_map_supported),
                local_port=_get_interface_name(str(interface["if_sub_type"]), interface["if_name"])
                if interface
                else None,
                local_port_index=local_if_index,
                neighbor_address=neighbor_address,
                neighbor_id=chassis_id,
                neighbor_name=(
                    "".join(chr(m) for m in neighbor_name)
                    if isinstance(neighbor_name, list)
                    else (neighbor_name if neighbor_name else (chassis_id or "unknown"))
                ),
                neighbor_port=_get_interface_name(str(port_id_sub_type), port_id) or "",
                port_description=str(port_description),
                system_description=str(system_description),
            )
        )
    return Lldp(lldp_global=LldpGlobal.parse(lldp_global), lldp_neighbors=neighbors)


def host_label_lldp_cache(section: Lldp) -> HostLabelGenerator:
    """
    Labels:
        cmk/has_lldp_neighbors:
            This label is set to "yes" for all devices with at least one LLDP neighbor
    """
    if len(section.lldp_neighbors) > 0:
        yield HostLabel(name="cmk/has_lldp_neighbors", value="yes")


def inventory_lldp_cache(params: InventoryParams, section: Lldp) -> InventoryResult:
    path = ["networking", "lldp_cache"]
    if section.lldp_global:
        yield Attributes(
            path=path,
            inventory_attributes={
                **({"local_id": section.lldp_global.id} if section.lldp_global.id else {}),
                **({"local_name": section.lldp_global.name} if section.lldp_global.name else {}),
                **(
                    {"local_description": section.lldp_global.description}
                    if section.lldp_global.description
                    else {}
                ),
                **(
                    {"local_cap_supported": section.lldp_global.cap_supported}
                    if section.lldp_global.cap_supported
                    else {}
                ),
                **(
                    {"local_cap_enabled": section.lldp_global.cap_enabled}
                    if section.lldp_global.cap_enabled
                    else {}
                ),
            },
        )

    path = path + ["neighbors"]
    used_local_port_index: MutableSequence[str] = []

    for neighbor in section.lldp_neighbors:
        if (
            params.get("one_neighbor_per_port")
            and neighbor.local_port_index in used_local_port_index
        ):
            continue
        used_local_port_index.append(neighbor.local_port_index)

        neighbor_name = neighbor.neighbor_name
        if params.get("remove_domain"):
            if params.get("domain_name", ""):
                neighbor_name = neighbor_name.replace(params.get("domain_name", ""), "")
            else:
                try:
                    neighbor_name = neighbor_name.split(".")[0]
                except AttributeError:
                    pass

        neighbor_port = neighbor.neighbor_port
        local_port = neighbor.local_port
        if params.get("use_short_if_name"):
            neighbor_port = get_short_if_name(neighbor_port) or neighbor_port
            local_port = get_short_if_name(str(local_port)) or str(local_port)

        key_columns = {
            # 'neighbor_id': neighbor.neighbor_id,
            "local_port": local_port,
            "neighbor_name": neighbor_name,
            "neighbor_port": neighbor_port,
        }

        inventory_columns = {}

        for key, value in [
            # ('neighbor_name', neighbor_name),
            ("capabilities", neighbor.capabilities),
            ("capabilities_map_supported", neighbor.capabilities_map_supported),
            ("neighbor_address", neighbor.neighbor_address),
            ("neighbor_id", neighbor.neighbor_id),
            ("port_description", neighbor.port_description),
            ("system_description", neighbor.system_description),
        ]:
            if key not in params.get("remove_columns", []) and value:
                inventory_columns[key] = value

        yield TableRow(path=path, key_columns=key_columns, inventory_columns=inventory_columns)


lldp_rem_entry = SNMPTree(
    base=".1.0.8802.1.1.2.1.4.1.1",  # LLDP-MIB::lldpRemEntry
    oids=[
        OIDEnd(),  #
        "4",  # lldpRemChassisIdSubtype
        OIDBytes("5"),  # lldpRemChassisId
        "6",  # lldpRemPortIdSubtype
        OIDBytes("7"),  # lldpRemPortId
        "8",  # lldpRemPortDesc
        "9",  # lldpRemSysName
        "10",  # lldpRemSysDesc
        "11",  # lldpRemSysCapSupported
        "12",  # lldpRemSysCapEnabled
    ],
)

lldp_local_port_entry = SNMPTree(
    base=".1.0.8802.1.1.2.1.3.7.1",  # LLDP-MIB::lldpLocPortEntry
    oids=[
        OIDEnd(),  # interface index
        "2",  # lldpLocPortIdSubtype
        OIDBytes("3"),  # lldpLocPortId
    ],
)

lldp_local_info = SNMPTree(
    base=".1.0.8802.1.1.2.1.3",  # LLDP-MIB::localInfo
    oids=[
        "1",  # lldpLocChassisIdSubtype
        OIDBytes("2"),  # lldpLocChassisId
        "3",  # lldpLocSysName
        "4",  # lldpLocSysDesc
        "5",  # lldpLocSysCapSupported
        "6",  # lldpLocSysCapEnabled
    ],
)

lldp_rem_man_addr_entry = SNMPTree(
    base=".1.0.8802.1.1.2.1.4.2.1",  # LLDP-MIB::lldpRemManAddrEntry
    oids=[
        OIDEnd(),  # type.length.address
        # '1',  # lldpRemManAddrSubtype
        # OIDBytes('2'),  # lldpRemManAddr
        "3",  # lldpRemManAddrIfSubtype
    ],
)

snmp_section_inv_lldp_cache = SNMPSection(
    name="inv_lldp_cache",
    # parsed_section_name='inv_lldp_cache',
    host_label_function=host_label_lldp_cache,
    parse_function=parse_lldp_cache,
    fetch=[
        lldp_rem_entry,
        lldp_local_port_entry,
        lldp_local_info,
        lldp_rem_man_addr_entry,
    ],
    detect=exists(".1.0.8802.1.1.2.1.4.1.1.4.*"),  #
)

inventory_plugin_inv_lldp_cache = InventoryPlugin(
    name="inv_lldp_cache",
    inventory_function=inventory_lldp_cache,
    inventory_default_parameters=InventoryParams(),
    inventory_ruleset_name="inv_lldp_cache",
)


def parse_lldp_cache_fortinet(string_table: Sequence[StringByteTable]) -> Lldp | None:
    try:
        lldp_info, if_info, lldp_global, lldp_mgmt_addresses, if_name, trunk_member = string_table
    except ValueError:
        return None

    map_if_name2idx = {name: idx for idx, name in if_name}
    map_if_idx2name = {idx: name for idx, name in if_name}

    if trunk_member:
        list_trunks = [trunk for trunk in str(trunk_member[0][0]).split("::") if trunk]
    else:
        list_trunks = []

    map_trunk2member = {}
    for list_trunk in list_trunks:
        trunk_id, members_str = list_trunk.split(":")
        members = [port for port in members_str.split(" ") if port]
        map_trunk2member[trunk_id.strip()] = members

    if not if_info:  # try to recreate missing if_info from if_name and trunk member
        if_info = []
        for index, name in if_name:
            if name not in map_trunk2member:
                if_info += [[index, "5", [ord(str(x)) for x in name]]]
        for ports in map_trunk2member.values():
            if_info += [[map_if_name2idx[port], "5", [ord(x) for x in port]] for port in ports]

    try:
        interfaces = {
            if_index: {"if_sub_type": if_sub_type, "if_name": if_name}
            for if_index, if_sub_type, if_name in if_info
        }
    except ValueError:
        return None

    for entry in lldp_info:
        try:
            (
                oid_end,
                chassis_id_sub_type,
                chassis_id,
                port_id_sub_type,
                port_id,
                port_description,
                neighbour_name,
                system_description,
                capabilities_map_supported,
                cache_capabilities,
            ) = entry
        except ValueError:
            continue

        try:
            local_if_index = str(oid_end).split(".")[1]
        except IndexError:
            local_if_index = str(oid_end).split(".")[0]

        try:
            _interface = interfaces[str(local_if_index)]
        except KeyError:
            trunk_name = map_if_idx2name[str(local_if_index)]
            port = map_trunk2member[str(trunk_name)][0]
            entry[0] = str(entry[0]).replace(f".{local_if_index}.", f".{map_if_name2idx[port]}.")
            map_trunk2member[str(trunk_name)].remove(port)

    return parse_lldp_cache([lldp_info, if_info, lldp_global, lldp_mgmt_addresses])


inv_if_name = SNMPTree(
    base=".1.3.6.1.2.1.31.1.1.1",  # IF-MIB::ifXTable
    oids=[
        OIDEnd(),  # ifIndex
        "1",  # ifName
    ],
)

fortinet_trunk_member = SNMPTree(
    base=".1.3.6.1.4.1.12356.106.3",  # FORTINET-FORTISWITCH-MIB::fsTrunkMemPrefix
    oids=[
        "1"  # fsTrunkMember
    ],
)

snmp_section_inv_lldp_cache_fortinet = SNMPSection(
    name="inv_lldp_cache_fortinet",
    parsed_section_name="inv_lldp_cache",
    supersedes=["inv_lldp_cache"],
    host_label_function=host_label_lldp_cache,
    parse_function=parse_lldp_cache_fortinet,
    fetch=[
        lldp_rem_entry,
        lldp_local_port_entry,
        lldp_local_info,
        lldp_rem_man_addr_entry,
        inv_if_name,
        fortinet_trunk_member,
    ],
    detect=all_of(
        DETECT_FORTINET,
        exists(".1.0.8802.1.1.2.1.4.1.1.4.*"),
        exists(".1.3.6.1.4.1.12356.106.3.1.*"),
        exists(".1.3.6.1.2.1.31.1.1.1.1.*"),
    ),
)
