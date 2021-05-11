#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'oracle_performance'

info = [
    ['SGP', 'sys_time_model', 'DB CPU', '55555899'],
    ['SGP', 'sys_time_model', 'DB time', '60435096'],
    ['SGP', 'SGA_info', 'Redo Buffers', '14655488'],
    ['SGP', 'SGA_info', 'Buffer Cache Size', '3875536896'],
    ['SGP', 'SGA_info', 'Shared Pool Size', '5385486336'],
    ['SGP', 'SGA_info', 'Large Pool Size', '33554432'],
    ['SGP', 'SGA_info', 'Java Pool Size', '67108864'],
    ['SGP', 'SGA_info', 'Streams Pool Size', '0'],
    ['SGP', 'SGA_info', 'Granule Size', '16777216'],
    ['SGP', 'SGA_info', 'Maximum SGA Size', '13119782912'],
    ['SGP', 'SGA_info', 'Startup overhead in Shared Pool', '218103808'],
    ['SGP', 'SGA_info', 'Free SGA Memory Available', '3187671040'],
    ['SGP', 'librarycache', 'JAVA RESOURCE', '2', '0', '2', '0', '0', '0'],
    ['SGP', 'librarycache', 'JAVA DATA', '18', '5', '676', '663', '0', '0']
]

discovery = {
    '': [('SGP', {})],
    'dbtime': [],
    'memory': [],
    'iostat_bytes': [],
    'iostat_ios': [],
    'waitclasses': []
}

checks = {
    '': [
        (
            'SGP', {}, [
                (
                    0, 'DB Time: 0.00 1/s', [
                        ('oracle_db_time', 0.0, None, None, None, None)
                    ]
                ),
                (
                    0, 'DB CPU: 0.00 1/s', [
                        ('oracle_db_cpu', 0.0, None, None, None, None)
                    ]
                ),
                (
                    0, 'DB Non-Idle Wait: 0.00 1/s', [
                        ('oracle_db_wait_time', 0.0, None, None, None, None)
                    ]
                ), (0, 'Maximum SGA Size: 12.22 GB', []),
                (0, 'Buffer Cache Size: 3.61 GB', []),
                (0, 'Shared Pool Size: 5.02 GB', []),
                (0, 'Redo Buffers: 13.98 MB', []),
                (0, 'Java Pool Size: 64.00 MB', []),
                (0, 'Large Pool Size: 32.00 MB', []),
                (0, 'Streams Pool Size: 0.00 B', []),
                (
                    0, 'Library cache hit ratio: 97.8%', [
                        (
                            'oracle_library_cache_hit_ratio',
                            97.78761061946902, None, None, None, None
                        )
                    ]
                ),
                (
                    0, '', [
                        ('oracle_pin_hits_sum', 0.0, None, None, None, None),
                        ('oracle_pins_sum', 0.0, None, None, None, None),
                        (
                            'oracle_sga_buffer_cache', 3875536896, None, None,
                            None, None
                        ),
                        (
                            'oracle_sga_java_pool', 67108864, None, None, None,
                            None
                        ),
                        (
                            'oracle_sga_large_pool', 33554432, None, None,
                            None, None
                        ),
                        (
                            'oracle_sga_redo_buffer', 14655488, None, None,
                            None, None
                        ),
                        (
                            'oracle_sga_shared_pool', 5385486336, None, None,
                            None, None
                        ),
                        (
                            'oracle_sga_size', 13119782912, None, None, None,
                            None
                        ),
                        ('oracle_sga_streams_pool', 0, None, None, None, None)
                    ]
                )
            ]
        )
    ]
}
