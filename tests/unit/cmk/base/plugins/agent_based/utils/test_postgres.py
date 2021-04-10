#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any

from cmk.base.plugins.agent_based.utils import postgres


def test_parse_function_for_stats_section():
    assert postgres.parse_dbs([
        [u'[databases_start]'],
        [u'postgres'],
        [u'adwebconnect'],
        [u'[databases_end]'],
        [u'datname', u'sname', u'tname', u'vtime', u'atime'],
        [u'postgres', u'pg_catalog', u'pg_statistic', u'-1', u'-1'],
        [u'adwebconnect', u'public', u'serveraktion', u'1488881726', u'1488881726'],
        [u'adwebconnect', u'pg_catalog', u'pg_statistic', u'1488882719', u'-1'],
        [u'adwebconnect', u'public', u'auftrag', u'1489001316', u'1489001316'],
        [u'adwebconnect', u'public', u'anrede', u'-1', u'-1'],
        [u'adwebconnect', u'public', u'auftrag_mediadaten', u'-1', u''],
    ]) == {
        'adwebconnect': [
            {
                'atime': '1488881726',
                'sname': 'public',
                'tname': 'serveraktion',
                'vtime': '1488881726'
            },
            {
                'atime': '-1',
                'sname': 'pg_catalog',
                'tname': 'pg_statistic',
                'vtime': '1488882719'
            },
            {
                'atime': '1489001316',
                'sname': 'public',
                'tname': 'auftrag',
                'vtime': '1489001316'
            },
            {
                'atime': '-1',
                'sname': 'public',
                'tname': 'anrede',
                'vtime': '-1'
            },
            {
                'atime': '',
                'sname': 'public',
                'tname': 'auftrag_mediadaten',
                'vtime': '-1'
            },
        ],
        'postgres': [{
            'atime': '-1',
            'sname': 'pg_catalog',
            'tname': 'pg_statistic',
            'vtime': '-1'
        },],
    }
