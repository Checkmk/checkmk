#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore


checkname = 'apache_status'

info = [
    [u'127.0.0.1', u'None', u'127.0.0.1'],
    [u'127.0.0.1', u'None', u'ServerVersion:', u'Apache/2.4.29', u'(Ubuntu)'],
    [u'127.0.0.1', u'None', u'ServerMPM:', u'event'],
    [u'127.0.0.1', u'None', u'Server', u'Built:', u'2019-07-16T18:14:45'],
    [u'127.0.0.1', u'None', u'CurrentTime:', u'Wednesday,', u'14-Aug-2019', u'10:46:26', u'CEST'],
    [u'127.0.0.1', u'None', u'RestartTime:', u'Monday,', u'12-Aug-2019', u'11:28:34', u'CEST'],
    [u'127.0.0.1', u'None', u'ParentServerConfigGeneration:', u'9'],
    [u'127.0.0.1', u'None', u'ParentServerMPMGeneration:', u'8'],
    [u'127.0.0.1', u'None', u'ServerUptimeSeconds:', u'170272'],
    [
        u'127.0.0.1', u'None', u'ServerUptime:', u'1', u'day', u'23', u'hours', u'17', u'minutes',
        u'52', u'seconds'
    ], [u'127.0.0.1', u'None', u'Load1:', u'0.70'], [u'127.0.0.1', u'None', u'Load5:', u'0.66'],
    [u'127.0.0.1', u'None', u'Load15:', u'0.67'],
    [u'127.0.0.1', u'None', u'Total', u'Accesses:', u'64265'],
    [u'127.0.0.1', u'None', u'Total', u'kBytes:', u'105614'],
    [u'127.0.0.1', u'None', u'CPUUser:', u'.34'], [u'127.0.0.1', u'None', u'CPUSystem:', u'.15'],
    [u'127.0.0.1', u'None', u'CPUChildrenUser:', u'0'],
    [u'127.0.0.1', u'None', u'CPUChildrenSystem:', u'0'],
    [u'127.0.0.1', u'None', u'CPULoad:', u'.000287775'],
    [u'127.0.0.1', u'None', u'Uptime:', u'170272'],
    [u'127.0.0.1', u'None', u'ReqPerSec:', u'.377426'],
    [u'127.0.0.1', u'None', u'BytesPerSec:', u'635.153'],
    [u'127.0.0.1', u'None', u'BytesPerReq:', u'1682.86'],
    [u'127.0.0.1', u'None', u'BusyWorkers:', u'1'], [u'127.0.0.1', u'None', u'IdleWorkers:', u'49'],
    [u'127.0.0.1', u'None', u'ConnsTotal:', u'1'],
    [u'127.0.0.1', u'None', u'ConnsAsyncWriting:', u'0'],
    [u'127.0.0.1', u'None', u'ConnsAsyncKeepAlive:', u'0'],
    [u'127.0.0.1', u'None', u'ConnsAsyncClosing:', u'0'],
    [
        u'127.0.0.1', u'None', u'Scoreboard:',
        u'__________________________________W_______________....................................................................................................'
    ]
]

discovery = {'': [(u'127.0.0.1', {})]}

checks = {
    '': [
        (u'127.0.0.1', {}, [
            (0, 'Uptime: 47 h', [(u'Uptime', 170272)]),
            (0, 'Idle workers: 49', [(u'IdleWorkers', 49)]),
            (0, 'Busy workers: 1', [(u'BusyWorkers', 1)]),
            (0, 'Total slots: 150', [('TotalSlots', 150)]),
            (0, 'Open slots: 100', [('OpenSlots', 100)]),
            (0, 'CPU load: 0.00', [(u'CPULoad', 0.000287775)]),
            (0, 'Requests per second: 0.00', [(u'ReqPerSec', 0.0)]),
            (0, 'Bytes per request: 1682.86', [(u'BytesPerReq', 1682.86)]),
            (0, 'Bytes per second: 0.00', [(u'BytesPerSec', 0.0)]),
            (0, 'Total connections: 1', [(u'ConnsTotal', 1)]),
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
