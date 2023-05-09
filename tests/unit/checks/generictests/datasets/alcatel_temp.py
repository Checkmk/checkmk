#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'alcatel_temp'

info = [['10', '20'], ['11', '21'], ['12', '22']]

discovery = {
    '': [('Slot 1 Board', {}), ('Slot 1 CPU', {}), ('Slot 2 Board', {}), ('Slot 2 CPU', {}),
         ('Slot 3 Board', {}), ('Slot 3 CPU', {})]
}

checks = {
    '': [('Slot 1 Board', {
        'levels': (45, 50)
    }, [(0, u'10 \xb0C', [('temp', 10, 45, 50, None, None)])]),
         ('Slot 1 CPU', {
             'levels': (45, 50)
         }, [(0, u'20 \xb0C', [('temp', 20, 45, 50, None, None)])]),
         ('Slot 2 Board', {
             'levels': (45, 50)
         }, [(0, u'11 \xb0C', [('temp', 11, 45, 50, None, None)])]),
         ('Slot 2 CPU', {
             'levels': (45, 50)
         }, [(0, u'21 \xb0C', [('temp', 21, 45, 50, None, None)])]),
         ('Slot 3 Board', {
             'levels': (45, 50)
         }, [(0, u'12 \xb0C', [('temp', 12, 45, 50, None, None)])]),
         ('Slot 3 CPU', {
             'levels': (45, 50)
         }, [(0, u'22 \xb0C', [('temp', 22, 45, 50, None, None)])])]
}
