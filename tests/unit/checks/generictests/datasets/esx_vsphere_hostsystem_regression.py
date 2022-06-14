#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

from cmk.base.plugins.agent_based.esx_vsphere_hostsystem_section import parse_esx_vsphere_hostsystem

checkname = 'esx_vsphere_hostsystem'

parsed = parse_esx_vsphere_hostsystem([
        [
            u'config.storageDevice.multipathInfo', u'6e843b6d8f2740bdecbad4676da7a9dd',
            u'vmhba66:C0:T2:L0', u'active', u'6e843b6bc5cc897d430ad40b7d9172d1',
            u'vmhba66:C0:T0:L0', u'active', u'6e843b63fcbd92ad8f22d4cf7d8e6cdc',
            u'vmhba66:C0:T1:L0', u'active', u'766d6862', u'vmhba1:C0:T0:L0', u'active',
            u'600605b002db9f7018d0a40c2a1444b0', u'vmhba0:C2:T0:L0', u'active'
        ],
        [u'hardware.biosInfo.biosVersion', u'-[D6E158AUS-1.16]-'],
        [u'hardware.biosInfo.releaseDate', u'2012-11-26T00:00:00Z'],
        [u'hardware.cpuInfo.hz', u'2933437094'],
        [u'hardware.cpuInfo.numCpuCores', u'12'],
        [u'hardware.cpuInfo.numCpuPackages', u'2'],
        [u'hardware.cpuInfo.numCpuThreads', u'24'],
        [u'hardware.cpuPkg.busHz.0', u'133338040'],
        [u'hardware.cpuPkg.busHz.1', u'133338015'],
        [
            u'hardware.cpuPkg.description.0', u'Intel(R)', u'Xeon(R)', u'CPU', u'X5670', u'@',
            u'2.93GHz'
        ],
        [
            u'hardware.cpuPkg.description.1', u'Intel(R)', u'Xeon(R)', u'CPU', u'X5670', u'@',
            u'2.93GHz'
        ],
        [u'hardware.cpuPkg.hz.0', u'2933437152'],
        [u'hardware.cpuPkg.hz.1', u'2933437036'],
        [u'hardware.cpuPkg.index.0', u'0'],
        [u'hardware.cpuPkg.index.1', u'1'],
        [u'hardware.cpuPkg.vendor.0', u'intel'],
        [u'hardware.cpuPkg.vendor.1', u'intel'],
        [u'hardware.memorySize', u'146016378880'],
        [u'hardware.systemInfo.model', u'System', u'x3650', u'M3', u'-[7945M2G]-'],
        [u'hardware.systemInfo.otherIdentifyingInfo.AssetTag.0', u'none'],
        [u'hardware.systemInfo.otherIdentifyingInfo.OemSpecificString.0', u'IBM', u'SystemX'],
        [u'hardware.systemInfo.otherIdentifyingInfo.ServiceTag.0', u'none'],
        [u'hardware.systemInfo.uuid', u'e8a2b8a7-b9d4-3f21-a53a-afca3baa74f2'],
        [u'hardware.systemInfo.vendor', u'IBM'],
        [u'name', u'esx-w.dhcp.mathias-kettner'],
        [u'overallStatus', u'green'],
        [u'runtime.inMaintenanceMode', u'false'],
        [u'runtime.powerState', u'poweredOn'],
        [u'summary.quickStats.overallCpuUsage', u'2946'],
        [u'summary.quickStats.overallMemoryUsage', u'110738'],
    ]
)

discovery = {
    '': [],
    'cpu_usage': [(None, {})],
    'cpu_util_cluster': [],
    'maintenance': [(None, {
        'target_state': 'false'
    })],
    'mem_usage': [(None, 'esx_host_mem_default_levels')],
    'mem_usage_cluster': [],
    'multipath': [
        (u'6e843b6d8f2740bdecbad4676da7a9dd', None),
        (u'6e843b6bc5cc897d430ad40b7d9172d1', None),
        (u'6e843b63fcbd92ad8f22d4cf7d8e6cdc', None),
        (u'766d6862', None),
        (u'600605b002db9f7018d0a40c2a1444b0', None),
    ],
    'state': [(None, None)]
}

checks = {
    'cpu_usage': [(
        None,
        {},
        [(
            0,
            'Total CPU: 8.37%',
            [('util', 8.369022144778265, None, None, 0, 100)],
        ),
        (0, '2.95GHz/35.20GHz', []),
        (0, '2 sockets, 6 cores/socket, 24 threads', [])],
    )],
    'maintenance': [(
        None,
        {
            'target_state': 'false'
        },
        [(0, 'System not in Maintenance mode', [])],
    )],
    'mem_usage': [(
        None,
        (80.0, 90.0),
        [(
            0,
            'Usage: 79.52% - 108 GiB of 136 GiB',
            [
                ('mem_used', 116117209088.0, 116813103104.0, 131414740992.0, 0, 146016378880.0),
                ('mem_total', 146016378880.0, None, None, None, None),
            ],
        )],
    )],
    'multipath': [
        (u'6e843b6d8f2740bdecbad4676da7a9dd', {}, [(
            0,
            u'1 active, 0 dead, 0 disabled, 0 standby, 0 unknown\nIncluded Paths:\nvmhba66:C0:T2:L0',
            [],
        )]),
        (u'6e843b6bc5cc897d430ad40b7d9172d1', {}, [(
            0,
            u'1 active, 0 dead, 0 disabled, 0 standby, 0 unknown\nIncluded Paths:\nvmhba66:C0:T0:L0',
            [],
        )]),
        (u'6e843b63fcbd92ad8f22d4cf7d8e6cdc', {}, [(
            0,
            u'1 active, 0 dead, 0 disabled, 0 standby, 0 unknown\nIncluded Paths:\nvmhba66:C0:T1:L0',
            [],
        )]),
        (u'766d6862', {}, [(
            0,
            u'1 active, 0 dead, 0 disabled, 0 standby, 0 unknown\nIncluded Paths:\nvmhba1:C0:T0:L0',
            [],
        )]),
        (u'600605b002db9f7018d0a40c2a1444b0', {}, [(
            0,
            u'1 active, 0 dead, 0 disabled, 0 standby, 0 unknown\nIncluded Paths:\nvmhba0:C2:T0:L0',
            [],
        )]),
    ],
    'state': [(
        None,
        {},
        [
            (0, 'Entity state: green', []),
            (0, 'Power state: poweredOn', []),
        ],
    )],
}
