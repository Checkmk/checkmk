#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'veeam_tapejobs'


info = [
    ['JobName', 'JobID', 'LastResult', 'LastState'],
    ['Job One', '1', 'Success', 'Stopped'],
    ['Job Two', '2', 'Warning', 'Stopped'],
    ['Job Three', '3', 'Failed', 'Stopped'],
    ['Job Four', '4', 'None', 'Working'],
    ['Job Five (older)', '5', 'None', 'Working'],
    ['Job Six', '6', 'None', 'Idle'],
    ['Job Seven (older)', '7', 'None', 'Idle'],
]


freeze_time = "2019-07-02 08:41:17"


mock_item_state = {
    '': {
        '4.running_since': 1562056000,
        '5.running_since': 1560006000,
        '6.running_since': 1562056000,
        '7.running_since': 1560006000,
    }
}


discovery = {
    '': [
        ('Job One', 'veeam_tapejobs_default_levels'),
        ('Job Two', 'veeam_tapejobs_default_levels'),
        ('Job Three', 'veeam_tapejobs_default_levels'),
        ('Job Four', 'veeam_tapejobs_default_levels'),
        ('Job Five (older)', 'veeam_tapejobs_default_levels'),
        ('Job Six', 'veeam_tapejobs_default_levels'),
        ('Job Seven (older)', 'veeam_tapejobs_default_levels'),
    ],
}


checks = {
    '': [
        ('Job One', (86400, 172800), [
            (0, 'Last backup result: Success', []),
            (0, 'Last state: Stopped', []),
        ]),
        ('Job Two', (86400, 172800), [
            (1, 'Last backup result: Warning', []),
            (0, 'Last state: Stopped', []),
        ]),
        ('Job Three', (86400, 172800), [
            (2, 'Last backup result: Failed', []),
            (0, 'Last state: Stopped', []),
        ]),
        ('Job Four', (86400, 172800), [
            (0, 'Backup in progress since 2019-07-02 10:26:40 (currently working)', []),
            (0, 'Running time: 14 minutes 37 seconds', []),
        ]),
        ('Job Five (older)', (86400, 172800), [
            (0, 'Backup in progress since 2019-06-08 17:00:00 (currently working)', []),
            (2, 'Running time: 23 days 17 hours (warn/crit at 1 day 0 hours/2 days 0 hours)', []),
        ]),
        ('Job Six', (86400, 172800), [
            (0, 'Backup in progress since 2019-07-02 10:26:40 (currently idle)', []),
            (0, 'Running time: 14 minutes 37 seconds', []),
        ]),
        ('Job Seven (older)', (86400, 172800), [
            (0, 'Backup in progress since 2019-06-08 17:00:00 (currently idle)', []),
            (2, 'Running time: 23 days 17 hours (warn/crit at 1 day 0 hours/2 days 0 hours)', []),
        ]),
    ],
}
