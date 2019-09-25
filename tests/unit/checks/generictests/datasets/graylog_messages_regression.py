# -*- encoding: utf-8
# yapf: disable


checkname = 'graylog_messages'


info = [[u'{"events": 8569688}']]


discovery = {'': [(None, {})]}


checks = {'': [(None,
                {},
                [(0,
                  'Total number of messages: 8569688',
                  [('messages', 8569688, None, None, None, None)]),
                 (0,
                  'Average number of messages (30 m): 0.00',
                  [('msgs_avg', 0, None, None, None, None)])])]}