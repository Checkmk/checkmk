#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = u'cisco_mem_asa64'

info = [[u'System memory', u'', u'1686331208']]

discovery = {'': [(u'System memory', {})]}

checks = {
    '': [
        (
            u'System memory', {
                'levels': (80.0, 90.0)
            }, [
                (
                    0, 'Usage: 0% - 0.00 B of 1.57 GB', [
                        ('mem_used_percent', 0.0, 80.0, 90.0, 0, None)
                    ]
                )
            ]
        )
    ]
}
