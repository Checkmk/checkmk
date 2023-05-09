#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'lnx_quota'


info = [
    ['[[[/]]]'],
    ['***', 'Report', 'for', 'user', 'quotas', 'on', 'device', '/dev/mapper/volume-root'],
    ['Block', 'grace', 'time:', '7days;', 'Inode', 'grace', 'time:', '7days'],
    ['Block', 'limits', 'File', 'limits'],
    ['User', 'used', 'soft', 'hard', 'grace', 'used', 'soft', 'hard', 'grace'],
    ['----------------------------------------------------------------------'],
    ['root', '--', '6003424', '0', '0', '0', '167394', '0', '0', '0'],
    ['[[[/quarktasche]]]'],
    ['***', 'Report', 'for', 'user', 'quotas', 'on', 'device', '/moo'],
    ['Block', 'grace', 'time:', '7days;', 'Inode', 'grace', 'time:', '7days'],
    ['Block', 'limits', 'File', 'limits'],
    ['User', 'used', 'soft', 'hard', 'grace', 'used', 'soft', 'hard', 'grace'],
    ['----------------------------------------------------------------------'],
    ['root', '--', '6003424', '0', '0', '0', '167394', '0', '100000000', '0'],
    ['[[[grp:/nussecke]]]'],
    ['***', 'Report', 'for', 'group', 'quotas', 'on', 'device', '/huiboo'],
    ['Block', 'grace', 'time:', '7days;', 'Inode', 'grace', 'time:', '7days'],
    ['Block', 'limits', 'File', 'limits'],
    ['User', 'used', 'soft', 'hard', 'grace', 'used', 'soft', 'hard', 'grace'],
    ['----------------------------------------------------------------------'],
    ['root', '--', '6003424', '0', '0', '0', '167394', '0', '100000000', '0'],
    ['www-data', '--', '4404688', '0', '0', '0', '49314', '31415', '100000000', '0'],
]


discovery = {
    '': [
        ('/', {'user': True, 'group': False}),
        ('/quarktasche', {'user': True, 'group': False}),
        ('/nussecke', {'user': False, 'group': True}),
    ],
}


checks = {
    '': [
        ('/', {'user': True}, [
            (0, 'All users within quota limits', []),
        ]),
        ('/quarktasche', {'user': True}, [
            (0, 'All users within quota limits', []),
        ]),
        ('/nussecke', {'user': False, 'group': True}, [
            (1, 'Group www-data exceeded file soft limit 49314/31415', []),
        ]),
    ],
}
