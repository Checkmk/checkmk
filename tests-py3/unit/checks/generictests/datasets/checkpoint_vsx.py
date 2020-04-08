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
            '0', 'imo1fwdc004', 'VSX Gateway', '195.23.49.134', 'Standard',
            'nix', 'Trust established', 'Standby'
        ]
    ],
    [
        [
            '0', '104470', '499900', '150512', '369', '150143', '0',
            '46451524', '44344', '0', '2386'
        ]
    ]
]

discovery = {
    '': [('1', {})],
    'connections': [('1', {})],
    'packets': [('1', {})],
    'traffic': [('1', {})],
    'status': [('1', {})]
}

checks = {
    '': [
        (
            '1', {}, [
                (0, 'Name: imo1fwdc004', []), (0, 'Type: VSX Gateway', []),
                (0, 'Main IP: 195.23.49.134', [])
            ]
        )
    ],
    'connections': [
        (
            '1', {
                'levels_perc': (90.0, 95.0)
            }, [
                (
                    0, 'Used connections: 104470', [
                        ('connections', 104470, None, None, None, None)
                    ]
                ), (0, 'Used percentage: 20.9%', [])
            ]
        )
    ],
    'packets': [
        (
            '1', {}, [
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
            '1', {}, [
                (
                    0, 'Total number of bytes accepted: 0.00 B 1/s', [
                        ('bytes_accepted', 0.0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Total number of bytes dropped: 0.00 B 1/s', [
                        ('bytes_dropped', 0.0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Total number of bytes rejected: 0.00 B 1/s', [
                        ('bytes_rejected', 0.0, None, None, None, None)
                    ]
                )
            ]
        )
    ],
    'status': [
        (
            '1', {}, [
                (0, 'HA Status: Standby', []),
                (0, 'SIC Status: Trust established', []),
                (0, 'Policy name: Standard', []),
                (2, 'Policy type: nix (no policy installed)', [])
            ]
        )
    ]
}
