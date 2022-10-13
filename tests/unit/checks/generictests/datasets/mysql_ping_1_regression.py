#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'mysql_ping'


info = [
    ['this', 'line', 'is', 'no', 'longer', 'ignored'],
    ['[[elephant]]'],
    ['mysqladmin:', 'connect', 'to', 'server', 'at', "'localhost'", 'failed'],
    ['[[moth]]'],
    ['mysqld', 'is', 'alive'],
]


discovery = {
    '': [
        ('mysql', {}),
        ('elephant', {}),
        ('moth', {}),
    ],
}


checks = {
    '': [
        ('mysql', {}, [(2, 'this line is no longer ignored', [])]),
        ('elephant', {}, [(2, "mysqladmin: connect to server at 'localhost' failed", [])]),
        ('moth', {}, [(0, 'MySQL Daemon is alive', [])]),
    ],
}
