#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'sap_hana_backup'


info = [
    [None, '[[Crap its broken]]'],
    [None, 'data snapshot', '?', 'failed', '', ''],
    [None, 'complete data backup', '2042-23-23 23:23:23.424242420', 'failed', '', (
    '[447] backup could not be completed, [110507] Backint exited with exit code 1 instead of 0.'
    ' console output: No additional Information was received, [110203] Not all data could be'
    ' written: Expected 4096 but transferred 0')],
]


discovery = {
    '': [
        ('Crap its broken - complete data backup', {}),
        ('Crap its broken - data snapshot', {}),
    ],
}


checks = {
    '': [
        ('Crap its broken - complete data backup', {'backup_age': (86400, 172800)},
                [(2, 'Status: failed', []),
                 (0, 'Message: [447] backup could not be completed, [110507] Backint exited with exit code 1 instead of 0. console output: No additional Information was received, [110203] Not all data could be written: Expected 4096 but transferred 0', [])]),
        ('Crap its broken - data snapshot', {'backup_age': (86400, 172800)}, [
            (2, 'Status: failed', []),
        ]),
    ],
}
