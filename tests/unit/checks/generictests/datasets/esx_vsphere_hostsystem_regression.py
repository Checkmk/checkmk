#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# type: ignore

from cmk.base.plugins.agent_based.esx_vsphere_hostsystem_section import parse_esx_vsphere_hostsystem

checkname = 'esx_vsphere_hostsystem'

parsed = parse_esx_vsphere_hostsystem([
        [
            'config.storageDevice.multipathInfo', '6e843b6d8f2740bdecbad4676da7a9dd',
            'vmhba66:C0:T2:L0', 'active', '6e843b6bc5cc897d430ad40b7d9172d1',
            'vmhba66:C0:T0:L0', 'active', '6e843b63fcbd92ad8f22d4cf7d8e6cdc',
            'vmhba66:C0:T1:L0', 'active', '766d6862', 'vmhba1:C0:T0:L0', 'active',
            '600605b002db9f7018d0a40c2a1444b0', 'vmhba0:C2:T0:L0', 'active'
        ],
        ['hardware.biosInfo.biosVersion', '-[D6E158AUS-1.16]-'],
        ['hardware.biosInfo.releaseDate', '2012-11-26T00:00:00Z'],
        ['hardware.cpuInfo.hz', '2933437094'],
        ['hardware.cpuInfo.numCpuCores', '12'],
        ['hardware.cpuInfo.numCpuPackages', '2'],
        ['hardware.cpuInfo.numCpuThreads', '24'],
        ['hardware.cpuPkg.busHz.0', '133338040'],
        ['hardware.cpuPkg.busHz.1', '133338015'],
        [
            'hardware.cpuPkg.description.0', 'Intel(R)', 'Xeon(R)', 'CPU', 'X5670', '@',
            '2.93GHz'
        ],
        [
            'hardware.cpuPkg.description.1', 'Intel(R)', 'Xeon(R)', 'CPU', 'X5670', '@',
            '2.93GHz'
        ],
        ['hardware.cpuPkg.hz.0', '2933437152'],
        ['hardware.cpuPkg.hz.1', '2933437036'],
        ['hardware.cpuPkg.index.0', '0'],
        ['hardware.cpuPkg.index.1', '1'],
        ['hardware.cpuPkg.vendor.0', 'intel'],
        ['hardware.cpuPkg.vendor.1', 'intel'],
        ['hardware.memorySize', '146016378880'],
        ['hardware.systemInfo.model', 'System', 'x3650', 'M3', '-[7945M2G]-'],
        ['hardware.systemInfo.otherIdentifyingInfo.AssetTag.0', 'none'],
        ['hardware.systemInfo.otherIdentifyingInfo.OemSpecificString.0', 'IBM', 'SystemX'],
        ['hardware.systemInfo.otherIdentifyingInfo.ServiceTag.0', 'none'],
        ['hardware.systemInfo.uuid', 'e8a2b8a7-b9d4-3f21-a53a-afca3baa74f2'],
        ['hardware.systemInfo.vendor', 'IBM'],
        ['name', 'esx-w.dhcp.mathias-kettner'],
        ['overallStatus', 'green'],
        ['runtime.inMaintenanceMode', 'false'],
        ['runtime.powerState', 'poweredOn'],
        ['summary.quickStats.overallCpuUsage', '2946'],
        ['summary.quickStats.overallMemoryUsage', '110738'],
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
        ('6e843b6d8f2740bdecbad4676da7a9dd', None),
        ('6e843b6bc5cc897d430ad40b7d9172d1', None),
        ('6e843b63fcbd92ad8f22d4cf7d8e6cdc', None),
        ('766d6862', None),
        ('600605b002db9f7018d0a40c2a1444b0', None),
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
        ('6e843b6d8f2740bdecbad4676da7a9dd', {}, [(
            0,
            '1 active, 0 dead, 0 disabled, 0 standby, 0 unknown\nIncluded Paths:\nvmhba66:C0:T2:L0',
            [],
        )]),
        ('6e843b6bc5cc897d430ad40b7d9172d1', {}, [(
            0,
            '1 active, 0 dead, 0 disabled, 0 standby, 0 unknown\nIncluded Paths:\nvmhba66:C0:T0:L0',
            [],
        )]),
        ('6e843b63fcbd92ad8f22d4cf7d8e6cdc', {}, [(
            0,
            '1 active, 0 dead, 0 disabled, 0 standby, 0 unknown\nIncluded Paths:\nvmhba66:C0:T1:L0',
            [],
        )]),
        ('766d6862', {}, [(
            0,
            '1 active, 0 dead, 0 disabled, 0 standby, 0 unknown\nIncluded Paths:\nvmhba1:C0:T0:L0',
            [],
        )]),
        ('600605b002db9f7018d0a40c2a1444b0', {}, [(
            0,
            '1 active, 0 dead, 0 disabled, 0 standby, 0 unknown\nIncluded Paths:\nvmhba0:C2:T0:L0',
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
