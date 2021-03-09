# -*- encoding: utf-8
# yapf: disable


checkname = u'websphere_mq_queues'


info = [[u'0', u'ABC-123-DEF'], [u'TEST-FOO', u'RUNNING']]


discovery = {'': [(u'ABC-123-DEF', 'websphere_mq_queues_default_levels')]}


checks = {'': [(u'ABC-123-DEF',
                {'message_count': (1000, 1200), 'message_count_perc': (80.0, 90.0)},
                [(0,
                  '0 messages in queue',
                  [('queue', 0, 1000.0, 1200.0, None, None)])])]}
