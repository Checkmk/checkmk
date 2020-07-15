#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore


checkname = 'aws_ec2'

parsed = {
    'Summary': {
        'CPUUtilization': 0.1,
        'NetworkIn': 3540.4,
        'StatusCheckFailed_Instance': 0.0,
        'NetworkOut': 27942.1,
        'StatusCheckFailed_System': 0.0,
        'DiskReadOps': 1000,
        'DiskWriteOps': 2000,
        'DiskReadBytes': 3000,
        'DiskWriteBytes': 4000,
    }
}

discovery = {
    '': [(None, {})],
    'cpu_util': [(None, {})],
    'network_io': [('Summary', {})],
    'disk_io': [('Summary', {})],
    'cpu_credits': []
}

checks = {
    '': [(None,
          {},
          [(0, 'System: passed', []), (0, 'Instance: passed', [])])],
    'cpu_util':
        [(None,
          {'util': (0.01, 95.0)},
          [(1, 'Total CPU: 0.1% (warn/crit at 0.01%/95.0%)', [('util', 0.1, 0.01, 95.0, 0, 100)])]),
         (None,
          {'util': (90.0, 95.0)},
          [(0, 'Total CPU: 0.1%', [('util', 0.1, 90.0, 95.0, 0, 100)])])],
    'disk_io':
        [('Summary',
          {},
          [(0, 'Read: 50.00 B/s', [('disk_read_throughput', 50.0, None, None)]),
           (0, 'Write: 66.67 B/s', [('disk_write_throughput', 66.66666666666667, None, None)]),
           (0, 'Read operations: 16.67 1/s', [('disk_read_ios', 16.666666666666668, None, None)]),
           (0, 'Write operations: 33.33 1/s', [('disk_write_ios', 33.333333333333336, None, None)]),
           ])],
    'network_io':
        [('Summary',
          {'errors_in': (0.01, 0.1), 'errors_out': (0.01, 0.1)},
          [(0, '[0] (up) speed unknown, In: 59.01 B/s, Out: 465.70 B/s',
            [('in', 59.00666666666667, None, None, 0, None),
             ('inmcast', 0.0, None, None, None, None), ('inbcast', 0.0, None, None, None, None),
             ('inucast', 0.0, None, None, None, None), ('innucast', 0.0, None, None, None, None),
             ('indisc', 0.0, None, None, None, None), ('inerr', 0.0, 0.01, 0.1, None, None),
             ('out', 465.70166666666665, None, None, 0, None),
             ('outmcast', 0.0, None, None, None, None), ('outbcast', 0.0, None, None, None, None),
             ('outucast', 0.0, None, None, None, None), ('outnucast', 0.0, None, None, None, None),
             ('outdisc', 0.0, None, None, None, None), ('outerr', 0.0, 0.01, 0.1, None, None),
             ('outqlen', 0)])])]
}
