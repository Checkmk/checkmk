#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'logwatch'

parsed = {None: {
    'errors': [],
    'logfiles': {
        'mylog': {
            'attr': 'ok',
            'lines': ['C whoha! Someone mooped!'],
        },
        'missinglog': {
            'attr': 'missing',
            'lines': [],
        },
        'unreadablelog': {
            'attr': 'cannotopen',
            'lines': [],
        },
        'empty.log': {
            'attr': 'ok',
            'lines': [],
        },
        'my_other_log': {
            'attr': 'ok',
            'lines': ['W watch your step!'],
        },
    },
}}

discovery = {
    '': [
        ('empty.log', {}),
        ('my_other_log', {}),
        ('mylog', {})],
    'ec': [],
    'ec_single': [],
    'groups': []}


checks = {
    '': [
        ('empty.log', [{'reclassify_patterns': []}], [
            (0, 'no error messages', []),
        ]),
        ('my_other_log', [{'reclassify_patterns': []}], [
            (1, '1 WARN messages (Last worst: "watch your step!")', []),
        ]),
        ('mylog', [{'reclassify_patterns': []}], [
            (2, '1 CRIT messages (Last worst: "whoha! Someone mooped!")', []),
        ]),
    ],
}
