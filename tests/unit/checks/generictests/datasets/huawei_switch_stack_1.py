#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'huawei_switch_stack'

info = [
    [[u'1']],
    [
        [u'1', u'1'],
        [u'2', u'3'],
        [u'3', u'2'],
        [u'4', u'2'],
        [u'5', u'4'],
    ],
]

discovery = {
    '': [
        (u'1', {
            'expected_role': 'master'
        }),
        (u'2', {
            'expected_role': 'slave'
        }),
        (u'3', {
            'expected_role': 'standby'
        }),
        (u'4', {
            'expected_role': 'standby'
        }),
        (u'5', {
            'expected_role': 'unknown'
        }),
    ]
}

checks = {
    '': [
        (
            u'1',
            {
                'expected_role': 'master'
            },
            [(0, 'master', [])],
        ),
        (
            u'2',
            {
                'expected_role': 'slave'
            },
            [(0, 'slave', [])],
        ),
        (
            u'3',
            {
                'expected_role': 'standby'
            },
            [(0, 'standby', [])],
        ),
        (
            u'4',
            {
                'expected_role': 'slave'
            },
            [(2, 'Unexpected role: standby (Expected: slave)', [])],
        ),
        (
            u'5',
            {
                'expected_role': 'unknown'
            },
            [(2, 'unknown', [])],
        ),
    ]
}
