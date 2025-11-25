# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
# Original author: thl-cmk[at]outlook[dot]com

# ToDo: add fallback if there is no if_name to if_description -> if_alias

from binascii import hexlify
from collections.abc import Mapping, Sequence
from ipaddress import AddressValueError, IPv4Address
from re import compile as re_compile
from re import match as re_match

from pydantic import BaseModel

from cmk.agent_based.v2 import (
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

_INTERFACE_DISPLAY_HINTS = {
    "ethernet": "eth",
    "fastethernet": "Fa",
    "gigabitethernet": "Gi",
    "tengigabitethernet": "Te",
    "fortygigabitethernet": "Fo",
    "hundredgigabitethernet": "Hu",
    "port-channel": "Po",
    "tunnel": "Tu",
    "loopback": "Lo",
    "cellular": "Cel",
    "vlan": "Vlan",
    "management": "Ma",
}


class CdpGlobal(BaseModel, frozen=True):
    enabled: str | None
    hold_time: int | None
    local_id: str | None
    message_interval: int | None


class CdpNeighbor(BaseModel, frozen=True):
    # key columns
    neighbor_id: str
    neighbor_port: str
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


class Cdp(BaseModel, frozen=True):
    cdp_global: CdpGlobal | None
    cdp_neighbors: Sequence[CdpNeighbor]


def _get_short_if_name(if_name: str) -> str:
    """
    returns short interface name from long interface name
    if_name: is the long interface name
    :type if_name: str
    """

    for if_name_prefix in _INTERFACE_DISPLAY_HINTS.keys():  # noqa: PLC0206
        if if_name.lower().startswith(if_name_prefix.lower()):
            if_name_short = _INTERFACE_DISPLAY_HINTS[if_name_prefix]
            return if_name.lower().replace(if_name_prefix.lower(), if_name_short, 1)
    return if_name


def _get_cdp_duplex(st: str) -> str | None:
    names = {
        "0": "N/A",
        "1": "unknown",
        "2": "half duplex",
        "3": "full duplex",
    }
    return names.get(st)


def _render_ip_address(bytestring: str) -> str | None:
    if len(bytestring) == 14:  # "0A 0D FC 15 "  -> some Nexus
        ip_parts = bytestring.strip('"').strip(" ").split(" ")
        if len(ip_parts) == 4:
            ip_address = ".".join([f"{int(m, 16)}" for m in ip_parts])
        else:
            ip_address = ".".join([f"{ord(m)}" for m in bytestring])
    else:
        ip_address = ".".join([f"{ord(m)}" for m in bytestring])
    try:
        return IPv4Address(ip_address).exploded
    except AddressValueError:
        # maybe I let it crash here on purpose with bad data
        pass
    return None


def _render_mac_address(bytestring: str) -> str | None:
    if mac_address := _sanitize_mac("".join([f"{ord(m):02x}" for m in bytestring])):
        return mac_address
    # try encode().hex()
    if mac_address := _sanitize_mac(bytestring.encode().hex()):
        return mac_address

    return None


def _sanitize_mac(mac: str) -> str | None:
    """Sanitize and normalize a MAC address to the format AA:BB:CC:DD:EE:FF.

    Accepts MAC addresses in multiple formats (case-insensitive):
    - aa:bb:cc:dd:ee:ff (colon-separated pairs)
    - aabb-ccdd-eeff (dash-separated pairs)
    - aabb.ccdd.eeff (dot-separated pairs)
    - aabbcc-ddeeff (dash-separated triplets)
    - aabbccddeeff (no separators)

    Args:
        mac: A MAC address string in one of the supported formats.

    Returns:
        A normalized MAC address string in the format AA:BB:CC:DD:EE:FF if the input
        is valid, otherwise None.

    Examples:
        >>> _sanitize_mac("aa:bb:cc:dd:ee:ff")
        'AA:BB:CC:DD:EE:FF'

        >>> _sanitize_mac("aabb-ccdd-eeff")
        'AA:BB:CC:DD:EE:FF'

        >>> _sanitize_mac("aabb.ccdd.eeff")
        'AA:BB:CC:DD:EE:FF'

        >>> _sanitize_mac("aabbcc-ddeeff")
        'AA:BB:CC:DD:EE:FF'

        >>> _sanitize_mac("aabbccddeeff")
        'AA:BB:CC:DD:EE:FF'

        >>> _sanitize_mac("AA:BB:CC:DD:EE:FF")
        'AA:BB:CC:DD:EE:FF'

        >>> _sanitize_mac("invalid") is None
        True

        >>> _sanitize_mac("aa:bb:cc:dd:ee") is None
        True
    """
    re_mac_pattern = (
        "^"  # beginning of line
        "(([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2})"  # aa:bb:cc:dd:ee:ff
        "|(([0-9a-fA-F]{4}[\\.\\-]){2}[0-9a-fA-F]{4})|"  # or aabb-ccdd-eeff
        "(([0-9a-fA-F]{6}\\-[0-9a-fA-F]{6}))"  # or aabbcc-ddeeff
        "|([0-9a-fA-F]{12})"  # or aabbccddeeff
        "$"  # end of line
    )
    compiled_re = re_compile(re_mac_pattern)
    if re_match(compiled_re, mac):
        temp = mac.replace(":", "").replace("-", "").replace(".", "").upper()
        temp = ":".join([temp[i] + temp[i + 1] for i in range(0, 12, 2)])
        return temp

    return None


def _get_capabilities(
    raw_capabilities: str | list[int],
) -> str | None:
    cdp_capabilities = {
        0: "",
        1: "L3",  # router
        2: "TB",  # transparent bridge
        4: "SB",  # source route bridge
        8: "L2",  # switch
        16: "Host",
        32: "IGMP",  # IGMP snooping
        64: "Repeater",
        128: "Phone",  #
        256: "Remote",  #
        512: "CVTA",  #
        1024: "Two-port Mac Relay",  #
    }

    try:
        if isinstance(raw_capabilities, str):
            s = raw_capabilities.strip()
            s_clean = s.replace(" ", "").replace(":", "").replace("-", "").replace(".", "")
            try:
                bytes_data = bytes.fromhex(s_clean)
            except ValueError:
                bytes_data = s.encode("latin-1")
        else:
            bytes_data = bytes(raw_capabilities)
    except Exception:
        return None

    byte_string = hexlify(bytes_data)
    try:
        raw_int = int(byte_string, 16)
    except ValueError:
        return None

    capabilities = [
        value
        for capability, value in cdp_capabilities.items()
        if capability != 0 and (raw_int & capability)
    ]
    if capabilities:
        capabilities.sort()
        return ", ".join(capabilities)

    return None


def _is_ascii(str_to_test: str) -> bool:
    try:
        _test = str_to_test.encode().decode("ascii")
    except UnicodeDecodeError:
        return False
    return True


def _get_address(address_type: str, raw_address: str) -> str | None:
    match address_type:
        case "1":  # ip address
            if (address := _render_ip_address(raw_address)) is not None:
                return address
        case "65535":  # unknown (HPE stack MAC address)
            if (address := _render_mac_address(raw_address)) is not None:
                return address
        case _:
            # maybe I let it crash on purpose with bad data
            pass
    return None


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
    """Parses CDP cache from SNMP string table"""
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
            "0": "no",
            "1": "yes",
        }

        global_info = CdpGlobal(
            enabled=_cdp_run.get(str(cdp_run)),
            message_interval=int(str(cdp_message_interval))
            if str(cdp_message_interval).isdigit()
            else None,
            hold_time=int(str(cdp_hold_time)) if str(cdp_hold_time).isdigit() else None,
            local_id=str(local_device_id) if local_device_id else None,
        )

    neighbors = []

    for entry in cdp_info:
        try:
            (
                oid_end,
                address_type,
                address,
                platform_details,
                device_id,
                device_port,
                platform,
                capabilities,
                vtp_mgmt_domain,
                native_vlan,
                duplex,
                power_consumption,
            ) = entry
        except ValueError:
            continue

        # skip neighbour if one of the key columns is None
        if not (neighbor_id := _get_device_id(str(device_id))):
            continue
        if not (neighbor_port := _get_device_port(str(device_port))):
            continue
        if_index = str(oid_end).split(".")[0]
        if not (local_port := interface_by_index.get(if_index, if_index)):
            continue

        neighbors.append(
            CdpNeighbor(
                address=_get_address(str(address_type), str(address)),
                platform_details=str(platform_details) if platform_details else None,
                neighbor_id=neighbor_id,
                neighbor_port=neighbor_port,
                local_port=str(local_port),
                platform=str(platform) if platform else None,
                capabilities=_get_capabilities(capabilities),
                vtp_mgmt_domain=str(vtp_mgmt_domain) if vtp_mgmt_domain else None,
                native_vlan=str(native_vlan) if str(native_vlan) else None,
                duplex=_get_cdp_duplex(str(duplex)),
                power_consumption=str(power_consumption) if str(power_consumption) else None,
            )
        )

    return Cdp(cdp_global=global_info, cdp_neighbors=neighbors)


def host_label_inv_cdp_cache(section: Cdp) -> HostLabelGenerator:
    """Generates host labels for CDP cache

    Labels:

        cmk/has_cdp_neighbors:
            This label is set to "yes" if the device has any CDP neighbors.

    """
    if section.cdp_neighbors:
        yield HostLabel(name="cmk/has_cdp_neighbors", value="yes")


def inventory_cdp_cache(params: Mapping[str, str], section: Cdp) -> InventoryResult:
    """Generates inventory for CDP cache"""
    path = ["networking", "cdp_cache"]

    if section.cdp_global:
        yield Attributes(
            path=path,
            inventory_attributes={
                **({"enabled": section.cdp_global.enabled} if section.cdp_global.enabled else {}),
                **(
                    {"message_interval": section.cdp_global.message_interval}
                    if section.cdp_global.message_interval
                    else {}
                ),
                **(
                    {"hold_time": section.cdp_global.hold_time}
                    if section.cdp_global.hold_time
                    else {}
                ),
                **(
                    {"local_name": section.cdp_global.local_id}
                    if section.cdp_global.local_id
                    else {}
                ),
            },
        )

    path = path + ["neighbours"]
    for neighbor in section.cdp_neighbors:
        neighbor_id = str(neighbor.neighbor_id)
        if params.get("remove_domain"):
            if params.get("domain_name"):
                neighbor_id = neighbor_id.replace(params["domain_name"], "")
            else:
                neighbor_id = neighbor_id.split(".")[0]

        neighbor_port = neighbor.neighbor_port
        local_port = neighbor.local_port
        if params.get("use_short_if_name"):
            neighbor_port = _get_short_if_name(neighbor_port)
            local_port = _get_short_if_name(local_port)

        key_columns = {
            "neighbour_name": neighbor_id,
            "neighbour_port": neighbor_port,
            "local_port": local_port,
        }

        inventory_columns = {}
        for key, value in [
            ("neighbour_address", neighbor.address),
            ("platform_details", neighbor.platform_details),
            ("platform", neighbor.platform),
            ("capabilities", neighbor.capabilities),
            ("vtp_mgmt_domain", neighbor.vtp_mgmt_domain),
            ("native_vlan", neighbor.native_vlan),
            ("duplex", neighbor.duplex),
            ("power_consumption", neighbor.power_consumption),
        ]:
            if key not in params.get("removecolumns", []) and value is not None:
                inventory_columns[key] = value

        yield TableRow(
            path=path,
            key_columns=key_columns,
            inventory_columns=inventory_columns,
        )


snmp_section_inv_cdp_cache = SNMPSection(
    name="inv_cdp_cache",
    parse_function=parse_inv_cdp_cache,
    host_label_function=host_label_inv_cdp_cache,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.9.9.23.1.2.1.1",  # CISCO-CDP-MIB::cdpCacheEntry
            oids=[
                OIDEnd(),  # ifIndex.neighbour-index-on-interface
                "3",  # cdpCacheAddressType
                "4",  # cdpCacheAddress
                "5",  # cdpCacheVersion   # is not version but platform details
                "6",  # cdpCacheDeviceId
                "7",  # cdpCacheDevicePort
                "8",  # cdpCachePlatform
                OIDBytes("9"),  # cdpCacheCapabilities
                "10",  # cdpCacheVTPMgmtDomain
                "11",  # cdpCacheNativeVLAN
                "12",  # cdpCacheDuplex
                "15",  # cdpCachePowerConsumption
                # '24',  # cdpCacheLastChange
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.9.9.23.1.3",  # CISCO-CDP-MIB::cdpGlobal
            oids=[
                "1",  # cdpGlobalRun
                "2",  # cdpGlobalMessageInterval
                "3",  # cdpGlobalHoldTime
                "4",  # cdpGlobalDeviceId
                # '5',  # cdpGlobalLastChange
                # '6',  # cdpGlobalDeviceIdFormatCpb
                # '7',  # cdpGlobalDeviceIdFormat
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.2.1.31.1.1.1",  # IF-MIB::ifXEntry
            oids=[
                OIDEnd(),  # ifIndex
                "1",  # ifName
            ],
        ),
    ],
    detect=exists(".1.3.6.1.4.1.9.9.23.1.2.1.1.*"),  # CISCO-CDP-MIB::cdpCacheEntry
)

inventory_plugin_inv_cdp_cache = InventoryPlugin(
    name="inv_cdp_cache",
    inventory_function=inventory_cdp_cache,
    inventory_default_parameters={},
    inventory_ruleset_name="inv_cdp_cache",
)
