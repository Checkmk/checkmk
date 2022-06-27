#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore


checkname = 'ucs_c_rack_server_util'


info = [['serverUtilization',
         'dn sys/rack-unit-1/utilization',
         'overallUtilization 0',
         'cpuUtilization 0',
         'memoryUtilization 0',
         'ioUtilization 0'],
        ['serverUtilization',
         'dn sys/rack-unit-2/utilization',
         'overallUtilization 90',
         'cpuUtilization 90',
         'memoryUtilization 90',
         'ioUtilization 90']]


discovery = {'': [('Rack unit 1', {}), ('Rack unit 2', {})],
             'cpu': [('Rack unit 1', {}), ('Rack unit 2', {})],
             'io': [('Rack unit 1', {}), ('Rack unit 2', {})],
             'mem': [('Rack unit 1', {}), ('Rack unit 2', {})],
             'pci_io': [('Rack unit 1', {}), ('Rack unit 2', {})]}


checks = {'': [('Rack unit 1',
                {'upper_levels': (90.0, 95.0)},
                [(0,
                  '0%',
                  [('overall_util', 0.0, 90.0, 95.0, None, None)])]),
               ('Rack unit 2',
                {'upper_levels': (90.0, 95.0)},
                [(1,
                  '90.00% (warn/crit at 90.00%/95.00%)',
                  [('overall_util', 90.0, 90.0, 95.0, None, None)])])],
          'cpu': [('Rack unit 1',
                   {'upper_levels': (90.0, 95.0)},
                   [(0, 'Total CPU: 0%', [('util', 0.0, 90.0, 95.0, 0, 100)])]),
                  ('Rack unit 2',
                   {'upper_levels': (90.0, 95.0)},
                   [(1,
                     'Total CPU: 90.00% (warn/crit at 90.00%/95.00%)',
                     [('util', 90.0, 90.0, 95.0, 0, 100)])])],
          'mem': [('Rack unit 1',
                   {'upper_levels': (90.0, 95.0)},
                   [(0,
                     '0%',
                     [('memory_util', 0.0, 90.0, 95.0, None, None)])]),
                  ('Rack unit 2',
                   {'upper_levels': (90.0, 95.0)},
                   [(1,
                     '90.00% (warn/crit at 90.00%/95.00%)',
                     [('memory_util', 90.0, 90.0, 95.0, None, None)])])],
          'pci_io': [('Rack unit 1',
                      {'upper_levels': (90.0, 95.0)},
                      [(0,
                        '0%',
                        [('pci_io_util', 0.0, 90.0, 95.0, None, None)])]),
                     ('Rack unit 2',
                      {'upper_levels': (90.0, 95.0)},
                      [(1,
                        '90.00% (warn/crit at 90.00%/95.00%)',
                        [('pci_io_util', 90.0, 90.0, 95.0, None, None)])])]}
