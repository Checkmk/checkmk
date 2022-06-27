#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'ucd_diskio'

freeze_time = '1970-01-01 00:00:01'

info = [
    [u'1', u'sdk', u'208537088', u'1368398848', u'3924134', u'704587945'],
    [u'2', u'dm-0', u'2438861824', u'1343166464', u'4027162', u'440261948'],
    [u'3', u'dm-1', u'85700608', u'0', u'20026', u'0']
]

discovery = {'': [(u'dm-0', {}), (u'dm-1', {}), (u'sdk', {})]}

checks = {
    '': [
        (
            u'dm-0', {}, [
                (0, u'[2]', []),
                (
                    0, 'Read: 2.44 GB/s', [
                        (
                            'disk_read_throughput', 2438861824.0, None, None,
                            None, None
                        )
                    ]
                ),
                (
                    0, 'Write: 1.34 GB/s', [
                        (
                            'disk_write_throughput', 1343166464.0, None, None,
                            None, None
                        )
                    ]
                ),
                (
                    0, 'Read operations: 4027162.00 1/s', [
                        ('disk_read_ios', 4027162.0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Write operations: 440261948.00 1/s',
                    [('disk_write_ios', 440261948.0, None, None, None, None)]
                )
            ]
        ),
        (
            u'dm-1', {}, [
                (0, u'[3]', []),
                (
                    0, 'Read: 85.7 MB/s', [
                        (
                            'disk_read_throughput', 85700608.0, None, None,
                            None, None
                        )
                    ]
                ),
                (
                    0, 'Write: 0.00 B/s', [
                        ('disk_write_throughput', 0.0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Read operations: 20026.00 1/s', [
                        ('disk_read_ios', 20026.0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Write operations: 0.00 1/s', [
                        ('disk_write_ios', 0.0, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            u'sdk', {'read': (50.0, 100.0), 'write': (1000.0, 5000.0)}, [
                (0, u'[1]', []),
                (
                    2, 'Read: 209 MB/s (warn/crit at 52.4 MB/s/105 MB/s)', [
                        (
                            'disk_read_throughput', 208537089.0, 52428800.0, 104857600.0,
                            None, None
                        )
                    ]
                ),
                (
                    1, 'Write: 1.37 GB/s (warn/crit at 1.05 GB/s/5.24 GB/s)', [
                        (
                            'disk_write_throughput', 1368398849.0, 1048576000.0, 5242880000.0,
                            None, None
                        )
                    ]
                ),
                (
                    0, 'Read operations: 3924134.00 1/s', [
                        ('disk_read_ios', 3924134.0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Write operations: 704587945.00 1/s',
                    [('disk_write_ios', 704587945.0, None, None, None, None)]
                )
            ]
        )
    ]
}

mock_item_state = {'': (0, 0)}
