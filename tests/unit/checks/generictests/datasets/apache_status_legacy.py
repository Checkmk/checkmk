# -*- encoding: utf-8
# yapf: disable

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
    '': [(u'127.0.0.1', {}, [(
        0,
        u'Uptime: 47 h, IdleWorkers: 49, BusyWorkers: 1, OpenSlots: 100, TotalSlots: 150, CPULoad: 0.00, ReqPerSec: 0.00, BytesPerReq: 1682.86, BytesPerSec: 0.00, States: (Waiting: 49, SendingReply: 1), ConnsTotal: 1, ConnsAsyncWriting: 0, ConnsAsyncKeepAlive: 0, ConnsAsyncClosing: 0',
        [(u'Uptime', 170272, None, None, None, None), (u'IdleWorkers', 49, None, None, None, None),
         (u'BusyWorkers', 1, None, None, None, None), ('OpenSlots', 100, None, None, None, None),
         ('TotalSlots', 150, None, None, None, None),
         (u'CPULoad', 0.000287775, None, None, None, None),
         (u'ReqPerSec', 0.0, None, None, None, None),
         (u'BytesPerReq', 1682.86, None, None, None, None),
         (u'BytesPerSec', 0.0, None, None, None, None),
         ('State_StartingUp', 0, None, None, None, None),
         ('State_Waiting', 49, None, None, None, None),
         ('State_Logging', 0, None, None, None, None), ('State_DNS', 0, None, None, None, None),
         ('State_SendingReply', 1, None, None, None, None),
         ('State_ReadingRequest', 0, None, None, None, None),
         ('State_Closing', 0, None, None, None, None),
         ('State_IdleCleanup', 0, None, None, None, None),
         ('State_Finishing', 0, None, None, None, None),
         ('State_Keepalive', 0, None, None, None, None), (u'ConnsTotal', 1, None, None, None, None),
         (u'ConnsAsyncWriting', 0, None, None, None, None),
         (u'ConnsAsyncKeepAlive', 0, None, None, None, None),
         (u'ConnsAsyncClosing', 0, None, None, None, None)])])]
}
