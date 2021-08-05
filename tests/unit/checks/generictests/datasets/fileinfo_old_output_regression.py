#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'fileinfo'

info = [
    ['1536557964'],
    ['regular.txt', '4242', '1536421281'],
    ['missing_file.txt', 'missing'],
    ['not_readable.txt', 'not readable', '1536421281'],
    ['stat_failes.txt', '', '', '0000'],
]

discovery = {
    '': [('not_readable.txt', {}), ('regular.txt', {}), ('stat_failes.txt', {})],
    'groups': []
}

checks = {
    '': [('regular.txt', {}, [(0, 'Size: 4242 B', [('size', 4242, None, None, None, None)]),
                              (0, 'Age: 37 h', [('age', 136683, None, None, None, None)])]),
         ('missinf_file.txt', {}, [(3, 'File not found', [])]),
         ('not_readable.txt', {}, [(1, 'File stat failed', [])]),
         ('stat_failes.txt', {}, [(1, 'File stat failed', [])])],
}
