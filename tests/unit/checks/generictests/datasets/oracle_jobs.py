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
        'DB19', 'CDB$ROOT', 'ORACLE_OCM', 'MGMT_STATS_CONFIG_JOB', 'SCHEDULED',
        '0', '2', 'TRUE', '01-JAN-20 01.01.01.312723 AM +00:00', '-',
        'SUCCEEDED'
    ]
]

discovery = {'': [('DB19.CDB$ROOT.ORACLE_OCM.MGMT_STATS_CONFIG_JOB', {})]}

checks = {
    '': [
        (
            'DB19.CDB$ROOT.ORACLE_OCM.MGMT_STATS_CONFIG_JOB', {
                'disabled': True,
                'status_missing_jobs': 2,
                'missinglog': 1
            }, [
                (
                    0,
                    'Job-State: SCHEDULED, Enabled: Yes, Last Duration: 0 seconds, Next Run: 01-JAN-20 01.01.01.312723 AM +00:00, Last Run Status: SUCCEEDED (ignored disabled Job)',
                    [('duration', 0, None, None, None, None)]
                )
            ]
        ),
        (
            'DB19.CDB$ROOT.ORACLE_OCM.MISSING',
            {
                'status_missing_jobs': 2,
            },
            [
                (
                    2,
                    'Job is missing',
                )
            ]
        ),
        # test if old autochecks files still work
        (
            'DB19.CDB$ROOT.ORACLE_OCM.MISSING',
            {
                'missingjob': 2,
            },
            [
                (
                    2,
                    'Job is missing',
                )
            ]
        ),
        (
            'DB19.CDB$ROOT.ORACLE_OCM.MISSING',
            {
                'status_missing_jobs': 2,
                'missingjob': 3,
            },
            [
                (
                    2,
                    'Job is missing',
                )
            ]
        ),
    ]
}
