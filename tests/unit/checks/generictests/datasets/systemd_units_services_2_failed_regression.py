#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'systemd_units'


info = [['[list-unit-files]'],
        ['[all]'],
        ['UNIT', 'LOAD', 'ACTIVE', 'SUB', 'DESCRIPTION'],
        ['foo.service',
         'loaded',
         'failed',
         'failed',
         'Arbitrary',
         'Executable',
         'File',
         'Formats',
         'File',
         'System',
         'Automount',
         'Point'],
        ['bar.service', 'loaded', 'failed', 'failed', 'a', 'bar', 'service']]


discovery = {'': [], 'services': [], 'services_summary': [('Summary', {})]}


checks = {
    'services_summary': [
        ('Summary', {
            'else': 2,
            'states': {'active': 0, 'failed': 2, 'inactive': 0},
            'states_default': 2,
        }, [
            (0, 'Total: 2', []),
            (0, 'Disabled: 0', []),
            (0, 'Failed: 2', []),
            (2, '2 services failed (bar, foo)', []),
        ]),
    ],
}
