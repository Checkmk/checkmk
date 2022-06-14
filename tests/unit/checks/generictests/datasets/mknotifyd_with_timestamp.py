#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'mknotifyd'

info = [
    [u'1571212728'],
    [u'[heute]'],
    [u'Version:         2019.10.14'],
    [u'Updated:         1571212726 (2019-10-16 09:58:46)'],
    [u'Started:         1571143926 (2019-10-15 14:52:06, 68800 sec ago)'],
    [u'Configuration:   1571143926 (2019-10-15 14:52:06, 68800 sec ago)'],
    [u'Listening FD:    5'],
    [u'Spool:           New'],
    [u'Count:           0'],
    [u'Oldest:'],
    [u'Youngest:'],
    [u'Spool:           Deferred'],
    [u'Count:           0'],
    [u'Oldest:'],
    [u'Youngest:'],
    [u'Spool:           Corrupted'],
    [u'Count:           0'],
    [u'Oldest:'],
    [u'Youngest:'],
    [u'Queue:           mail'],
    [u'Waiting:         0'],
    [u'Processing:      0'],
    [u'Queue:           None'],
    [u'Waiting:         0'],
    [u'Processing:      0'],
    [u'Connection:               127.0.0.1:49850'],
    [u'Type:                     incoming'],
    [u'State:                    established'],
    [u'Since:                    1571143941 (2019-10-15 14:52:21, 68785 sec ago)'],
    [u'Notifications Sent:       47'],
    [u'Notifications Received:   47'],
    [u'Pending Acknowledgements:'],
    [u'Socket FD:                6'],
    [u'HB. Interval:             10 sec'],
    [u'LastIncomingData:         1571212661 (2019-10-16 09:57:41, 65 sec ago)'],
    [u'LastHeartbeat:            1571212717 (2019-10-16 09:58:37, 9 sec ago)'],
    [u'InputBuffer:              0 Bytes'],
    [u'OutputBuffer:             0 Bytes'],
]

discovery = {
    '': [(u'heute', {})],
    'connection': [(u'heute-127.0.0.1', {})],
}

checks = {
    '': [(
        u'heute',
        {},
        [
            (0, u'Version: 2019.10.14', []),
            (0, 'Spooler running', [('last_updated', 2, None, None, None, None),
                                    ('new_files', 0, None, None, None, None)]),
        ],
    )],
    'connection': [(
        u'heute-127.0.0.1',
        {},
        [
            (0, 'Alive', []),
            (0, 'Uptime: 19 hours 6 minutes', []),
            (0, '47 Notifications sent', []),
            (0, '47 Notifications received', []),
        ],
    )]
}
