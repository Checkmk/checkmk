#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'logwatch'


info = [[None, '[[[mylog]]]'],
        [None, 'C', 'whoha!', 'Someone', 'mooped!'],
        [None, '[[[missinglog:missing]]]'],
        [None, '[[[unreadablelog:cannotopen]]]'],
        [None, '[[[empty.log]]]'],
        [None, '[[[my_other_log]]]'],
        [None, 'W', 'watch', 'your', 'step!']]


discovery = {
    '': [
        ('empty.log', None),
        ('my_other_log', None),
        ('mylog', None)],
    'ec': [],
    'ec_single': [],
    'groups': []}


checks = {
    '': [
        ('empty.log', {}, [
            (0, 'no error messages', []),
        ]),
        ('my_other_log', {}, [
            (1, '1 WARN messages (Last worst: "watch your step!")', []),
        ]),
        ('mylog', {}, [
            (2, '1 CRIT messages (Last worst: "whoha! Someone mooped!")', []),
        ]),
    ],
}
