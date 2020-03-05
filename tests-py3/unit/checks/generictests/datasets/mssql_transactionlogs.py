#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore


checkname = 'mssql_transactionlogs'

info = [
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
]

discovery = {
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
                    0, '16.00 MB of 2.00 TB used', [
                        (
                            'data_size', 16777216.0, 1759218604441.6,
                            1979120929996.8, 0, 2199023255552.0
                        )
                    ]
                ),
                (
                    0, '256.00 MB of 2.00 TB allocated', [
                        (
                            'allocated_size', 268435456.0, None, None, 0,
                            2199023255552.0
                        )
                    ]
                )
            ]
        ),
        (
            'MSSQL46.DASH_CONFIG_T.DASH_CONFIG_T_log', {
                'used_levels': (80.0, 90.0)
            }, [
                (
                    0, '1.00 MB of 2.00 TB used', [
                        (
                            'data_size', 1048576.0, 1759218604441.6,
                            1979120929996.8, 0, 2199023255552.0
                        )
                    ]
                ),
                (
                    0, '256.00 MB of 2.00 TB allocated', [
                        (
                            'allocated_size', 268435456.0, None, None, 0,
                            2199023255552.0
                        )
                    ]
                )
            ]
        ),
        (
            'MSSQL46.NOC_ALARM_T.NOC_ALARM_T_log', {
                'used_levels': (80.0, 90.0)
            }, [
                (
                    0, '8.00 MB of 2.00 TB used', [
                        (
                            'data_size', 8388608.0, 1759218604441.6,
                            1979120929996.8, 0, 2199023255552.0
                        )
                    ]
                ),
                (
                    0, '256.00 MB of 2.00 TB allocated', [
                        (
                            'allocated_size', 268435456.0, None, None, 0,
                            2199023255552.0
                        )
                    ]
                )
            ]
        ),
        (
            'MSSQL46.NOC_CONFIG_T.NOC_CONFIG_T_log', {
                'used_levels': (80.0, 90.0)
            }, [
                (
                    0, '31.00 MB of 2.00 TB used', [
                        (
                            'data_size', 32505856.0, 1759218604441.6,
                            1979120929996.8, 0, 2199023255552.0
                        )
                    ]
                ),
                (
                    0, '768.00 MB of 2.00 TB allocated', [
                        (
                            'allocated_size', 805306368.0, None, None, 0,
                            2199023255552.0
                        )
                    ]
                )
            ]
        ),
        (
            'MSSQL46.master.mastlog', {
                'used_levels': (80.0, 90.0)
            }, [
                (0, '0.00 B used', [('data_size', 0, None, None, None, None)]),
                (
                    0, '1.00 MB allocated', [
                        ('allocated_size', 1048576.0, None, None, None, None)
                    ]
                ), (0, 'no maximum size', [])
            ]
        ),
        (
            'MSSQL46.model.modellog', {
                'used_levels': (80.0, 90.0)
            }, [
                (
                    0, '32.00 MB used', [
                        ('data_size', 33554432.0, None, None, None, None)
                    ]
                ),
                (
                    0, '34.00 MB allocated', [
                        ('allocated_size', 35651584.0, None, None, None, None)
                    ]
                ), (0, 'no maximum size', [])
            ]
        ),
        (
            'MSSQL46.msdb.MSDBLog', {
                'used_levels': (80.0, 90.0)
            }, [
                (
                    0, '3.00 MB of 2.00 TB used', [
                        (
                            'data_size', 3145728.0, 1759218604441.6,
                            1979120929996.8, 0, 2199023255552.0
                        )
                    ]
                ),
                (
                    0, '17.00 MB of 2.00 TB allocated', [
                        (
                            'allocated_size', 17825792.0, None, None, 0,
                            2199023255552.0
                        )
                    ]
                )
            ]
        ),
        (
            'MSSQL46.tempdb.templog', {
                'used_levels': (80.0, 90.0)
            }, [
                (
                    0, '55.00 MB used', [
                        ('data_size', 57671680.0, None, None, None, None)
                    ]
                ),
                (
                    0, '160.00 MB allocated',
                    [('allocated_size', 167772160.0, None, None, None, None)]
                ), (0, 'no maximum size', [])
            ]
        ),
        (
            'MSSQL46.test_autoclose.test_autoclose_log', {
                'used_levels': (80.0, 90.0)
            }, [
                (
                    0, '1.00 MB of 2.00 TB used', [
                        (
                            'data_size', 1048576.0, 1759218604441.6,
                            1979120929996.8, 0, 2199023255552.0
                        )
                    ]
                ),
                (
                    0, '32.00 MB of 2.00 TB allocated', [
                        (
                            'allocated_size', 33554432.0, None, None, 0,
                            2199023255552.0
                        )
                    ]
                )
            ]
        )
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
