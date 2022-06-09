#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

from cmk.base.plugins.agent_based import suseconnect

checkname = 'suseconnect'

freeze_time = '2020-07-15T00:00:00'

parsed = suseconnect.parse_suseconnect([
    ['identifier', ' SLES'], ['version', ' 12.1'], ['arch', ' x86_64'],
    ['status', ' Registered'], ['regcode', ' banana001'],
    ['starts_at', ' 2015-12-01 00', '00', '00 UTC'],
    ['expires_at', ' 2019-12-31 00', '00', '00 UTC'],
    ['subscription_status', ' ACTIVE'], ['type', ' full']
])

discovery = {'': [(None, {})]}

checks = {
    '': [
        (
            None, {
                'status': 'Registered',
                'subscription_status': 'ACTIVE',
                'days_left': (14, 7)
            }, [
                (0, 'Status: Registered', []),
                (0, 'Subscription: ACTIVE', []),
                (
                    0,
                    'Subscription type: full, Registration code: banana001, Starts at: 2015-12-01 00:00:00 UTC, Expires at: 2019-12-31 00:00:00 UTC',
                    []
                ), (2, 'Expired since: 197 d', [])
            ]
        )
    ]
}
