#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# type: ignore

checkname = 'mssql_blocked_sessions'

info = [
    ['ID-1', 'No blocking sessions'],
    ['MSSQLSERVER_SA', 'No blocking sessions'],
    ['MSSQLSERVER_LIVE', 'No blocking sessions']
]

discovery = {
    '': [('ID-1', {}), ('MSSQLSERVER_LIVE', {}), ('MSSQLSERVER_SA', {})]
}

checks = {
    '': [
        ('ID-1', {
            'state': 1
        }, [(0, 'No blocking sessions', [])]),
        ('ID-1', {
            'state': 2
        }, [(0, 'No blocking sessions', [])]),
        ('MSSQLSERVER_LIVE', {
            'state': 2
        }, [(0, 'No blocking sessions', [])]),
        ('MSSQLSERVER_SA', {
            'state': 2
        }, [(0, 'No blocking sessions', [])])
    ]
}
