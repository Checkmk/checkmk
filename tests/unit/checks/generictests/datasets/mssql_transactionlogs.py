#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based.mssql_datafiles_transactionlogs import parse_mssql_datafiles
# yapf: disable
# type: ignore


checkname = 'mssql_transactionlogs'

parsed = parse_mssql_datafiles([
    [
        'MSSQL46', 'CorreLog_Report_T', 'CorreLog_Report_T_log',
        'Z:\\mypath\\CorreLog_Report_T_log.ldf', '2097152', '256', '16', '0'
    ],
    [
        'MSSQL46', 'DASH_CONFIG_T', 'DASH_CONFIG_T_log',
        'Z:\\mypath\\DASH_CONFIG_T_log.ldf', '2097152', '256', '1', '0'
    ],
    [
        'MSSQL46', 'master', 'mastlog', 'Z:\\mypath\\mastlog.ldf', '0', '1',
        '0', '1'
    ],
    [
        'MSSQL46', 'model', 'modellog', 'Z:\\mypath\\modellog.ldf', '0', '34',
        '32', '1'
    ],
    [
        'MSSQL46', 'msdb', 'MSDBLog', 'Z:\\mypath\\MSDBLog.ldf', '2097152',
        '17', '3', '0'
    ],
    [
        'MSSQL46', 'NOC_ALARM_T', 'NOC_ALARM_T_log',
        'Z:\\mypath\\NOC_ALARM_T_log.ldf', '2097152', '256', '8', '0'
    ],
    [
        'MSSQL46', 'NOC_CONFIG_T', 'NOC_CONFIG_T_log',
        'Z:\\mypath\\NOC_CONFIG_T_log.ldf', '2097152', '768', '31', '0'
    ],
    [
        'MSSQL46', 'tempdb', 'templog', 'Z:\\mypath\\templog.ldf', '0', '160',
        '55', '1'
    ],
    [
        'MSSQL46', 'test_autoclose', 'test_autoclose_log',
        'Z:\\mypath\\test_autoclose_log.ldf', '2097152', '32', '1', '0'
    ]
])

discovery = {  # type: ignore[var-annotated]
    '': [
        ('MSSQL46.CorreLog_Report_T.CorreLog_Report_T_log', {}),
        ('MSSQL46.DASH_CONFIG_T.DASH_CONFIG_T_log', {}),
        ('MSSQL46.NOC_ALARM_T.NOC_ALARM_T_log', {}),
        ('MSSQL46.NOC_CONFIG_T.NOC_CONFIG_T_log', {}),
        ('MSSQL46.model.modellog', {}),
        ('MSSQL46.test_autoclose.test_autoclose_log', {})
    ]
}

checks = {
    '': [
        (
            'MSSQL46.CorreLog_Report_T.CorreLog_Report_T_log', {
                'used_levels': (80.0, 90.0)
            }, [
                (
                    0, 'Used: 16.00 MB', [
                        (
                            'data_size', 16777216.0, 1759218604441.6,
                            1979120929996.8, 0, 2199023255552.0
                        )
                    ]
                ),
                (0, 'Allocated used: 16.00 MB', []),
                (
                    0, 'Allocated: 256.00 MB', [
                        (
                            'allocated_size', 268435456.0, None, None, 0,
                            2199023255552.0
                        )
                    ]
                ),
                (
                    0, "Maximum size: 2.00 TB", [],
                ),
            ]
        ),
        (
            'MSSQL46.DASH_CONFIG_T.DASH_CONFIG_T_log', {
                'used_levels': (80.0, 90.0)
            }, [
                (
                    0, 'Used: 1.00 MB', [
                        (
                            'data_size', 1048576.0, 1759218604441.6,
                            1979120929996.8, 0, 2199023255552.0
                        )
                    ]
                ),
                (0, 'Allocated used: 1.00 MB', []),
                (
                    0, 'Allocated: 256.00 MB', [
                        (
                            'allocated_size', 268435456.0, None, None, 0,
                            2199023255552.0
                        )
                    ]
                ),
                (
                    0, "Maximum size: 2.00 TB", [],
                ),
            ]
        ),
        (
            'MSSQL46.master.mastlog', {
                'used_levels': (80.0, 90.0)
            }, [
                (0, 'Used: 0.00 B', [('data_size', 0, None, None, 0.0, None)]),
                (0, 'Allocated used: 0.00 B', []),
                (
                    0, 'Allocated: 1.00 MB', [
                        ('allocated_size', 1048576.0, None, None, 0.0, None)
                    ]
                ),
                (0, 'Maximum size: unlimited', [])
            ]
        ),
    ]
}

extra_sections = {
    '': [
        [
            ['MSSQL46', 'master', 'ONLINE', 'SIMPLE', '0', '0'],
            ['MSSQL46', 'tempdb', 'ONLINE', 'SIMPLE', '0', '0'],
            ['MSSQL46', 'model', 'ONLINE', 'FULL', '0', '0'],
            ['MSSQL46', 'msdb', 'ONLINE', 'SIMPLE', '0', '0'],
            ['MSSQL46', 'NOC_CONFIG_T', 'ONLINE', 'FULL', '0', '0'],
            ['MSSQL46', 'DASH_CONFIG_T', 'ONLINE', 'FULL', '0', '0'],
            ['MSSQL46', 'NOC_ALARM_T', 'ONLINE', 'FULL', '0', '1'],
            ['MSSQL46', 'CorreLog_Report_T', 'ONLINE', 'FULL', '0', '0'],
            ['MSSQL46', 'test_autoclose', 'ONLINE', 'FULL', '1', '0']
        ]
    ]
}
