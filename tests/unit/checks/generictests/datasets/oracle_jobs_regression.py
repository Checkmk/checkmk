#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'oracle_jobs'

info = [
    [
        'ORCLCDB', 'CDB$ROOT', 'SYS', 'PURGE_LOG', 'SCHEDULED', '6', '4',
        'TRUE', '03-DEC-19 03.00.00.421040 AM PST8PDT', 'DAILY_PURGE_SCHEDULE',
        'SUCCEEDED'
    ],
    [
        'ORCLCDB', 'CDB$ROOT', 'SYS', 'CLEANUP_ONLINE_PMO', 'SCHEDULED', '0',
        '68', 'TRUE', '02-DEC-19 09.15.07.529970 AM -07:00', '-', ''
    ]
]

discovery = {
    '': [
        ('ORCLCDB.CDB$ROOT.SYS.CLEANUP_ONLINE_PMO', {}),
        ('ORCLCDB.CDB$ROOT.SYS.PURGE_LOG', {})
    ]
}

checks = {
    '': [
        (
            'ORCLCDB.CDB$ROOT.SYS.CLEANUP_ONLINE_PMO', {
                'disabled': True,
                'status_missing_jobs': 2,
                'missinglog': 1
            }, [
                (
                    1,
                    'Job-State: SCHEDULED, Enabled: Yes, Last Duration: 0 seconds, Next Run: 02-DEC-19 09.15.07.529970 AM -07:00,  no log information found(!)',
                    [('duration', 0, None, None, None, None)]
                )
            ]
        ),
        (
            'ORCLCDB.CDB$ROOT.SYS.PURGE_LOG', {
                'disabled': True,
                'status_missing_jobs': 2,
                'missinglog': 1
            }, [
                (
                    0,
                    'Job-State: SCHEDULED, Enabled: Yes, Last Duration: 6 seconds, Next Run: 03-DEC-19 03.00.00.421040 AM PST8PDT, Last Run Status: SUCCEEDED (ignored disabled Job)',
                    [('duration', 6, None, None, None, None)]
                )
            ]
        )
    ]
}
