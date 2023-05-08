#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'jenkins_instance'

info = [
    [
        u'{"quietingDown": false, "nodeDescription": "the master Jenkins node", "numExecutors": 10, "mode": "NORMAL", "_class": "hudson.model.Hudson", "useSecurity": true}'
    ]
]

discovery = {'': [(None, {})]}

checks = {
    '': [
        (
            None, {}, [
                (0, u'Description: The Master Jenkins Node', []),
                (0, 'Quieting Down: no', []), (0, 'Security used: yes', [])
            ]
        )
    ]
}
