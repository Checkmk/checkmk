#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'oracle_tablespaces'

info = [
    [
        None, 'NRBTL20', '/dbdata/nrbtl20/data/fis_arc_medium01.dbf',
        'FIS_ARC_MEDIUM', 'AVAILABLE', 'YES', '4194302', '4194302', '4193792',
        '131072', 'ONLINE', '8192', 'ONLINE', '2544128', 'PERMANENT',
        '12.2.0.1.0'
    ],
    [
        None, 'NRBTL20', '/dbdata/nrbtl20/data/fis_arc_medium02.dbf',
        'FIS_ARC_MEDIUM', 'AVAILABLE', 'YES', '3968000', '4194302', '3967488',
        '131072', 'ONLINE', '8192', 'ONLINE', '2402304', 'PERMANENT',
        '12.2.0.1.0'
    ],
    [
        None, 'NRBTL20', '/dbdata/nrbtl20/data/fis_arc_medium03.dbf',
        'FIS_ARC_MEDIUM', 'AVAILABLE', 'YES', '1664000', '4194302', '1663488',
        '131072', 'ONLINE', '8192', 'ONLINE', '989696', 'PERMANENT',
        '12.2.0.1.0'
    ]
]

discovery = {'': [('NRBTL20.FIS_ARC_MEDIUM', {'autoextend': True})]}

checks = {
    '': [
        (
            'NRBTL20.FIS_ARC_MEDIUM', {
                'levels': (10.0, 5.0),
                'magic_normsize': 1000,
                'magic_maxlevels': (60.0, 50.0),
                'defaultincrement': True,
                'autoextend': True
            }, [
                (
                    0,
                    'ONLINE (PERMANENT), Size: 74.97 GB, 30.92% used (29.68 GB of max. 96.00 GB), Free: 66.32 GB',
                    []
                ),
                (
                    0, '', [
                        (
                            'size', 80497065984, 92771249356.8, 97925207654.4,
                            None, None
                        ), ('used', 31868305408, None, None, None, None),
                        ('max_size', 103079165952, None, None, None, None)
                    ]
                ), (0, '3 data files (3 avail, 3 autoext)', [])
            ]
        )
    ]
}
