#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'apc_netbotz_drycontact'

info = [
    ['1.6', 'Pumpe 0 RZ4', 'Kaeltepark RZ4', '2'],
    ['2.5', 'Pumpe 1 RZ4', 'Kaeltepark RZ4', '1'],
    ['2.6', 'Pumpe 2 RZ4', 'Kaeltepark RZ4', '3']
]

discovery = {
    '': [
        ('Pumpe 0 RZ4 1.6', {}), ('Pumpe 1 RZ4 2.5', {}),
        ('Pumpe 2 RZ4 2.6', {})
    ]
}

checks = {
    '': [
        (
            'Pumpe 0 RZ4 1.6', {}, [
                (0, '[Kaeltepark RZ4] State: Open low mem', [])
            ]
        ),
        (
            'Pumpe 1 RZ4 2.5', {}, [
                (2, '[Kaeltepark RZ4] State: Closed high mem', [])
            ]
        ),
        ('Pumpe 2 RZ4 2.6', {}, [(1, '[Kaeltepark RZ4] State: Disabled', [])])
    ]
}
