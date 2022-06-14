#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'netapp_api_fcp'


freeze_time = '2001-09-09T01:46:40'


mock_item_state = {
    '': {
        'node0.avg_latency': (20000 - 100, 1000.0),
        'node0.avg_write_latency': (20000 - 100, 2000.0),
        'node0.avg_read_latency': (20000 - 100, 3000.0),
        'node0.write_bytes': (1000000000.0 - 100.0, 4000.0),
        'node0.read_bytes': (1000000000.0 - 100.0, 5000.0),
        'node0.read_ops': (1000000000.0 - 100.0, 6000),
        'node0.write_ops': (1000000000.0 - 100.0, 7000),
    }
}


info = [[u'instance_name node0',
         u'state online',
         u'port_wwpn de:ad:be:ef',
         u'data-link-rate 16',
         u'read_ops 20000',
         u'write_ops 20000',
         u'read_data 20000',
         u'write_data 20000',
         u'total_ops 20000',
         u'avg_latency 10000000',
         u'avg_read_latency 20000000',
         u'avg_write_latency 5000000']]


discovery = {'': [(u'node0', {'inv_speed': 16000000000, 'inv_state': u'online'})]}


checks = {
    '': [
        (u'node0', {'inv_speed': 16000000000, 'inv_state': u'online'}, [
            (0, 'Read: 150 B/s', [('read_bytes', 150.0)]),
            (0, 'Write: 160 B/s', [('write_bytes', 160.0)]),
            (0, 'Speed: 16 Gbit/s', []),
            (0, '\nState: online', []),
            (0, '\nRead OPS: 140', [('read_ops', 140)]),
            (0, '\nWrite OPS: 130', [('write_ops', 130)]),
            (0, '\nLatency: 90.00 ms',[('avg_latency_latency', 90.0)]),
            (0, '\nRead Latency: 170.00 ms', [('avg_read_latency_latency', 170.0)]),
            (0, '\nWrite Latency: 30.00 ms', [('avg_write_latency_latency', 30.0)]),
            (0, '\nAddress de:ad:be:ef', []),
        ]),
    ],
}
