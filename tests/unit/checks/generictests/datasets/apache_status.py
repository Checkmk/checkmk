# -*- encoding: utf-8
# yapf: disable

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
    '': [(u'MY CHECK MK', {}, [(
        0,
        u'Uptime: 27 h, IdleWorkers: 49, BusyWorkers: 1, OpenSlots: 100, TotalSlots: 150, CPULoad: 0.00, ReqPerSec: 0.00, BytesPerReq: 1657.38, BytesPerSec: 0.00, States: (Waiting: 49, SendingReply: 1), ConnsTotal: 0, ConnsAsyncWriting: 0, ConnsAsyncKeepAlive: 0, ConnsAsyncClosing: 0',
        [(u'Uptime', 99739, None, None, None, None), (u'IdleWorkers', 49, None, None, None, None),
         (u'BusyWorkers', 1, None, None, None, None), ('OpenSlots', 100, None, None, None, None),
         ('TotalSlots', 150, None, None, None, None),
         (u'CPULoad', 0.00482259, None, None, None, None),
         (u'ReqPerSec', 0.0, None, None, None, None),
         (u'BytesPerReq', 1657.38, None, None, None, None),
         (u'BytesPerSec', 0.0, None, None, None, None),
         ('State_StartingUp', 0, None, None, None, None),
         ('State_Waiting', 49, None, None, None, None),
         ('State_Logging', 0, None, None, None, None), ('State_DNS', 0, None, None, None, None),
         ('State_SendingReply', 1, None, None, None, None),
         ('State_ReadingRequest', 0, None, None, None, None),
         ('State_Closing', 0, None, None, None, None),
         ('State_IdleCleanup', 0, None, None, None, None),
         ('State_Finishing', 0, None, None, None, None),
         ('State_Keepalive', 0, None, None, None, None), (u'ConnsTotal', 0, None, None, None, None),
         (u'ConnsAsyncWriting', 0, None, None, None, None),
         (u'ConnsAsyncKeepAlive', 0, None, None, None, None),
         (u'ConnsAsyncClosing', 0, None, None, None, None)])])]
}
