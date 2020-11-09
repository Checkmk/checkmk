#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Infoblox services and node services
"""
from typing import Dict, List, Mapping, Tuple

from .agent_based_api.v1 import (
    SNMPTree,
    register,
    Service,
    Result,
    State as state,
    any_of,
    startswith,
    contains,
)
from .agent_based_api.v1.type_defs import (
    StringTable,
    CheckResult,
    DiscoveryResult,
)
Section = Dict[str, Tuple[str, str]]
OID_sysObjectID = ".1.3.6.1.2.1.1.2.0"

# note: directly migrated from infoblox.include - it's likely that the object id check is sufficient
DETECT_INFOBLOX = any_of(contains(".1.3.6.1.2.1.1.1.0", "infoblox"),
                         startswith(OID_sysObjectID, ".1.3.6.1.4.1.7779.1."))

SERVICE_ID = {
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
}
STATUS_ID = {
    "1": "working",
    "2": "warning",
    "3": "failed",
    "4": "inactive",
    "5": "unknown",
}
STATE = {
    "working": state.OK,
    "warning": state.WARN,
    "failed": state.CRIT,
    "unexpected": state.UNKNOWN,
}


def parse_infoblox_services(string_table: List[StringTable]) -> Section:
    """
    >>> for item, status in parse_infoblox_services([[
    ...         ['9', '1', 'Running'],
    ...         ['10', '1', '2% - Primary drive usage is OK.'],
    ...         ['11', '1', '11.112.133.14'],
    ...         ['27', '5', ''],
    ...         ['28', '1', 'FAN 1: 8725 RPM'],
    ...         ['43', '1', 'CPU Usage: 5%'],
    ...         ['57', '5', 'Cloud API service is inactive.'],
    ...         ]]).items():
    ...     print(item, status)
    node-status ('working', 'Running')
    disk-usage ('working', '2% - Primary drive usage is OK.')
    enet-lan ('working', '11.112.133.14')
    fan1 ('working', 'FAN 1: 8725 RPM')
    cpu-usage ('working', 'CPU Usage: 5%')
    """
    return {
        SERVICE_ID[service_id]: (status, description)
        for service_id, status_id, description in string_table[0]
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
    if not item in section:
        return
    status, description = section[item]
    yield Result(
        state=STATE[status],
        summary="Status: %s%s" % (status, description and " (%s)" % description),
    )


def cluster_check_infoblox_services(item: str, section: Mapping[str, Section]) -> CheckResult:
    """
    >>> for result in cluster_check_infoblox_services("memory", {
    ...     "node1": {
    ...         'memory': ('warning', '54% - System memory usage is LOW.'),
    ...         'replication': ('working', 'Online'),
    ...     }, "node2": {
    ...         'memory': ('working', '14% - System memory usage is OK.'),
    ...         'replication': ('working', 'Online'),
    ...     }, "node3": {
    ...         'memory': ('failed', '74% - System memory usage is CRIT.'),
    ...         'replication': ('working', 'Online'),
    ... }}):
    ...     print(result)
    Result(state=<State.OK: 0>, summary='Status: working (14% - System memory usage is OK.)')
    """
    try:
        status, description = min(
            (node_section[item] for node_section in section.values() if item in node_section),
            key=lambda x: STATE[x[0]].value)
    except ValueError:
        # no node with given item found
        return
    yield Result(
        state=STATE[status],
        summary="Status: %s%s" % (status, description and " (%s)" % description),
    )


register.snmp_section(
    name="infoblox_services",
    detect=DETECT_INFOBLOX,
    parse_function=parse_infoblox_services,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.7779.3.1.1.2.1.9.1",
            oids=[
                "1",  # IB-PLATFORMONE-MIB::ibServiceName
                "2",  # IB-PLATFORMONE-MIB::ibServiceStatus
                "3",  # IB-PLATFORMONE-MIB::ibServiceDesc
            ]),
    ],
)

register.check_plugin(
    name="infoblox_services",  # name taken from pre-1.7 plugin
    service_name="Service %s",
    discovery_function=discovery_infoblox_services,
    check_function=check_infoblox_services,
    cluster_check_function=cluster_check_infoblox_services,
)

register.snmp_section(
    name="infoblox_node_services",
    detect=DETECT_INFOBLOX,
    parse_function=parse_infoblox_services,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.7779.3.1.1.2.1.10.1",
            oids=[
                "1",  # IB-PLATFORMONE-MIB::ibNodeServiceName
                "2",  # IB-PLATFORMONE-MIB::ibNodeServiceStatus
                "3",  # IB-PLATFORMONE-MIB::ibNodeServiceDesc
            ]),
    ],
)

register.check_plugin(
    name="infoblox_node_services",  # name taken from pre-1.7 plugin
    service_name="Node service %s",
    discovery_function=discovery_infoblox_services,
    check_function=check_infoblox_services,
    cluster_check_function=cluster_check_infoblox_services,
)
