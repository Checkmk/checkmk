#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'mssql_instance'

info = [
    ['MSSQL_SQL2019MT02', 'config', '15.0.2000.5', 'Standard Edition', ''],
    ['MSSQL_SQL2019MT02', 'state', '1', ''],
    [
        'MSSQL_SQL2019MT02', 'details', '15.0.4053.23', 'RTM',
        'Standard Edition (64-bit)'
    ], ['MSSQL_SQL2017MT02', 'config', '14.0.2000.5', 'Standard Edition', ''],
    ['MSSQL_SQL2017MT02', 'state', '1', ''],
    [
        'MSSQL_SQL2017MT02', 'details', '14.0.4053.23', 'RTM',
        'Standard Edition (64-bit)'
    ], ['MSSQL_SQL2016MT02', 'config', '13.0.2000.5', 'Standard Edition', ''],
    ['MSSQL_SQL2016MT02', 'state', '1', ''],
    [
        'MSSQL_SQL2016MT02', 'details', '13.0.4053.23', 'RTM',
        'Standard Edition (64-bit)'
    ], ['MSSQL_SQL2014MT02', 'config', '12.0.2000.5', 'Standard Edition', ''],
    ['MSSQL_SQL2014MT02', 'state', '1', ''],
    [
        'MSSQL_SQL2014MT02', 'details', '12.0.4053.23', 'RTM',
        'Standard Edition (64-bit)'
    ], ['MSSQL_SQL2012MT02', 'config', '11.0.2000.5', 'Standard Edition', ''],
    ['MSSQL_SQL2012MT02', 'state', '1', ''],
    [
        'MSSQL_SQL2012MT02', 'details', '11.0.4053.23', 'RTM',
        'Standard Edition (64-bit)'
    ],
    ['MSSQL_SQL2008R2MT02', 'config', '10.50.2000.5', 'Standard Edition', ''],
    ['MSSQL_SQL2008R2MT02', 'state', '1', ''],
    [
        'MSSQL_SQL2008R2MT02', 'details', '10.50.4053.23', 'RTM',
        'Standard Edition (64-bit)'
    ], ['MSSQL_SQL2008MT02', 'config', '10.0.2000.5', 'Standard Edition', ''],
    ['MSSQL_SQL2008MT02', 'state', '1', ''],
    [
        'MSSQL_SQL2008MT02', 'details', '10.0.4053.23', 'RTM',
        'Standard Edition (64-bit)'
    ], ['MSSQL_SQL2005MT02', 'config', '9.0.2000.5', 'Standard Edition', ''],
    ['MSSQL_SQL2005MT02', 'state', '1', ''],
    [
        'MSSQL_SQL2005MT02', 'details', '9.0.4053.23', 'RTM',
        'Standard Edition (64-bit)'
    ], ['MSSQL_SQL2000MT02', 'config', '8.0.2000.5', 'Standard Edition', ''],
    ['MSSQL_SQL2000MT02', 'state', '1', ''],
    [
        'MSSQL_SQL2000MT02', 'details', '8.0.4053.23', 'RTM',
        'Standard Edition (64-bit)'
    ]
]

discovery = {
    '': [
        ('SQL2000MT02', {}), ('SQL2005MT02', {}), ('SQL2008MT02', {}),
        ('SQL2008R2MT02', {}), ('SQL2012MT02', {}), ('SQL2014MT02', {}),
        ('SQL2016MT02', {}), ('SQL2017MT02', {}), ('SQL2019MT02', {})
    ]
}

checks = {
    '': [
        (
            'SQL2000MT02', {}, [
                (
                    0,
                    'Version: Microsoft SQL Server 2000 (RTM) (8.0.4053.23) - Standard Edition (64-bit)',
                    []
                )
            ]
        ),
        (
            'SQL2005MT02', {}, [
                (
                    0,
                    'Version: Microsoft SQL Server 2005 (RTM) (9.0.4053.23) - Standard Edition (64-bit)',
                    []
                )
            ]
        ),
        (
            'SQL2008MT02', {}, [
                (
                    0,
                    'Version: Microsoft SQL Server 2008 (RTM) (10.0.4053.23) - Standard Edition (64-bit)',
                    []
                )
            ]
        ),
        (
            'SQL2008R2MT02', {}, [
                (
                    0,
                    'Version: Microsoft SQL Server 2008R2 (RTM) (10.50.4053.23) - Standard Edition (64-bit)',
                    []
                )
            ]
        ),
        (
            'SQL2012MT02', {}, [
                (
                    0,
                    'Version: Microsoft SQL Server 2012 (RTM) (11.0.4053.23) - Standard Edition (64-bit)',
                    []
                )
            ]
        ),
        (
            'SQL2014MT02', {}, [
                (
                    0,
                    'Version: Microsoft SQL Server 2014 (RTM) (12.0.4053.23) - Standard Edition (64-bit)',
                    []
                )
            ]
        ),
        (
            'SQL2016MT02', {}, [
                (
                    0,
                    'Version: Microsoft SQL Server 2016 (RTM) (13.0.4053.23) - Standard Edition (64-bit)',
                    []
                )
            ]
        ),
        (
            'SQL2017MT02', {}, [
                (
                    0,
                    'Version: Microsoft SQL Server 2017 (RTM) (14.0.4053.23) - Standard Edition (64-bit)',
                    []
                )
            ]
        ),
        (
            'SQL2019MT02', {}, [
                (
                    0,
                    'Version: Microsoft SQL Server 2019 (RTM) (15.0.4053.23) - Standard Edition (64-bit)',
                    []
                )
            ]
        )
    ]
}
