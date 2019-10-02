# -*- encoding: utf-8
# yapf: disable


checkname = 'nginx_status'


freeze_time = '2019-10-02 08:15:35'


info = [['127.0.0.1', '80', 'Active', 'connections:', '10'],
        ['127.0.0.1', '80', 'serveracceptshandledrequests'],
        ['127.0.0.1', '80', '12', '10', '120'],
        ['127.0.0.1', '80', 'Reading:', '2', 'Writing:', '1', 'Waiting:', '3'],
        ['127.0.1.1', '80', 'Active', 'connections:', '24'],
        ['127.0.1.1', '80', 'server', 'accepts', 'handled', 'requests'],
        ['127.0.1.1', '80', '23', '42', '323'],
        ['127.0.1.1', '80', 'Reading:', '1', 'Writing:', '5', 'Waiting:', '0']]


discovery = {'': [('127.0.0.1:80', {}), ('127.0.1.1:80', {})]}


checks = {'': [('127.0.0.1:80',
                {},
                [(0,
                  'Active: 10 (2 reading, 1 writing, 3 waiting), Requests: 0.02/s (12.00/Connection), Accepted: 0.00/s, Handled: 0.00/s',
                  [('accepted', 12, None, None, None, None),
                   ('active', 10, None, None, None, None),
                   ('handled', 10, None, None, None, None),
                   ('reading', 2, None, None, None, None),
                   ('requests', 120, None, None, None, None),
                   ('waiting', 3, None, None, None, None),
                   ('writing', 1, None, None, None, None)])]),
               ('127.0.1.1:80',
                {},
                [(0,
                  'Active: 24 (1 reading, 5 writing, 0 waiting), Requests: 0.05/s (7.00/Connection), Accepted: 0.00/s, Handled: 0.01/s',
                  [('accepted', 23, None, None, None, None),
                   ('active', 24, None, None, None, None),
                   ('handled', 42, None, None, None, None),
                   ('reading', 1, None, None, None, None),
                   ('requests', 323, None, None, None, None),
                   ('waiting', 0, None, None, None, None),
                   ('writing', 5, None, None, None, None)])])]}


mock_item_state = {'': (1569996970, 0)}