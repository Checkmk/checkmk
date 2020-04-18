#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'esx_vsphere_counters'


info = [
    ['disk.read', '', '11#12#13', 'kiloBytesPerSecond'],
    ['disk.numberRead', '', '110#140#150', 'number'],
    ['disk.write', '', '51#49#53', 'kiloBytesPerSecond'],
    ['disk.numberWrite', '', '11#102#5', 'kiloBytesPerSecond'],
    ['disk.deviceLatency', '', '700#900#23', 'millisecond']
]


discovery = {
    '': [],
    'diskio': [
        ('SUMMARY', {}),
    ],
    'if': [],
    'ramdisk': [],
    'uptime': [],
    'swap': [(None, {})],
}


checks = {
    'diskio': [
        ('SUMMARY', {}, [
            (0, 'Read: 12.00 kB/s', [
                ('disk_read_throughput', 12288.0, None, None, None, None),
            ]),
            (0, 'Write: 51.00 kB/s', [
                ('disk_write_throughput', 52224.0, None, None, None, None),
            ]),
            (0, 'Latency: 900.00 ms', [
                ('disk_latency', 0.9, None, None, None, None),
            ]),
            (0, 'Read operations: 6.67 1/s', [
                ('disk_read_ios', 6.666666666666667, None, None, None, None),
            ]),
            (0, 'Write operations: 1.97 1/s', [
                ('disk_write_ios', 1.9666666666666668, None, None, None, None),
            ]),
        ]),
    ],
}
