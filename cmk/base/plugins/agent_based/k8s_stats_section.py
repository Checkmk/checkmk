#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
from typing import Any, Dict, List

from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable

from .agent_based_api.v1 import register
from .utils.k8s import Filesystem, Interface, Section, to_filesystem, to_interface

###########################################################################
# NOTE: This check (and associated special agent) is deprecated and will be
#       removed in Checkmk version 2.2.
###########################################################################


def parse_k8s(string_table: StringTable) -> Section:
    """Basically we return the JSON parsed input -
    but for easier processing and better type safety we also convert the `network/interface` and
    `filesystem` lists into dicts

    >>> for key, value in parse_k8s([['{'
    ...       '"network": {"tx_dropped": 0, "rx_packets": 573200, '
    ...       '  "interfaces": ['
    ...       '    {"tx_dropped": 0, "rx_packets": 573200, "name": "eth1", "rx_bytes": 371123972, "tx_errors": 0, "tx_bytes": 1358359683, "rx_dropped": 0, "tx_packets": 544397, "rx_errors": 0}, '
    ...       '    {"tx_dropped": 0, "rx_packets": 465930, "name": "eth0", "rx_bytes": 468641826, "tx_errors": 0, "tx_bytes": 11076147, "rx_dropped": 0, "tx_packets": 184527, "rx_errors": 0}, '
    ...       '    {"tx_dropped": 0, "rx_packets": 0, "name": "sit0", "rx_bytes": 0, "tx_errors": 0, "tx_bytes": 0, "rx_dropped": 0, "tx_packets": 0, "rx_errors": 0}], '
    ...       '  "rx_errors": 0, "tx_packets": 544397}, '
    ...       '"filesystem": ['
    ...       '  {"available": 1043775488, "capacity": 1043775488, "io_time": 0, "sectors_read": 0, "writes_completed": 0, "weighted_io_time": 0, '
    ...       '   "inodes_free": 254827, "reads_completed": 0, "read_time": 0, "writes_merged": 0, '
    ...       '   "inodes": 254828, "device": "tmpfs", "sectors_written": 0, "reads_merged": 0, "has_inodes": true, "usage": 0, "write_time": 0, "type": "vfs", "io_in_progress": 0, "base_usage": 0}, '
    ...       '  {"available": 12933038080, "capacity": 17293533184, "io_time": 3353942, "sectors_read": 2393042, '
    ...       '   "writes_completed": 2479813, "weighted_io_time": 4655694, "inodes_free": 9668974, '
    ...       '   "reads_completed": 37680, "read_time": 58206, "writes_merged": 924180, "inodes": 9732096, "device": "/dev/sda1", "sectors_written": 175754080, "reads_merged": 675, "has_inodes": true, '
    ...       '   "usage": 3347623936, "write_time": 4611717, "type": "vfs", "io_in_progress": 0, "base_usage": 0}, '
    ...       '  {"available": 0, "capacity": 0, "io_time": 0, "sectors_read": 0, "writes_completed": 0, '
    ...       '   "weighted_io_time": 0, "inodes_free": 0, "reads_completed": 0, "read_time": 0, "writes_merged": 0, "inodes": 0, "device": "rootfs", "sectors_written": 0, "reads_merged": 0, '
    ...       '   "has_inodes": true, "usage": 0, "write_time": 0, "type": "vfs", "io_in_progress": 0, "base_usage": 0}], '
    ...       '"timestamp": 1553765630.0, '
    ...       '"diskio": {}'
    ... '}']]).items():
    ...   print("%s: %r" % (key, value))
    filesystem: {'tmpfs': [{'capacity': 1043775488, 'available': 1043775488, 'inodes': 254828, 'inodes_free': 254827}], '/dev/sda1': [{'capacity': 17293533184, 'available': 12933038080, 'inodes': 9732096, 'inodes_free': 9668974}], 'rootfs': [{'capacity': 0, 'available': 0, 'inodes': 0, 'inodes_free': 0}]}
    interfaces: {'eth1': [{'rx_packets': 573200, 'tx_packets': 544397, 'rx_errors': 0, 'tx_errors': 0, 'rx_bytes': 371123972, 'tx_bytes': 1358359683, 'rx_dropped': 0, 'tx_dropped': 0}], 'eth0': [{'rx_packets': 465930, 'tx_packets': 184527, 'rx_errors': 0, 'tx_errors': 0, 'rx_bytes': 468641826, 'tx_bytes': 11076147, 'rx_dropped': 0, 'tx_dropped': 0}], 'sit0': [{'rx_packets': 0, 'tx_packets': 0, 'rx_errors': 0, 'tx_errors': 0, 'rx_bytes': 0, 'tx_bytes': 0, 'rx_dropped': 0, 'tx_dropped': 0}]}
    timestamp: 1553765630.0
    """

    def to_interfaces(data: Any) -> Dict[str, List[Interface]]:
        assert isinstance(data, list)
        result: Dict[str, List[Interface]] = {}
        for elem in data:
            result.setdefault(elem["name"], []).append(to_interface(elem))
        return result

    def to_filesystems(data: Any) -> Dict[str, List[Filesystem]]:
        assert isinstance(data, list)
        result: Dict[str, List[Filesystem]] = {}
        for device, fs_data in ((elem["device"], elem) for elem in data):
            result.setdefault(device, []).append(to_filesystem(fs_data))
        return result

    stats_data = json.loads(string_table[0][0])
    return {
        "filesystem": to_filesystems(stats_data.get("filesystem", [])),
        "interfaces": to_interfaces(stats_data.get("network", {}).get("interfaces", [])),
        "timestamp": float(stats_data["timestamp"]),
    }


register.agent_section(
    name="k8s_stats",
    parse_function=parse_k8s,
)
