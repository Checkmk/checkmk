#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'mssql_jobs'

info = [
    ['MSSQLSERVER'],
    [
        '{2C32E575-3C76-48E0-9E04-43BD2A15B2E1}', 'teststsssss', '1', '', '',
        '5', '', '0', '0', '0', '', '2021-02-08 07:38:50'
    ]
]

discovery = {'': [('teststsssss', {})]}

checks = {
    '': [
        (
            'teststsssss', {
                'ignore_db_status': True,
                'status_disabled_jobs': 0,
                'status_missing_jobs': 2,
                'run_duration': None
            }, [
                (
                    0, 'Last duration: 0.00 s', [
                        ('database_job_duration', 0.0, None, None, None, None)
                    ]
                ),
                (0, 'MSSQL status: Unknown', []),
                (0, 'Last run: N/A', []),
                (0, 'Schedule is disabled', []),
                (0, '\nOutcome message: ', [])
            ]
        )
    ]
}
