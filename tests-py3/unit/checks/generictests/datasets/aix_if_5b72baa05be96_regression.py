#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = u'aix_if'


info = [[u'[en3]'],
        [u'Hardware', u'Address:', u'00:AA:BB:CC:DD:EE'],
        [u'Packets:', u'38832476370', u'Packets:', u'4125941951'],
        [u'Bytes:', u'57999949458755', u'Bytes:', u'627089523952']]


discovery = {'': [('1', "{'state': ['1'], 'speed': 0}")]}


checks = {'': [('1',
                {'errors': (0.01, 0.1), 'speed': 0, 'state': ['1']},
                [(0, '[en3] (up) MAC: 00:AA:BB:CC:DD:EE, speed unknown', [])])]}
