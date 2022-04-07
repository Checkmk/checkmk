#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'megaraid_pdisks'

info = [
    ['Enclosure', 'Device', 'ID:', '10'], ['Slot', 'Number:', '0'],
    ['Device', 'Id:', '4'],
    ['Raw', 'Size:', '140014MB', '[0x11177330', 'Sectors]'],
    ['Firmware', 'state:', 'Unconfigured(good)'],
    ['Predictive', 'Failure', 'Count:', '10'],
    ['Inquiry', 'Data:', 'FUJITSU', 'MBB2147RC', '5204BS04P9104BV5'],
    ['Enclosure', 'Device', 'ID:', '11'], ['Slot', 'Number:', '1'],
    ['Device', 'Id:', '5'],
    ['Raw', 'Size:', '140014MB', '[0x11177330', 'Sectors]'],
    ['Firmware', 'state:', 'Unconfigured(good)'],
    ['Inquiry', 'Data:', 'FUJITSU', 'MBB2147RC', '5204BS04P9104BSC'],
    ['Enclosure', 'Device', 'ID:', '12'], ['Slot', 'Number:', '2'],
    ['Device', 'Id:', '6'],
    ['Raw', 'Size:', '140014MB', '[0x11177330', 'Sectors]'],
    ['Predictive', 'Failure', 'Count:', '19'],
    ['Firmware', 'state:', 'Failed'],
    ['Inquiry', 'Data:', 'FUJITSU', 'MBB2147RC', '5204BS04P9104BSC']
]

discovery = {'': [('e10/0', {}), ('e11/1', {}), ('e12/2', {})]}

checks = {
    '': [
        (
            'e10/0', {}, [
                (
                    0,
                    'Unconfigured(good) (FUJITSU MBB2147RC 5204BS04P9104BV5)',
                    []
                ),
                (
                    1,
                    'Predictive fail count: 10',
                    []
                )
            ]
        ),
        (
            'e11/1', {}, [
                (
                    0,
                    'Unconfigured(good) (FUJITSU MBB2147RC 5204BS04P9104BSC)',
                    []
                )
            ]
        ),
        (
            'e12/2', {}, [
                (
                    2,
                    'Failed (FUJITSU MBB2147RC 5204BS04P9104BSC)',
                    []
                ),
                (
                    1,
                    'Predictive fail count: 19',
                    []
                )
            ]
        )
    ]
}
