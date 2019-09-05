# -*- encoding: utf-8
# yapf: disable


checkname = 'datapower_tcp'


info = [[u'1.0', u'10'],
        [u'2.0', u'2'],
        [u'3.0', u'0'],
        [u'4.0', u'0'],
        [u'5.0', u'0'],
        [u'6.0', u'15'],
        [u'7.0', u'0'],
        [u'8.0', u'0'],
        [u'9.0', u'0'],
        [u'10.0', u'24'],
        [u'11.0', u'0']]


discovery = {'': [(None, 'tcp_conn_stats_default_levels')]}


checks = {'': [(None,
                {},
                [(0, 'ESTABLISHED: 10', []),
                 (0, 'TIME_WAIT: 15', []),
                 (0, 'SYN_SENT: 2', []),
                 (0, 'LISTEN: 24', []),
                 (0,
                  '',
                  [('ESTABLISHED', 10, None, None, None, None),
                   ('SYN_RECV', 0, None, None, None, None),
                   ('CLOSING', 0, None, None, None, None),
                   ('CLOSE_WAIT', 0, None, None, None, None),
                   ('FIN_WAIT2', 0, None, None, None, None),
                   ('FIN_WAIT1', 0, None, None, None, None),
                   ('LAST_ACK', 0, None, None, None, None),
                   ('TIME_WAIT', 15, None, None, None, None),
                   ('CLOSED', 0, None, None, None, None),
                   ('SYN_SENT', 2, None, None, None, None),
                   ('LISTEN', 24, None, None, None, None)])])]}