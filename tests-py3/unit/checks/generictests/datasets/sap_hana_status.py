#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'sap_hana_status'

info = [
    [None, '[[H62 10]]'],
    [None, 'Version', '', '1.00.122.22.1543461992 (fa/hana1sp12)'],
    [None, 'All Started', 'OK', 'Yes'],
    [None, '[[H90 33]]'],
    [None, 'Version', '', '1.00.122.22.1543461992 (fa/hana1sp12)'],
    [None, 'All Started', 'OK', 'Yes']
]

discovery = {'': [('Status H62 10', {}), ('Version H62 10', {}),('Status H90 33', {}), ('Version H90 33', {})]}

checks = {
    '': [
        ('Status H62 10', {}, [(0, 'Status: OK', [])]),
        (
            'Version H62 10', {}, [
                (0, 'Version: 1.00.122.22.1543461992 (fa/hana1sp12)', [])
            ]
        ),
        ('Status H90 33', {}, [(0, 'Status: OK', [])]),
        (
            'Version H90 33', {}, [
                (0, 'Version: 1.00.122.22.1543461992 (fa/hana1sp12)', [])
            ]
        )
    ]
}
