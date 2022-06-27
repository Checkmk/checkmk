#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'nimble_latency'

info = [
    [
        'Nimble-DS02-10TB', '2749393105', '823401304', '64892594',
        '1472507102', '209251305', '72177249', '48215967', '22500331',
        '20998217', '14280659', '1063850', '58321', '17993', '0', '1578578518',
        '858441885', '415775502', '245830152', '21290631', '11363763',
        '24902844', '523548', '251495', '120980', '56755', '16917', '10804',
        '0'
    ],
    [
        'SY-OLKVM-VSORAC01-DD-02', '0', '0', '0', '0', '0', '0', '0', '0', '0',
        '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0',
        '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0',
        '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0',
        '0', '0', '0', '0', '0'
    ]
]

discovery = {
    '': [('Nimble-DS02-10TB', {}), ('SY-OLKVM-VSORAC01-DD-02', {})],
    'write': [('Nimble-DS02-10TB', {}), ('SY-OLKVM-VSORAC01-DD-02', {})]
}

checks = {
    '': [
        (
            'Nimble-DS02-10TB', {
                'range_reference': '20',
                'read': (1.0, 2.0),
                'write': (1.0, 2.0)
            }, [
                (
                    1, 'At or above 10-20 ms: 1.32% (warn/crit at 1.00%/2.00%)',
                    []
                ), (0, '\nLatency breakdown:', []),
                (
                    0, '0-0.1 ms: 29.95%', [
                        (
                            'nimble_read_latency_01', 29.948474901700166, None,
                            None, None, None
                        )
                    ]
                ),
                (
                    0, '0.1-0.2 ms: 2.36%', [
                        (
                            'nimble_read_latency_02', 2.360251572682983, None,
                            None, None, None
                        )
                    ]
                ),
                (
                    0, '0.2-0.5 ms: 53.56%', [
                        (
                            'nimble_read_latency_05', 53.55753236312856, None,
                            None, None, None
                        )
                    ]
                ),
                (
                    0, '0.5-1.0 ms: 7.61%', [
                        (
                            'nimble_read_latency_1', 7.610817988139241, None,
                            None, None, None
                        )
                    ]
                ),
                (
                    0, '1-2 ms: 2.63%', [
                        (
                            'nimble_read_latency_2', 2.6252065908196127, None,
                            None, None, None
                        )
                    ]
                ),
                (
                    0, '2-5 ms: 1.75%', [
                        (
                            'nimble_read_latency_5', 1.753694912245006, None,
                            None, None, None
                        )
                    ]
                ),
                (
                    0, '5-10 ms: 0.82%', [
                        (
                            'nimble_read_latency_10', 0.8183744608612452, None,
                            None, None, None
                        )
                    ]
                ),
                (
                    0, '10-20 ms: 0.76%', [
                        (
                            'nimble_read_latency_20', 0.7637400763758735, None,
                            None, None, None
                        )
                    ]
                ),
                (
                    0, '20-50 ms: 0.52%', [
                        (
                            'nimble_read_latency_50', 0.5194113193209597, None,
                            None, None, None
                        )
                    ]
                ),
                (
                    0, '50-100 ms: 0.04%', [
                        (
                            'nimble_read_latency_100', 0.03869399388778928,
                            None, None, None, None
                        )
                    ]
                ),
                (
                    0, '100-200 ms: <0.01%', [
                        (
                            'nimble_read_latency_200', 0.002121231769074361,
                            None, None, None, None
                        )
                    ]
                ),
                (
                    0, '200-500 ms: <0.01%', [
                        (
                            'nimble_read_latency_500', 0.0006544353358302322,
                            None, None, None, None
                        )
                    ]
                ),
                (
                    0, '500+ ms: 0%', [
                        (
                            'nimble_read_latency_1000', 0.0, None, None, None,
                            None
                        )
                    ]
                )
            ]
        ),
        (
            'SY-OLKVM-VSORAC01-DD-02', {
                'range_reference': '20',
                'read': (1.0, 2.0),
                'write': (1.0, 2.0)
            }, [(0, 'No current read operations', [])]
        )
    ],
    'write': [
        (
            'Nimble-DS02-10TB', {
                'range_reference': '20',
                'read': (1.0, 2.0),
                'write': (1.0, 2.0)
            }, [
                (0, 'At or above 10-20 ms: 0.03%', []),
                (0, '\nLatency breakdown:', []),
                (
                    0, '0-0.1 ms: 54.38%', [
                        (
                            'nimble_write_latency_01', 54.38068966551083, None,
                            None, None, None
                        )
                    ]
                ),
                (
                    0, '0.1-0.2 ms: 26.34%', [
                        (
                            'nimble_write_latency_02', 26.338601295979373,
                            None, None, None, None
                        )
                    ]
                ),
                (
                    0, '0.2-0.5 ms: 15.57%', [
                        (
                            'nimble_write_latency_05', 15.5728808669877, None,
                            None, None, None
                        )
                    ]
                ),
                (
                    0, '0.5-1.0 ms: 1.35%', [
                        (
                            'nimble_write_latency_1', 1.3487216984920354, None,
                            None, None, None
                        )
                    ]
                ),
                (
                    0, '1-2 ms: 0.72%', [
                        (
                            'nimble_write_latency_2', 0.7198731561606111, None,
                            None, None, None
                        )
                    ]
                ),
                (
                    0, '2-5 ms: 1.58%', [
                        (
                            'nimble_write_latency_5', 1.5775486436715846, None,
                            None, None, None
                        )
                    ]
                ),
                (
                    0, '5-10 ms: 0.03%', [
                        (
                            'nimble_write_latency_10', 0.03316578770268049,
                            None, None, None, None
                        )
                    ]
                ),
                (
                    0, '10-20 ms: 0.02%', [
                        (
                            'nimble_write_latency_20', 0.015931738404665153,
                            None, None, None, None
                        )
                    ]
                ),
                (
                    0, '20-50 ms: <0.01%', [
                        (
                            'nimble_write_latency_50', 0.007663856984021115,
                            None, None, None, None
                        )
                    ]
                ),
                (
                    0, '50-100 ms: <0.01%', [
                        (
                            'nimble_write_latency_100', 0.003595323219772841,
                            None, None, None, None
                        )
                    ]
                ),
                (
                    0, '100-200 ms: <0.01%', [
                        (
                            'nimble_write_latency_200', 0.0010716603455007867,
                            None, None, None, None
                        )
                    ]
                ),
                (
                    0, '200-500 ms: <0.01%', [
                        (
                            'nimble_write_latency_500', 0.0006844132158651357,
                            None, None, None, None
                        )
                    ]
                ),
                (
                    0, '500+ ms: 0%', [
                        (
                            'nimble_write_latency_1000', 0.0, None, None, None,
                            None
                        )
                    ]
                )
            ]
        ),
        (
            'SY-OLKVM-VSORAC01-DD-02', {
                'range_reference': '20',
                'read': (1.0, 2.0),
                'write': (1.0, 2.0)
            }, [(0, 'No current write operations', [])]
        )
    ]
}
