#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'postgres_stats'


mock_item_state = {
    '': 1547250000.0,
}


freeze_time = '2019-01-12 00:00:00'


info = [[u'[databases_start]'],
        [u'postgres'],
        [u'adwebconnect'],
        [u'[databases_end]'],
        [u'datname', u'sname', u'tname', u'vtime', u'atime'],
        [u'postgres', u'pg_catalog', u'pg_statistic', u'-1', u'-1'],
        [u'adwebconnect', u'public', u'serveraktion', u'1488881726', u'1488881726'],
        [u'adwebconnect', u'pg_catalog', u'pg_statistic', u'1488882719', u'-1'],
        [u'adwebconnect', u'public', u'auftrag', u'1489001316', u'1489001316'],
        [u'adwebconnect', u'public', u'anrede', u'-1', u'-1'],
        [u'adwebconnect', u'public', u'auftrag_mediadaten', u'-1', u'']]


discovery = {'': [(u'ANALYZE adwebconnect', {}),
                  (u'ANALYZE postgres', {}),
                  (u'VACUUM adwebconnect', {}),
                  (u'VACUUM postgres', {})]}


checks = {
    '': [
        (u'ANALYZE adwebconnect', {'never_analyze_vacuum': (1000, 1100)}, [
            (0, u'Table: serveraktion', []),
            (0, u'Time since last analyse: 676 d', []),
            (0, u'2 tables were never analyzed: anrede/auftrag_mediadaten', []),
            (2, u'Unhandled tables for: 20 m (warn/crit at 16 m/18 m)', []),
        ]),
        (u'ANALYZE adwebconnect', {'never_analyze_vacuum': (0, 1000 * 365 * 24 * 3600)}, [
            (0, u'Table: serveraktion', []),
            (0, u'Time since last analyse: 676 d', []),
            (0, u'2 tables were never analyzed: anrede/auftrag_mediadaten', []),
            (1, u'Unhandled tables for: 20 m (warn/crit at 0.00 s/1000 y)', []),
        ]),
        (u'ANALYZE adwebconnect', {'never_analyze_vacuum': None}, [
            (0, u'Table: serveraktion', []),
            (0, u'Time since last analyse: 676 d', []),
            (0, u'2 tables were never analyzed: anrede/auftrag_mediadaten', []),
            (0, u'Unhandled tables for: 20 m', []),
        ]),
        (u'ANALYZE postgres', {}, [
            (0, u'No never checked tables', []),
        ]),
        (u'VACUUM adwebconnect', {}, [
            (0, u'Table: serveraktion', []),
            (0, u'Time since last vacuum: 676 d', []),
            (0, u'2 tables were never vacuumed: anrede/auftrag_mediadaten', []),
            (0, u'Unhandled tables for: 20 m', []),
        ]),
        (u'VACUUM postgres', {}, [
            (0, u'No never checked tables', []),
        ]),
]}
