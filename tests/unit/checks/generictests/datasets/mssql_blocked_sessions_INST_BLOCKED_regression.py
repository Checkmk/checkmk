#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'mssql_blocked_sessions'


info = [['ID 1', '1', '232292187', 'Foo', '2'],
        ['ID 1', '3', '232292187', 'Foo', '4'],
        ['ID 1', '5', '232292187', 'Bar', '6'],
        ['ID 1', '7', '232292187', 'Bar', '8'],
        ['ID 2', '1', '232292187', 'Foo', '2'],
        ['ID 2', '3', '232292187', 'Foo', '4'],
        ['ID 2', '5', '232292187', 'Bar', '6'],
        ['ID 2', '7', '232292187', 'Bar', '8']]


discovery = {'': [('ID 1', {}), ('ID 2', {})]}


checks = {'': [('ID 1',
                {'state': 2},
                [(2,
                  'Summary: 1 blocked by 1 ID(s), 3 blocked by 1 ID(s), 5 blocked by 1 ID(s), 7 blocked by 1 ID(s)',
                  []),
                 (0, '\nSession 1 blocked by 2 (Type: Foo, Wait: 2 days 16 hours)', []),
                 (0, '\nSession 3 blocked by 4 (Type: Foo, Wait: 2 days 16 hours)', []),
                 (0, '\nSession 5 blocked by 6 (Type: Bar, Wait: 2 days 16 hours)', []),
                 (0, '\nSession 7 blocked by 8 (Type: Bar, Wait: 2 days 16 hours)', [])]),
               ('ID 2',
                {'state': 2},
                [(2,
                  'Summary: 1 blocked by 1 ID(s), 3 blocked by 1 ID(s), 5 blocked by 1 ID(s), 7 blocked by 1 ID(s)',
                  []),
                 (0, '\nSession 1 blocked by 2 (Type: Foo, Wait: 2 days 16 hours)', []),
                 (0, '\nSession 3 blocked by 4 (Type: Foo, Wait: 2 days 16 hours)', []),
                 (0, '\nSession 5 blocked by 6 (Type: Bar, Wait: 2 days 16 hours)', []),
                 (0, '\nSession 7 blocked by 8 (Type: Bar, Wait: 2 days 16 hours)', [])])]}
