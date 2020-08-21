#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore


checkname = 'mssql_tablespaces'


info = [
    ['MSSQL_SQLEXPRESS', 'master', '5.25', 'MB', '1.59', 'MB', '2464',
     'KB', '1096', 'KB', '1024', 'KB', '344', 'KB'],
    ['MSSQL_Katze', 'Kitty'] + ['-'] * 12 + 'ERROR: Kitty ist auf die Nase gefallen!'.split(' '),
]


discovery = {
    '': [
        ('MSSQL_SQLEXPRESS master', {}),
        ('MSSQL_Katze Kitty', {}),
    ],
}


checks = {
    '': [
        ('MSSQL_SQLEXPRESS master', {}, [
            (0, 'Size: 5.25 MB', [('size', 5505024.0, None, None, None, None)]),
            (0, 'Unallocated space: 1.59 MB, 30.29%', [('unallocated', 1667235.84, None, None, None, None)]),
            (0, 'Reserved space: 2.41 MB, 45.83%', [('reserved', 2523136.0, None, None, None, None)]),
            (0, 'Data: 1.07 MB, 20.39%', [('data', 1122304.0, None, None, None, None)]),
            (0, 'Indexes: 1.00 MB, 19.05%', [('indexes', 1048576.0, None, None, None, None)]),
            (0, 'Unused: 344.00 kB, 6.4%', [('unused', 352256.0, None, None, None, None)]),
        ]),
        ('MSSQL_SQLEXPRESS master', {"size": (3*1024**2, 6*1024**2)}, [
            (1, 'Size: 5.25 MB (warn/crit at 3.00 MB/6.00 MB)', [('size', 5505024.0, 3*1024**2, 6*1024**2, None, None)]),
            (0, 'Unallocated space: 1.59 MB, 30.29%', [('unallocated', 1667235.84, None, None, None, None)]),
            (0, 'Reserved space: 2.41 MB, 45.83%', [('reserved', 2523136.0, None, None, None, None)]),
            (0, 'Data: 1.07 MB, 20.39%', [('data', 1122304.0, None, None, None, None)]),
            (0, 'Indexes: 1.00 MB, 19.05%', [('indexes', 1048576.0, None, None, None, None)]),
            (0, 'Unused: 344.00 kB, 6.4%', [('unused', 352256.0, None, None, None, None)]),
        ]),
        ('MSSQL_Katze Kitty', {}, [
            (2, 'Kitty ist auf die Nase gefallen!'),
        ]),
    ],
}
