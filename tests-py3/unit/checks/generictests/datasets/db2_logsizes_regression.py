#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'db2_logsizes'

info = [
    [u'[[[db2mpss:ASMPROD]]]'], [u'TIMESTAMP', u'1474466290'],
    [u'usedspace', u'2204620'], [u'logfilsiz', u'2000'], [u'logprimary', u'5'],
    [u'logsecond', u'20']
]

discovery = {'': [(u'db2mpss:ASMPROD', {})]}

checks = {
    '': [
        (
            u'db2mpss:ASMPROD', {}, [
                (
                    0, '1.03% used (2.00 of 195.00 MB)', [
                        (u'db2mpss:ASMPROD', 2, 156.0, 175.5, 0, 195),
                        ('fs_size', 195, None, None, None, None)
                    ]
                )
            ]
        )
    ]
}
