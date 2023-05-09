#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'oracle_performance'


info = [['TWH', 'sys_time_model', 'DB CPU', '14826'],
        ['TWH', 'sys_time_model', 'DB time', '69830'],
        ['TWH',
         'buffer_pool_statistics',
         'DEFAULT',
         '63743116',
         '55914822',
         '1059719411',
         '21386319',
         '1506816',
         '0',
         '1631907'],
        ['TWH',
         'librarycache',
         'SQL AREA',
         '248642',
         '227658',
         '10643092',
         '10582899',
         '13830',
         '14665'],
        ['TWH',
         'librarycache',
         'TABLE/PROCEDURE',
         '99440',
         '90692',
         '467944',
         '453367',
         '838',
         '3'],
]


discovery = {'': [('TWH', {})]}


checks = {'': [('TWH',
                {},
                [(0,
                  'DB Time: 0.00 1/s',
                  [('oracle_db_time', 0.0, None, None, None, None)]),
                 (0,
                  'DB CPU: 0.00 1/s',
                  [('oracle_db_cpu', 0.0, None, None, None, None)]),
                 (0,
                  'DB Non-Idle Wait: 0.00 1/s',
                  [('oracle_db_wait_time', 0.0, None, None, None, None)]),
                 (0,
                  'Buffer hit ratio: 98.1%',
                  [('oracle_buffer_hit_ratio',
                    98.096392315184,
                    None,
                    None,
                    None,
                    None)]),
                 (0,
                  'Library cache hit ratio: 99.3%',
                  [('oracle_library_cache_hit_ratio',
                    99.32706545096245,
                    None,
                    None,
                    None,
                    None)]),
                 (0,
                  '',
                  sorted([
                   ('oracle_db_block_gets', 0.0, None, None, None, None),
                   ('oracle_db_block_change', 0.0, None, None, None, None),
                   ('oracle_consistent_gets', 0.0, None, None, None, None),
                   ('oracle_physical_reads', 0.0, None, None, None, None),
                   ('oracle_physical_writes', 0.0, None, None, None, None),
                   ('oracle_free_buffer_wait', 0.0, None, None, None, None),
                   ('oracle_buffer_busy_wait', 0.0, None, None, None, None),
                   ('oracle_pins_sum', 0.0, None, None, None, None),
                   ('oracle_pin_hits_sum', 0.0, None, None, None, None)]))])]}
