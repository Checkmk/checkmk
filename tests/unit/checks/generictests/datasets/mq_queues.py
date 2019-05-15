# -*- encoding: utf-8
# yapf: disable


checkname = 'mq_queues'


info = [[u'[[Queue_App1_App2]]'], [u'1', u'2', u'3', u'4']]


discovery = {'': [(u'Queue_App1_App2',
                   {'consumerCount': (None, None), 'size': (None, None)})]}


checks = {'': [(u'Queue_App1_App2',
                {'consumerCount': (None, None), 'size': (None, None)},
                [(0,
                  'Queue Size: 1, Enqueue Count: 3, Dequeue Count: 4',
                  [('queue', 1, None, None, None, None),
                   ('enque', 3, None, None, None, None),
                   ('deque', 4, None, None, None, None)])])]}
