#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore


checkname = 'apache_status'

info = [
    [u'127.0.0.1', u'None', u'MY CHECK MK', u'127.0.0.1'],
    [u'127.0.0.1', u'None', u'MY CHECK MK', u'ServerVersion: Apache/2.4.29 (Ubuntu)'],
    [u'127.0.0.1', u'None', u'MY CHECK MK', u'ServerMPM: event'],
    [u'127.0.0.1', u'None', u'MY CHECK MK', u'Server Built: 2019-07-16T18:14:45'],
    [u'127.0.0.1', u'None', u'MY CHECK MK', u'CurrentTime: Tuesday, 13-Aug-2019 15:10:54 CEST'],
    [u'127.0.0.1', u'None', u'MY CHECK MK', u'RestartTime: Monday, 12-Aug-2019 11:28:34 CEST'],
    [u'127.0.0.1', u'None', u'MY CHECK MK', u'ParentServerConfigGeneration: 6'],
    [u'127.0.0.1', u'None', u'MY CHECK MK', u'ParentServerMPMGeneration: 5'],
    [u'127.0.0.1', u'None', u'MY CHECK MK', u'ServerUptimeSeconds: 99739'],
    [u'127.0.0.1', u'None', u'MY CHECK MK', u'ServerUptime: 1 day 3 hours 42 minutes 19 seconds'],
    [u'127.0.0.1', u'None', u'MY CHECK MK', u'Load1: 0.70'],
    [u'127.0.0.1', u'None', u'MY CHECK MK', u'Load5: 0.70'],
    [u'127.0.0.1', u'None', u'MY CHECK MK', u'Load15: 0.58'],
    [u'127.0.0.1', u'None', u'MY CHECK MK', u'Total Accesses: 62878'],
    [u'127.0.0.1', u'None', u'MY CHECK MK', u'Total kBytes: 101770'],
    [u'127.0.0.1', u'None', u'MY CHECK MK', u'CPUUser: 2.99'],
    [u'127.0.0.1', u'None', u'MY CHECK MK', u'CPUSystem: 1.82'],
    [u'127.0.0.1', u'None', u'MY CHECK MK', u'CPUChildrenUser: 0'],
    [u'127.0.0.1', u'None', u'MY CHECK MK', u'CPUChildrenSystem: 0'],
    [u'127.0.0.1', u'None', u'MY CHECK MK', u'CPULoad: .00482259'],
    [u'127.0.0.1', u'None', u'MY CHECK MK', u'Uptime: 99739'],
    [u'127.0.0.1', u'None', u'MY CHECK MK', u'ReqPerSec: .630425'],
    [u'127.0.0.1', u'None', u'MY CHECK MK', u'BytesPerSec: 1044.85'],
    [u'127.0.0.1', u'None', u'MY CHECK MK', u'BytesPerReq: 1657.38'],
    [u'127.0.0.1', u'None', u'MY CHECK MK', u'BusyWorkers: 1'],
    [u'127.0.0.1', u'None', u'MY CHECK MK', u'IdleWorkers: 49'],
    [u'127.0.0.1', u'None', u'MY CHECK MK', u'ConnsTotal: 0'],
    [u'127.0.0.1', u'None', u'MY CHECK MK', u'ConnsAsyncWriting: 0'],
    [u'127.0.0.1', u'None', u'MY CHECK MK', u'ConnsAsyncKeepAlive: 0'],
    [u'127.0.0.1', u'None', u'MY CHECK MK', u'ConnsAsyncClosing: 0'],
    [
        u'127.0.0.1', u'None', u'MY CHECK MK',
        u'Scoreboard: ________________________________W_________________....................................................................................................'
    ]
]

discovery = {'': [(u'MY CHECK MK', {})]}

checks = {
    '': [
        ('MY CHECK MK', {}, [
            (0, 'Uptime: 27 h', [(u'Uptime', 99739)]),
            (0, 'Idle workers: 49', [(u'IdleWorkers', 49)]),
            (0, 'Busy workers: 1', [(u'BusyWorkers', 1)]),
            (0, 'Total slots: 150', [('TotalSlots', 150)]),
            (0, 'Open slots: 100', [('OpenSlots', 100)]),
            (0, 'CPU load: 0.00', [(u'CPULoad', 0.00482259)]),
            (0, 'Requests per second: 0.00', [(u'ReqPerSec', 0.0)]),
            (0, 'Bytes per request: 1657.38', [(u'BytesPerReq', 1657.38)]),
            (0, 'Bytes per second: 0.00', [(u'BytesPerSec', 0.0)]),
            (0, 'Total connections: 0', [(u'ConnsTotal', 0)]),
            (0, 'Async writing connections: 0', [(u'ConnsAsyncWriting', 0)]),
            (0, 'Async keep alive connections: 0', [(u'ConnsAsyncKeepAlive', 0)]),
            (0, 'Async closing connections: 0', [(u'ConnsAsyncClosing', 0)]),
            (0, ('\nScoreboard states:'
                 '\n  Waiting: 49'
                 '\n  SendingReply: 1'), [
                ('State_Waiting', 49),
                ('State_StartingUp', 0),
                ('State_ReadingRequest', 0),
                ('State_SendingReply', 1),
                ('State_Keepalive', 0),
                ('State_DNS', 0),
                ('State_Closing', 0),
                ('State_Logging', 0),
                ('State_Finishing', 0),
                ('State_IdleCleanup', 0),
            ]),
        ]),
    ],
}
