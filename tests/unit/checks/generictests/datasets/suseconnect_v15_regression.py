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
    ['Installed Products', ''], ['Advanced Systems Management Module'],
    ['(sle-module-adv-systems-management/12/x86_64)'], ['Registered'],
    ['SUSE Linux Enterprise Server for SAP Applications 12 SP5'],
    ['(SLES_SAP/12.5/x86_64)'], ['Registered'], ['Subscription', ''],
    ['Regcode', ' banana005'], ['Starts at', ' 2018-07-01 00', '00', '00 UTC'],
    ['Expires at', ' 2021-06-30 00', '00', '00 UTC'], ['Status', ' ACTIVE'],
    ['Type', ' full'], ['SUSE Package Hub 12'], ['(PackageHub/12.5/x86_64)'],
    ['Registered']
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
                (0, 'Status: Registered', []), (0, 'Subscription: ACTIVE', []),
                (
                    0,
                    'Subscription type: full, Registration code: banana005, Starts at: 2018-07-01 00:00:00 UTC, Expires at: 2021-06-30 00:00:00 UTC',
                    []
                ), (0, 'Expires in: 350 d', [])
            ]
        )
    ]
}
