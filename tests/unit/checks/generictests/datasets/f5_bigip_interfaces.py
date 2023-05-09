#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'f5_bigip_interfaces'

info = [
    ['1.1', '0', '439189486311', '375541323492'],
    ['1.2', '0', '121591230679', '201963958037'],
    ['1.3', '0', '434523103807', '413556383286'],
    ['1.4', '0', '1244059671', '991534207'], ['2.1', '5', '0', '0'],
    ['2.2', '5', '0', '0'], ['mgmt', '0', '21498688535', '3648383840']
]

discovery = {
    '': [
        ('1.1', {
            'state': 0
        }), ('1.2', {
            'state': 0
        }), ('1.3', {
            'state': 0
        }), ('1.4', {
            'state': 0
        }), ('mgmt', {
            'state': 0
        })
    ]
}

checks = {
    '': [
        (
            '1.1', {
                'state': 0
            }, [
                (
                    0, 'in bytes: 0.00 B/s, out bytes: 0.00 B/s', [
                        ('bytes_in', 0.0, None, None, None, None),
                        ('bytes_out', 0.0, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            '1.2', {
                'state': 0
            }, [
                (
                    0, 'in bytes: 0.00 B/s, out bytes: 0.00 B/s', [
                        ('bytes_in', 0.0, None, None, None, None),
                        ('bytes_out', 0.0, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            '1.3', {
                'state': 0
            }, [
                (
                    0, 'in bytes: 0.00 B/s, out bytes: 0.00 B/s', [
                        ('bytes_in', 0.0, None, None, None, None),
                        ('bytes_out', 0.0, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            '1.4', {
                'state': 0
            }, [
                (
                    0, 'in bytes: 0.00 B/s, out bytes: 0.00 B/s', [
                        ('bytes_in', 0.0, None, None, None, None),
                        ('bytes_out', 0.0, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            'mgmt', {
                'state': 0
            }, [
                (
                    0, 'in bytes: 0.00 B/s, out bytes: 0.00 B/s', [
                        ('bytes_in', 0.0, None, None, None, None),
                        ('bytes_out', 0.0, None, None, None, None)
                    ]
                )
            ]
        )
    ]
}
