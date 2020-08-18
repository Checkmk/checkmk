#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
def scan_infoblox(oid):
    return "infoblox" in oid(".1.3.6.1.2.1.1.1.0").lower() or \
           oid(".1.3.6.1.2.1.1.2.0").startswith(".1.3.6.1.4.1.7779.1")

def parse_infoblox_services(info):
    map_service_ids = {
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

    map_status_id = {
        "1": "working",
        "2": "warning",
        "3": "failed",
        "4": "inactive",
        "5": "unknown",
    }

    parsed = {}
    for _node, service_id, status_id, description in info:
        status = map_status_id.get(status_id, "unexpected")
        if status in ["inactive", "unknown"]:
            continue

        service_name = map_service_ids[service_id]
        service_nodes = parsed.setdefault(service_name, [])
        service_nodes.append((status, description))

    return parsed


def inventory_infoblox_services(parsed):
    for service_name in parsed:
        yield service_name, None


def check_infoblox_services(item, _no_params, parsed):
    if item in parsed:
        map_status = {
            "working": 0,
            "warning": 1,
            "failed": 2,
            "unexpected": 3,
        }
        node_data = parsed[item]

        # For a clustered service the best state is used
        min_status, min_descr = node_data[0]
        min_state = map_status[min_status]

        for status, descr in node_data[1:]:
            state = map_status[status]
            if state < min_state:
                min_state, min_status, min_descr = state, status, descr

        infotext = "Status: %s" % min_status
        if min_descr:
            infotext += " (%s)" % min_descr

        return min_state, infotext

# .1.3.6.1.4.1.7779.3.1.1.2.1.9.1.1.1 1 --> IB-PLATFORMONE-MIB::ibServiceName.dhcp
# .1.3.6.1.4.1.7779.3.1.1.2.1.9.1.1.2 2 --> IB-PLATFORMONE-MIB::ibServiceName.dns
# .1.3.6.1.4.1.7779.3.1.1.2.1.9.1.1.3 3 --> IB-PLATFORMONE-MIB::ibServiceName.ntp
# .1.3.6.1.4.1.7779.3.1.1.2.1.9.1.1.4 4 --> IB-PLATFORMONE-MIB::ibServiceName.tftp
# .1.3.6.1.4.1.7779.3.1.1.2.1.9.1.1.5 5 --> IB-PLATFORMONE-MIB::ibServiceName.http-file-dist
# .1.3.6.1.4.1.7779.3.1.1.2.1.9.1.1.6 6 --> IB-PLATFORMONE-MIB::ibServiceName.ftp
# .1.3.6.1.4.1.7779.3.1.1.2.1.9.1.1.7 7 --> IB-PLATFORMONE-MIB::ibServiceName.bloxtools-move
# .1.3.6.1.4.1.7779.3.1.1.2.1.9.1.1.8 8 --> IB-PLATFORMONE-MIB::ibServiceName.bloxtools
# .1.3.6.1.4.1.7779.3.1.1.2.1.9.1.2.1 4 --> IB-PLATFORMONE-MIB::ibServiceStatus.dhcp
# .1.3.6.1.4.1.7779.3.1.1.2.1.9.1.2.2 4 --> IB-PLATFORMONE-MIB::ibServiceStatus.dns
# .1.3.6.1.4.1.7779.3.1.1.2.1.9.1.2.3 1 --> IB-PLATFORMONE-MIB::ibServiceStatus.ntp
# .1.3.6.1.4.1.7779.3.1.1.2.1.9.1.2.4 4 --> IB-PLATFORMONE-MIB::ibServiceStatus.tftp
# .1.3.6.1.4.1.7779.3.1.1.2.1.9.1.2.5 4 --> IB-PLATFORMONE-MIB::ibServiceStatus.http-file-dist
# .1.3.6.1.4.1.7779.3.1.1.2.1.9.1.2.6 4 --> IB-PLATFORMONE-MIB::ibServiceStatus.ftp
# .1.3.6.1.4.1.7779.3.1.1.2.1.9.1.2.7 5 --> IB-PLATFORMONE-MIB::ibServiceStatus.bloxtools-move
# .1.3.6.1.4.1.7779.3.1.1.2.1.9.1.2.8 4 --> IB-PLATFORMONE-MIB::ibServiceStatus.bloxtools
# .1.3.6.1.4.1.7779.3.1.1.2.1.9.1.3.1 DHCP Service is inactive --> IB-PLATFORMONE-MIB::ibServiceDesc.dhcp
# .1.3.6.1.4.1.7779.3.1.1.2.1.9.1.3.2 DNS Service is inactive --> IB-PLATFORMONE-MIB::ibServiceDesc.dns
# .1.3.6.1.4.1.7779.3.1.1.2.1.9.1.3.3 NTP Service is working --> IB-PLATFORMONE-MIB::ibServiceDesc.ntp
# .1.3.6.1.4.1.7779.3.1.1.2.1.9.1.3.4 Hard Disk: 0% - TFTP Service is inactive --> IB-PLATFORMONE-MIB::ibServiceDesc.tftp
# .1.3.6.1.4.1.7779.3.1.1.2.1.9.1.3.5 Hard Disk: 0% - HTTP File Dist Service is inactive --> IB-PLATFORMONE-MIB::ibServiceDesc.http-file-dist
# .1.3.6.1.4.1.7779.3.1.1.2.1.9.1.3.6 Hard Disk: 0% - FTP Service is inactive --> IB-PLATFORMONE-MIB::ibServiceDesc.ftp
# .1.3.6.1.4.1.7779.3.1.1.2.1.9.1.3.7 --> IB-PLATFORMONE-MIB::ibServiceDesc.bloxtools-move
# .1.3.6.1.4.1.7779.3.1.1.2.1.9.1.3.8 CPU: 100%, Memory: 0%, Hard Disk: 0% - --> IB-PLATFORMONE-MIB::ibServiceDesc.bloxtools

check_info['infoblox_services'] = {
    'parse_function': parse_infoblox_services,
    'inventory_function': inventory_infoblox_services,
    'check_function': check_infoblox_services,
    'service_description': 'Service %s',
    'snmp_info': (
        ".1.3.6.1.4.1.7779.3.1.1.2.1.9.1",
        [
            "1",  # IB-PLATFORMONE-MIB::ibServiceName
            "2",  # IB-PLATFORMONE-MIB::ibServiceStatus
            "3",  # IB-PLATFORMONE-MIB::ibServiceDesc
        ]),
    'snmp_scan_function': scan_infoblox,
    'includes': ["infoblox.include"],
    'node_info': True,
}
# .1.3.6.1.4.1.7779.3.1.1.2.1.10.1.1.9 9 --> IB-PLATFORMONE-MIB::ibNodeServiceName.node-status
# .1.3.6.1.4.1.7779.3.1.1.2.1.10.1.1.10 10 --> IB-PLATFORMONE-MIB::ibNodeServiceName.disk-usage
# .1.3.6.1.4.1.7779.3.1.1.2.1.10.1.1.11 11 --> IB-PLATFORMONE-MIB::ibNodeServiceName.enet-lan
# .1.3.6.1.4.1.7779.3.1.1.2.1.10.1.1.12 12 --> IB-PLATFORMONE-MIB::ibNodeServiceName.enet-lan2
# .1.3.6.1.4.1.7779.3.1.1.2.1.10.1.1.13 13 --> IB-PLATFORMONE-MIB::ibNodeServiceName.enet-ha
# .1.3.6.1.4.1.7779.3.1.1.2.1.10.1.1.14 14 --> IB-PLATFORMONE-MIB::ibNodeServiceName.enet-mgmt
# .1.3.6.1.4.1.7779.3.1.1.2.1.10.1.1.15 15 --> IB-PLATFORMONE-MIB::ibNodeServiceName.lcd
# .1.3.6.1.4.1.7779.3.1.1.2.1.10.1.2.9 1 --> IB-PLATFORMONE-MIB::ibNodeServiceStatus.node-status
# .1.3.6.1.4.1.7779.3.1.1.2.1.10.1.2.10 1 --> IB-PLATFORMONE-MIB::ibNodeServiceStatus.disk-usage
# .1.3.6.1.4.1.7779.3.1.1.2.1.10.1.2.11 1 --> IB-PLATFORMONE-MIB::ibNodeServiceStatus.enet-lan
# .1.3.6.1.4.1.7779.3.1.1.2.1.10.1.2.12 5 --> IB-PLATFORMONE-MIB::ibNodeServiceStatus.enet-lan2
# .1.3.6.1.4.1.7779.3.1.1.2.1.10.1.2.13 5 --> IB-PLATFORMONE-MIB::ibNodeServiceStatus.enet-ha
# .1.3.6.1.4.1.7779.3.1.1.2.1.10.1.2.14 1 --> IB-PLATFORMONE-MIB::ibNodeServiceStatus.enet-mgmt
# .1.3.6.1.4.1.7779.3.1.1.2.1.10.1.2.15 5 --> IB-PLATFORMONE-MIB::ibNodeServiceStatus.lcd
# .1.3.6.1.4.1.7779.3.1.1.2.1.10.1.3.9 Running --> IB-PLATFORMONE-MIB::ibNodeServiceDesc.node-status
# .1.3.6.1.4.1.7779.3.1.1.2.1.10.1.3.10 15% - Primary drive usage is OK. --> IB-PLATFORMONE-MIB::ibNodeServiceDesc.disk-usage
# .1.3.6.1.4.1.7779.3.1.1.2.1.10.1.3.11 X.X.X.X --> IB-PLATFORMONE-MIB::ibNodeServiceDesc.enet-lan
# .1.3.6.1.4.1.7779.3.1.1.2.1.10.1.3.12 --> IB-PLATFORMONE-MIB::ibNodeServiceDesc.enet-lan2
# .1.3.6.1.4.1.7779.3.1.1.2.1.10.1.3.13 --> IB-PLATFORMONE-MIB::ibNodeServiceDesc.enet-ha
# .1.3.6.1.4.1.7779.3.1.1.2.1.10.1.3.14 X.X.X.X --> IB-PLATFORMONE-MIB::ibNodeServiceDesc.enet-mgmt
# .1.3.6.1.4.1.7779.3.1.1.2.1.10.1.3.15 --> IB-PLATFORMONE-MIB::ibNodeServiceDesc.lcd
check_info['infoblox_node_services'] = {
    'parse_function': parse_infoblox_services,
    'inventory_function': inventory_infoblox_services,
    'check_function': check_infoblox_services,
    'service_description': 'Node service %s',
    'snmp_info': (
        ".1.3.6.1.4.1.7779.3.1.1.2.1.10.1",
        [
            "1",  # IB-PLATFORMONE-MIB::ibNodeServiceName
            "2",  # IB-PLATFORMONE-MIB::ibNodeServiceStatus
            "3",  # IB-PLATFORMONE-MIB::ibNodeServiceDesc
        ]),
    'snmp_scan_function': scan_infoblox,
    'includes': ["infoblox.include"],
    'node_info': True,
}

"""
