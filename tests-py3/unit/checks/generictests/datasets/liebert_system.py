#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'liebert_system'


info = [
    [u'System Status', u'Normal with Warning'],
    [u'System Model Number', u'Liebert HPC'],
    [u'Unit Operating State', u'standby'],
    [u'Unit Operating State Reason', u'Reason Unknown'],
]


discovery = {
    '': [
        (u'Liebert HPC', {}),
    ],
}


checks = {
    '': [
        (u'Liebert HPC', {}, [
            (0, u'System Model Number: Liebert HPC', []),
            (2, u'System Status: Normal with Warning', []),
            (0, u'Unit Operating State: standby', []),
            (0, u'Unit Operating State Reason: Reason Unknown', []),
        ]),
    ],
}
