#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'ps'

info = [[None, 'dummy', 'section', '--', 'refer', 'to', 'section', 'ps_lnx']]

discovery = {
    '': [
        (
            'something', {
                'process': None,
                'match_groups': (),
                'user': None,
                'cgroup': (None, False),
                'cpu_rescale_max': True,
                'levels': (1, 2, 3, 4)
            }
        )
    ],
    'perf': []
}

checks = {
    '': [
        (
            'something', {
                'process': None,
                'match_groups': (),
                'user': None,
                'cgroup': (None, False),
                'cpu_rescale_max': True,
                'levels': (1, 2, 3, 4)
            }, [
                (
                    2, 'Processes: 5 (warn/crit at 4/5)', [
                        ('count', 5, 4.0, 5.0, 0.0, None)
                    ]
                ),
                (
                    0, 'virtual: 60.67 MB', [
                        ('vsz', 62124, None, None, None, None)
                    ]
                ),
                (
                    0, 'physical: 29.81 MB', [
                        ('rss', 30528, None, None, None, None)
                    ]
                ), (0, 'CPU: 0%', [('pcpu', 0.0, None, None, None, None)]),
                (
                    0,
                    'youngest running for: 1.00 s, oldest running for: 10 h',
                    []
                )
            ]
        ),
        (
            'something', {
                'process': None,
                'match_groups': (),
                'user': None,
                'cgroup': (None, False),
                'cpu_rescale_max': True,
                'levels': (1, 2, 3, 4),
                'max_age': (18000, 54000)
            }, [
                (
                    2, 'Processes: 5 (warn/crit at 4/5)', [
                        ('count', 5, 4.0, 5.0, 0.0, None)
                    ]
                ),
                (
                    0, 'virtual: 60.67 MB', [
                        ('vsz', 62124, None, None, None, None)
                    ]
                ),
                (
                    0, 'physical: 29.81 MB', [
                        ('rss', 30528, None, None, None, None)
                    ]
                ), (0, 'CPU: 0%', [('pcpu', 0.0, None, None, None, None)]),
                (
                    1,
                    'youngest running for: 1.00 s, oldest running for: 10 h (warn/crit at 300 m/15 '
                    'h)',
                    []
                )
            ]
        )
    ]
}

extra_sections = {
    '': [
        [
            [
                None, '[header]', 'CGROUP', 'USER', 'VSZ', 'RSS', 'TIME',
                'ELAPSED', 'PID', 'COMMAND'
            ],
            [
                None,
                '12:blkio:/user.slice,11:devices:/user.slice,5:cpu,cpuacct:/user.slice,4:pids:/user.slice/user-1000.slice/user@1000.service,2:memory:/user.slice/user-1000.slice/user@1000.service,1:name=systemd:/user.slice/user-1000.slice/user@1000.service/vte-spawn-052a0d9a-9d9b-441a-af56-15abe1f4c573.scope,0::/user.slice/user-1000.slice/user@1000.service/vte-spawn-052a0d9a-9d9b-441a-af56-15abe1f4c573.scope',
                'joerg', '13740', '7800', '00:00:03', '10:06:14', '6195',
                '/bin/bash'
            ],
            [
                None,
                '12:blkio:/user.slice,11:devices:/user.slice,5:cpu,cpuacct:/user.slice,4:pids:/user.slice/user-1000.slice/user@1000.service,2:memory:/user.slice/user-1000.slice/user@1000.service,1:name=systemd:/user.slice/user-1000.slice/user@1000.service/vte-spawn-94f2992d-1408-41a7-946e-82cb5cfadcbf.scope,0::/user.slice/user-1000.slice/user@1000.service/vte-spawn-94f2992d-1408-41a7-946e-82cb5cfadcbf.scope',
                'joerg', '11712', '5656', '00:00:00', '10:02:52', '7413',
                '/bin/bash'
            ],
            [
                None,
                '12:blkio:/user.slice,11:devices:/user.slice,5:cpu,cpuacct:/user.slice,4:pids:/user.slice/user-1000.slice/user@1000.service,2:memory:/user.slice/user-1000.slice/user@1000.service,1:name=systemd:/user.slice/user-1000.slice/user@1000.service/vte-spawn-94f2992d-1408-41a7-946e-82cb5cfadcbf.scope,0::/user.slice/user-1000.slice/user@1000.service/vte-spawn-94f2992d-1408-41a7-946e-82cb5cfadcbf.scope',
                'ps_stable', '13184', '5816', '00:00:00', '01:40:25', '220485',
                'bash'
            ],
            [
                None,
                '12:blkio:/user.slice,11:devices:/user.slice,5:cpu,cpuacct:/user.slice,4:pids:/user.slice/user-1000.slice/user@1000.service,2:memory:/user.slice/user-1000.slice/user@1000.service,1:name=systemd:/user.slice/user-1000.slice/user@1000.service/vte-spawn-56f500f9-50cd-4ef3-b286-33d221c13a9e.scope,0::/user.slice/user-1000.slice/user@1000.service/vte-spawn-56f500f9-50cd-4ef3-b286-33d221c13a9e.scope',
                'joerg', '12636', '6828', '00:00:00', '40:22', '264451',
                '/bin/bash'
            ],
            [
                None,
                '12:blkio:/system.slice/xinetd.service,11:devices:/system.slice/xinetd.service,5:cpu,cpuacct:/system.slice/xinetd.service,4:pids:/system.slice/xinetd.service,2:memory:/system.slice/xinetd.service,1:name=systemd:/system.slice/xinetd.service,0::/system.slice/xinetd.service',
                'root', '10852', '4428', '00:00:00', '00:01', '303304',
                '/bin/bash', '/usr/bin/check_mk_agent'
            ]
        ],
        [
            ['MemTotal:', '16203208', 'kB'], ['MemFree:', '474848', 'kB'],
            ['MemAvailable:', '6528956', 'kB'], ['Buffers:', '690504', 'kB'],
            ['Cached:', '6594060', 'kB'], ['SwapCached:', '5444', 'kB'],
            ['Active:', '10150504', 'kB'], ['Inactive:', '4166456', 'kB'],
            ['Active(anon):', '7263308', 'kB'],
            ['Inactive(anon):', '1343092', 'kB'],
            ['Active(file):', '2887196', 'kB'],
            ['Inactive(file):', '2823364', 'kB'],
            ['Unevictable:', '299032', 'kB'], ['Mlocked:', '320', 'kB'],
            ['SwapTotal:', '999420', 'kB'], ['SwapFree:', '913660', 'kB'],
            ['Dirty:', '1712', 'kB'], ['Writeback:', '0', 'kB'],
            ['AnonPages:', '7326540', 'kB'], ['Mapped:', '1350168', 'kB'],
            ['Shmem:', '1575724', 'kB'], ['KReclaimable:', '685556', 'kB'],
            ['Slab:', '948724', 'kB'], ['SReclaimable:', '685556', 'kB'],
            ['SUnreclaim:', '263168', 'kB'], ['KernelStack:', '20944', 'kB'],
            ['PageTables:', '45984', 'kB'], ['NFS_Unstable:', '0', 'kB'],
            ['Bounce:', '0', 'kB'], ['WritebackTmp:', '0', 'kB'],
            ['CommitLimit:', '9101024', 'kB'],
            ['Committed_AS:', '15536416', 'kB'],
            ['VmallocTotal:', '34359738367', 'kB'],
            ['VmallocUsed:', '50020', 'kB'], ['VmallocChunk:', '0', 'kB'],
            ['Percpu:', '9312', 'kB'], ['HardwareCorrupted:', '0', 'kB'],
            ['AnonHugePages:', '0', 'kB'], ['ShmemHugePages:', '0', 'kB'],
            ['ShmemPmdMapped:', '0', 'kB'], ['FileHugePages:', '0', 'kB'],
            ['FilePmdMapped:', '0', 'kB'], ['CmaTotal:', '0', 'kB'],
            ['CmaFree:', '0', 'kB'], ['HugePages_Total:', '0'],
            ['HugePages_Free:', '0'], ['HugePages_Rsvd:', '0'],
            ['HugePages_Surp:', '0'], ['Hugepagesize:', '2048', 'kB'],
            ['Hugetlb:', '0', 'kB'], ['DirectMap4k:', '584800', 'kB'],
            ['DirectMap2M:', '13901824', 'kB'],
            ['DirectMap1G:', '2097152', 'kB']
        ], None, None, None,
        [['1.77', '1.36', '1.30', '1/1298', '303334', '8'], ['125872']]
    ]
}

mock_host_conf = {
    '': {
        'default_params': {
            'cpu_rescale_max': True,
            'levels': (1, 2, 3, 4)
        },
        'descr': 'something'
    }
}
