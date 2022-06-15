#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'checkpoint_vsx'

info = [
    [
        [
            '0', 'my_vsid1', 'VSX Gateway', '192.168.1.11', 'Standard',
            'ACTIVE', 'Trust established', 'Standby'
        ],
        [
            '1', 'my_vsid2', 'VSX Gateway', '192.168.1.111', 'Standard',
            'STANDBY', 'not known', 'Standby'
        ]
    ],
    [
        [
            '104470', '499900', '150512', '369', '150143', '0', '46451524',
            '44344', '0', '2386'
        ],
        [
            '104470', '499900', '150512', '369', '150143', '0', '46451524',
            '44344', '0', '2386'
        ]
    ]
]

discovery = {
    '': [('my_vsid1 0', {}), ('my_vsid2 1', {})],
    'connections': [('my_vsid1 0', {}), ('my_vsid2 1', {})],
    'packets': [('my_vsid1 0', {}), ('my_vsid2 1', {})],
    'traffic': [('my_vsid1 0', {}), ('my_vsid2 1', {})],
    'status': [('my_vsid1 0', {}), ('my_vsid2 1', {})]
}

checks = {
    '': [
        (
            'my_vsid1 0', {}, [
                (0, 'Type: VSX Gateway', []), (0, 'Main IP: 192.168.1.11', [])
            ]
        ),
        (
            'my_vsid2 1', {}, [
                (0, 'Type: VSX Gateway', []),
                (0, 'Main IP: 192.168.1.111', [])
            ]
        )
    ],
    'connections': [
        (
            'my_vsid1 0', {
                'levels_perc': (90.0, 95.0)
            }, [
                (
                    0, 'Used connections: 104470', [
                        ('connections', 104470, None, None, None, None)
                    ]
                ), (0, 'Used percentage: 20.90%', [])
            ]
        ),
        (
            'my_vsid2 1', {
                'levels_perc': (90.0, 95.0)
            }, [
                (
                    0, 'Used connections: 104470', [
                        ('connections', 104470, None, None, None, None)
                    ]
                ), (0, 'Used percentage: 20.90%', [])
            ]
        )
    ],
    'packets': [
        (
            'my_vsid1 0', {}, [
                (
                    0, 'Total number of packets processed: 0 1/s', [
                        ('packets', 0.0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Total number of accepted packets: 0 1/s', [
                        ('packets_accepted', 0.0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Total number of dropped packets: 0 1/s', [
                        ('packets_dropped', 0.0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Total number of rejected packets: 0 1/s', [
                        ('packets_rejected', 0.0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Total number of logs sent: 0 1/s', [
                        ('logged', 0.0, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            'my_vsid2 1', {}, [
                (
                    0, 'Total number of packets processed: 0 1/s', [
                        ('packets', 0.0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Total number of accepted packets: 0 1/s', [
                        ('packets_accepted', 0.0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Total number of dropped packets: 0 1/s', [
                        ('packets_dropped', 0.0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Total number of rejected packets: 0 1/s', [
                        ('packets_rejected', 0.0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Total number of logs sent: 0 1/s', [
                        ('logged', 0.0, None, None, None, None)
                    ]
                )
            ]
        )
    ],
    'traffic': [
        (
            'my_vsid1 0', {}, [
                (
                    0, 'Total number of bytes accepted: 0.00 B/s', [
                        ('bytes_accepted', 0.0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Total number of bytes dropped: 0.00 B/s', [
                        ('bytes_dropped', 0.0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Total number of bytes rejected: 0.00 B/s', [
                        ('bytes_rejected', 0.0, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            'my_vsid2 1', {}, [
                (
                    0, 'Total number of bytes accepted: 0.00 B/s', [
                        ('bytes_accepted', 0.0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Total number of bytes dropped: 0.00 B/s', [
                        ('bytes_dropped', 0.0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Total number of bytes rejected: 0.00 B/s', [
                        ('bytes_rejected', 0.0, None, None, None, None)
                    ]
                )
            ]
        )
    ],
    'status': [
        (
            'my_vsid1 0', {}, [
                (0, 'HA Status: Standby', []),
                (0, 'SIC Status: Trust established', []),
                (0, 'Policy name: Standard', []),
                (0, 'Policy type: ACTIVE', [])
            ]
        ),
        (
            'my_vsid2 1', {}, [
                (0, 'HA Status: Standby', []),
                (2, 'SIC Status: not known', []),
                (0, 'Policy name: Standard', []),
                (2, 'Policy type: STANDBY (no policy installed)', [])
            ]
        )
    ]
}
