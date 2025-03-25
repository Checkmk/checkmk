#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Infoblox services and node services"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from cmk.agent_based.v2 import (
    any_of,
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    startswith,
    State,
    StringTable,
)

Section = dict[str, tuple[str, str]]

DETECT_INFOBLOX = any_of(
    contains(".1.3.6.1.2.1.1.1.0", "infoblox"),
    startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.7779.1."),
)

SERVICE_ID_lower_v9 = {
    "1": "dhcp",
    "2": "dns",
    "3": "ntp",
    "4": "tftp",
    "5": "http-file-dist",
    "6": "ftp",
    "7": "bloxtools-move",
    "8": "bloxtools",
    "9": "node-status",
    "10": "disk-usage",
    "11": "enet-lan",
    "12": "enet-lan2",
    "13": "enet-ha",
    "14": "enet-mgmt",
    "15": "lcd",
    "16": "memory",
    "17": "replication",
    "18": "db-object",
    "19": "raid-summary",
    "20": "raid-disk1",
    "21": "raid-disk2",
    "22": "raid-disk3",
    "23": "raid-disk4",
    "24": "raid-disk5",
    "25": "raid-disk6",
    "26": "raid-disk7",
    "27": "raid-disk8",
    "28": "fan1",
    "29": "fan2",
    "30": "fan3",
    "31": "fan4",
    "32": "fan5",
    "33": "fan6",
    "34": "fan7",
    "35": "fan8",
    "36": "power-supply1",
    "37": "power-supply2",
    "38": "ntp-sync",
    "39": "cpu1-temp",
    "40": "cpu2-temp",
    "41": "sys-temp",
    "42": "raid-battery",
    "43": "cpu-usage",
    "44": "ospf",
    "45": "bgp",
    "46": "mgm-service",
    "47": "subgrid-conn",
    "48": "network-capacity",
    "49": "reporting",
    "50": "dns-cache-acceleration",
    "51": "ospf6",
    "52": "swap-usage",
    "53": "discovery-consolidator",
    "54": "discovery-collector",
    "55": "discovery-capacity",
    "56": "threat-protection",
    "57": "cloud-api",
    "58": "threat-analytics",
    "59": "taxii",
    "60": "bfd",
    "61": "outbound",
}
SERVICE_ID_v9 = {
    "1": "dhcp",
    "2": "dns",
    "3": "ntp",
    "4": "tftp",
    "5": "http-file-dist",
    "6": "ftp",
    "7": "node-status",
    "8": "disk-usage",
    "9": "enet-lan",
    "10": "enet-lan2",
    "11": "enet-ha",
    "12": "enet-mgmt",
    "13": "lcd",
    "14": "memory",
    "15": "replication",
    "16": "db-object",
    "17": "raid-summary",
    "18": "raid-disk1",
    "19": "raid-disk2",
    "20": "raid-disk3",
    "21": "raid-disk4",
    "22": "raid-disk5",
    "23": "raid-disk6",
    "24": "raid-disk7",
    "25": "raid-disk8",
    "26": "fan1",
    "27": "fan2",
    "28": "fan3",
    "29": "fan4",
    "30": "fan5",
    "31": "fan6",
    "32": "fan7",
    "33": "fan8",
    "34": "power-supply1",
    "35": "power-supply2",
    "36": "ntp-sync",
    "37": "cpu1-temp",
    "38": "cpu2-temp",
    "39": "sys-temp",
    "40": "raid-battery",
    "41": "cpu-usage",
    "42": "ospf",
    "43": "bgp",
    "44": "mgm-service",
    "45": "subgrid-conn",
    "46": "network-capacity",
    "47": "reporting",
    "48": "dns-cache-acceleration",
    "49": "ospf6",
    "50": "swap-usage",
    "51": "discovery-consolidator",
    "52": "discovery-collector",
    "53": "discovery-capacity",
    "54": "threat-protection",
    "55": "cloud-api",
    "56": "threat-analytics",
    "57": "taxii",
    "58": "bfd",
    "59": "outbound",
}
STATUS_ID = {
    "1": "working",
    "2": "warning",
    "3": "failed",
    "4": "inactive",
    "5": "unknown",
}
STATE = {
    "working": State.OK,
    "warning": State.WARN,
    "failed": State.CRIT,
    "unexpected": State.UNKNOWN,
}


@dataclass(frozen=True)
class _Version:
    major: int
    minor: int
    patch: int


def _parse_version(raw_version: Sequence[Sequence[str]]) -> _Version | None:
    try:
        version = raw_version[0][0]
    except IndexError:
        return None
    parts = version.split("-")[0].split(".")
    try:
        return _Version(int(parts[0]), int(parts[1]), int(parts[2]))
    except (IndexError, ValueError):
        return None


def _find_service_id_map(version: _Version | None) -> Mapping[str, str]:
    # See:
    # - https://docs.infoblox.com/space/nios85/35418019/SNMP+MIB+Hierarchy ff.
    # - https://docs.infoblox.com/space/nios90/280760493/SNMP+MIB+Hierarchy
    if not version:
        return SERVICE_ID_lower_v9
    return SERVICE_ID_v9 if version.major >= 9 else SERVICE_ID_lower_v9


def parse_infoblox_services(string_table: Sequence[StringTable]) -> Section:
    raw_version, table = string_table
    service_id_map = _find_service_id_map(_parse_version(raw_version))
    return {
        service_id_map[service_id]: (status, description)
        for service_id, status_id, description in table
        for status in (STATUS_ID.get(status_id, "unexpected"),)
        if status not in {"inactive", "unknown"}
    }


def discovery_infoblox_services(section: Section) -> DiscoveryResult:
    """
    >>> for result in discovery_infoblox_services({
    ...         'node-status': ('working', 'Running'),
    ...         'discovery-capacity': ('working', '0% - Discovery capacity usage is OK.'),
    ... }):
    ...     print(result)
    Service(item='node-status')
    Service(item='discovery-capacity')
    """
    yield from (Service(item=item) for item in section)


def check_infoblox_services(item: str, section: Section) -> CheckResult:
    """
    >>> for result in check_infoblox_services("memory", {
    ...         'node-status': ('working', 'Running'),
    ...         'memory': ('working', '14% - System memory usage is OK.'),
    ...         'discovery-capacity': ('working', '0% - Discovery capacity usage is OK.'),
    ... }):
    ...     print(result)
    Result(state=<State.OK: 0>, summary='Status: working (14% - System memory usage is OK.)')
    """
    if item not in section:
        return
    status, description = section[item]
    yield Result(
        state=STATE[status],
        summary="Status: {}{}".format(status, description and " (%s)" % description),
    )


snmp_section_infoblox_services = SNMPSection(
    name="infoblox_services",
    detect=DETECT_INFOBLOX,
    parse_function=parse_infoblox_services,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.7779.3.1.1.2.1",
            oids=[
                "7",  # IB-PLATFORMONE-MIB::ibNiosVersion
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.7779.3.1.1.2.1.9.1",
            oids=[
                "1",  # IB-PLATFORMONE-MIB::ibServiceName
                "2",  # IB-PLATFORMONE-MIB::ibServiceStatus
                "3",  # IB-PLATFORMONE-MIB::ibServiceDesc
            ],
        ),
    ],
)

check_plugin_infoblox_services = CheckPlugin(
    name="infoblox_services",  # name taken from pre-1.7 plug-in
    service_name="Service %s",
    discovery_function=discovery_infoblox_services,
    check_function=check_infoblox_services,
)


snmp_section_infoblox_node_services = SNMPSection(
    name="infoblox_node_services",
    detect=DETECT_INFOBLOX,
    parse_function=parse_infoblox_services,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.7779.3.1.1.2.1",
            oids=[
                "7",  # IB-PLATFORMONE-MIB::ibNiosVersion
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.7779.3.1.1.2.1.10.1",
            oids=[
                "1",  # IB-PLATFORMONE-MIB::ibNodeServiceName
                "2",  # IB-PLATFORMONE-MIB::ibNodeServiceStatus
                "3",  # IB-PLATFORMONE-MIB::ibNodeServiceDesc
            ],
        ),
    ],
)

check_plugin_infoblox_node_services = CheckPlugin(
    name="infoblox_node_services",  # name taken from pre-1.7 plug-in
    service_name="Node service %s",
    discovery_function=discovery_infoblox_services,
    check_function=check_infoblox_services,
)
