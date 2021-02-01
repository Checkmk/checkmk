#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'postgres_stats'


mock_item_state = {
    '': 1547250000.0,
}


freeze_time = '2019-01-12 00:00:00'


parsed = {
    'adwebconnect': [
        {
            'atime': '1488881726',
            'sname': 'public',
            'tname': 'serveraktion',
            'vtime': '1488881726',
        },
        {
            'atime': '-1',
            'sname': 'pg_catalog',
            'tname': 'pg_statistic',
            'vtime': '1488882719',
        },
        {
            'atime': '1489001316',
            'sname': 'public',
            'tname': 'auftrag',
            'vtime': '1489001316',
        },
        {
            'atime': '-1',
            'sname': 'public',
            'tname': 'anrede',
            'vtime': '-1',
        },
        {
            'atime': '',
            'sname': 'public',
            'tname': 'auftrag_mediadaten',
            'vtime': '-1',
        },
    ],
    'postgres': [
        {
            'atime': '-1',
            'sname': 'pg_catalog',
            'tname': 'pg_statistic',
            'vtime': '-1',
        },
    ],
}


discovery = {'': [(u'ANALYZE adwebconnect', {}),
                  (u'ANALYZE postgres', {}),
                  (u'VACUUM adwebconnect', {}),
                  (u'VACUUM postgres', {})]}


checks = {
    '': [
        (u'ANALYZE adwebconnect', {'never_analyze_vacuum': (1000, 1100)}, [
            (0, u'Table: serveraktion', []),
            (0, u'Not analyzed for: 676 d', []),
            (0, u'2 tables were never analyzed: anrede / auftrag_mediadaten', []),
            (2, u'Never analyzed tables for: 20 m (warn/crit at 16 m/18 m)', []),
        ]),
        (u'ANALYZE adwebconnect', {'never_analyze_vacuum': (0, 1000 * 365 * 24 * 3600)}, [
            (0, u'Table: serveraktion', []),
            (0, u'Not analyzed for: 676 d', []),
            (0, u'2 tables were never analyzed: anrede / auftrag_mediadaten', []),
            (1, u'Never analyzed tables for: 20 m (warn/crit at 0.00 s/1000 y)', []),
        ]),
        (u'ANALYZE adwebconnect', {'never_analyze_vacuum': None}, [
            (0, u'Table: serveraktion', []),
            (0, u'Not analyzed for: 676 d', []),
            (0, u'2 tables were never analyzed: anrede / auftrag_mediadaten', []),
            (0, u'Never analyzed tables for: 20 m', []),
        ]),
        (u'ANALYZE postgres', {}, [
            (0, u'No never checked tables', []),
        ]),
        (u'VACUUM adwebconnect', {}, [
            (0, u'Table: serveraktion', []),
            (0, u'Not vacuumed for: 676 d', []),
            (0, u'2 tables were never vacuumed: anrede / auftrag_mediadaten', []),
            (0, u'Never vacuumed tables for: 20 m', []),
        ]),
        (u'VACUUM postgres', {}, [
            (0, u'No never checked tables', []),
        ]),
]}
