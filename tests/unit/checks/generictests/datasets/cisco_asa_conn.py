#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'cisco_asa_conn'


info = [[['0', 'interface 0'],
         ['1', 'interface 1'],
         ['2', 'interface 2'],
         ['3', 'interface 3']],
        [['0', '123.456.789.0'],
         ['1', '123.456.789.1'],
         ['2', '']],
        [['0', '1', '1'],
         ['1', '9', '7'],
         ['2', '1', '1'],
         ['3', '1', '1']]]


discovery = {'': [('0', None), ('2', None)]}


checks = {'': [('0',
                {},
                [(0, 'Name: interface 0', []),
                 (0, 'IP: 123.456.789.0', []),
                 (0, 'Status: up', [])]),
               ('2',
                {},
                [(0, 'Name: interface 2', []),
                 (2, 'IP: Not found!', []),
                 (0, 'Status: up', [])])]}
