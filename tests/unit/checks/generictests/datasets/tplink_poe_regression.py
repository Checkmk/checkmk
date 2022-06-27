#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'tplink_poe'

info = [
    [
        [u'1'], [u'49153'], [u'49154'], [u'49155'], [u'49156'], [u'49157'],
        [u'49159'], [u'49160'], [u'49180']
    ],
    [
        [u'1', u'1', u'300', u'0', u'0'], [u'2', u'1', u'300', u'0', u'1'],
        [u'3', u'1', u'300', u'-10', u'0'], [u'4', u'1', u'300', u'290', u'2'],
        [u'5', u'1', u'300', u'36', u'2'], [u'6', u'1', u'300', u'0', u'2'],
        [u'7', u'1', u'300', u'0', u'8'], [u'8', u'1', u'300', u'39', u'2'],
        [u'9', u'1', u'300', u'0', u'10']
    ]
]

discovery = {
    '': [
        (u'1', {}), (u'49153', {}), (u'49154', {}), (u'49155', {}),
        (u'49156', {}), (u'49157', {}), (u'49159', {}), (u'49160', {}),
        (u'49180', {})
    ]
}

checks = {
    '': [
        (u'1', {}, [(0, 'Operational status of the PSE is OFF', [])]),
        (u'49153', {}, [(0, 'Operational status of the PSE is OFF', [])]),
        (
            u'49154', {}, [
                (
                    3,
                    'Device returned faulty data: nominal power: 30.0, power consumption: -1.0, operational status: PoeStatus.OFF',
                    []
                )
            ]
        ),
        (
            u'49155', {}, [
                (
                    2,
                    'POE usage (29.0W/30.0W): : 96.67% (warn/crit at 90.00%/95.00%)',
                    [
                        (
                            'power_usage_percentage', 96.66666666666667, 90.0,
                            95.0, None, None
                        )
                    ]
                )
            ]
        ),
        (
            u'49156', {}, [
                (
                    0, 'POE usage (3.6W/30.0W): : 12.00%', [
                        (
                            'power_usage_percentage', 12.000000000000002, 90.0,
                            95.0, None, None
                        )
                    ]
                )
            ]
        ),
        (
            u'49157', {}, [
                (
                    0, 'POE usage (0.0W/30.0W): : 0%',
                    [('power_usage_percentage', 0.0, 90.0, 95.0, None, None)]
                )
            ]
        ),
        (
            u'49159', {}, [
                (
                    2,
                    'Operational status of the PSE is FAULTY (hardware-fault)',
                    []
                )
            ]
        ),
        (
            u'49160', {}, [
                (
                    0, 'POE usage (3.9W/30.0W): : 13.00%',
                    [('power_usage_percentage', 13.0, 90.0, 95.0, None, None)]
                )
            ]
        ),
        (u'49180', {}, [(2, 'Operational status of the PSE is FAULTY', [])])
    ]
}
