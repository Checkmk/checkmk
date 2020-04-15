#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore


checkname = "mssql_backup"

freeze_time = '2020-01-30 00:00:00'

info = [
     ['MSSQL_SQL0x4', 'master', '2016-07-08 20:20:27', 'D'],
     ['MSSQL_SQL0x4', 'model', '2016-07-08 20:20:28', 'D'],
     ['MSSQL_SQL0x4', 'model', '2016-07-12 09:09:42', 'L'],
     ['MSSQL_SQL0x4', 'model', '2016-07-11 20:20:07', 'I'],
     ['MSSQL_SQL0x4', 'msdb', '2016-07-08', '20:20:43', 'D'],
     ['MSSQL_SQL0x4', 'msdb', '-', '-', '-', 'no backup found'],
     ['MSSQL_SQL0x4', 'foo'],
     ['MSSQL_SQL0x4', 'bar', '12345678'],
     ['MSSQL_Parrot', 'Polly', '-', '-', '-', 'ERROR: Polly has no crackers']
]

extra_sections = {
    '': [{u'SQL0x4 master': {'DBname': u'master',
                             'Instance': u'MSSQLSERVER',
                             'Recovery': u'SIMPLE',
                             'Status': u'ONLINE',
                             'auto_close': u'0',
                             'auto_shrink': u'0'},
          u'SQL0x4 model': {'DBname': u'model',
                            'Instance': u'MSSQLSERVER',
                            'Recovery': u'FULL',
                            'Status': u'ONLINE',
                            'auto_close': u'0',
                            'auto_shrink': u'0'},
          u'SQL0x4 msdb': {'DBname': u'msdb',
                           'Instance': u'MSSQLSERVER',
                           'Recovery': u'SIMPLE',
                           'Status': u'ONLINE',
                           'auto_close': u'0',
                           'auto_shrink': u'0'},
          u'SQL0x4 foo': {},
          u'SQL0x4 bar': None,
          u'Parrot Polly': {'DBname': u'Polly' },
        }]
}

discovery = {
    '': [
        ("MSSQL_SQL0x4 master", {}),
        ("MSSQL_SQL0x4 model", {}),
        ("MSSQL_SQL0x4 msdb", {}),
        ("MSSQL_SQL0x4 bar", {}),
        ("MSSQL_Parrot Polly", {}),
    ],
    'per_type': [],
}

checks = {'': [('MSSQL_Parrot Polly',
                {'database': (None, None),
                 'database_diff': (None, None),
                 'file_diff': (None, None),
                 'file_or_filegroup': (None, None),
                 'log': (None, None),
                 'partial': (None, None),
                 'partial_diff': (None, None),
                 'unspecific': (None, None)},
                [(2, 'Polly has no crackers', [])]),
               ('MSSQL_SQL0x4 bar',
                {'database': (None, None),
                 'database_diff': (None, None),
                 'file_diff': (None, None),
                 'file_or_filegroup': (None, None),
                 'log': (None, None),
                 'partial': (None, None),
                 'partial_diff': (None, None),
                 'unspecific': (None, None)},
                [(0,
                  '[database] Last backup was at 1970-05-23 22:21:18 (50 y ago)',
                  [('seconds', 1567996722.0, None, None, None, None)])]),
               ('MSSQL_SQL0x4 master',
                {'database': (None, None),
                 'database_diff': (None, None),
                 'file_diff': (None, None),
                 'file_or_filegroup': (None, None),
                 'log': (None, None),
                 'partial': (None, None),
                 'partial_diff': (None, None),
                 'unspecific': (None, None)},
                [(0,
                  '[database] Last backup was at 2016-07-08 20:20:27 (3.7 d ago)',
                  [('backup_age_database', 322773.0, None, None, None, None)])]),
               ('MSSQL_SQL0x4 model',
                {'database': (None, None),
                 'database_diff': (None, None),
                 'file_diff': (None, None),
                 'file_or_filegroup': (None, None),
                 'log': (None, None),
                 'partial': (None, None),
                 'partial_diff': (None, None),
                 'unspecific': (None, None)},
                [(0,
                  '[database] Last backup was at 2016-07-08 20:20:28 (3.7 d ago)',
                  [('backup_age_database', 322772.0, None, None, None, None)]),
                 (0,
                  '[log] Last backup was at 2016-07-12 09:09:42 (290 m ago)',
                  [('backup_age_log', 17418.0, None, None, None, None)]),
                 (0,
                  '[database diff] Last backup was at 2016-07-11 20:20:07 (17 h ago)',
                  [('backup_age_database_diff', 63593.0, None, None, None, None)])]),
               ('MSSQL_SQL0x4 msdb',
                {'database': (None, None),
                 'database_diff': (None, None),
                 'file_diff': (None, None),
                 'file_or_filegroup': (None, None),
                 'log': (None, None),
                 'partial': (None, None),
                 'partial_diff': (None, None),
                 'unspecific': (None, None)},
                [(0,
                  '[database] Last backup was at 2016-07-08 20:20:43 (3.7 d ago)',
                  [('backup_age_database', 322757.0, None, None, None, None)]),
                 (1, 'No backup found', [])]),
               ('MSSQL_SQL0x4 tempdb',
                {'database': (None, None),
                 'database_diff': (None, None),
                 'file_diff': (None, None),
                 'file_or_filegroup': (None, None),
                 'log': (None, None),
                 'partial': (None, None),
                 'partial_diff': (None, None),
                 'unspecific': (None, None)},
                [(1, 'No backup found', [])])]}
