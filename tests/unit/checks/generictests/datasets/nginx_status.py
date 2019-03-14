# yapf: disable


checkname = 'nginx_status'


info = [['127.0.0.1', '80', 'Active', 'connections:', '1'],
        ['127.0.0.1', '80', 'serveracceptshandledrequests'],
        ['127.0.0.1', '80', '12', '12', '12'],
        ['127.0.0.1', '80', 'Reading:', '0', 'Writing:', '1', 'Waiting:', '0']]


discovery = {'': [('127.0.0.1:80', {})]}


checks = {'': [('127.0.0.1:80',
                {},
                [(0,
                  'Active: 1 (0 reading, 1 writing, 0 waiting), Requests: 0.00/s (1.00/Connection), Accepted/Handled: 0.00/s',
                  [('accepted', 12, None, None, None, None),
                   ('accepted_per_sec', 0.0, None, None, None, None),
                   ('active', 1, None, None, None, None),
                   ('handled', 12, None, None, None, None),
                   ('handled_per_sec', 0.0, None, None, None, None),
                   ('reading', 0, None, None, None, None),
                   ('requests', 12, None, None, None, None),
                   ('requests_per_conn', 1, None, None, None, None),
                   ('requests_per_sec', 0.0, None, None, None, None),
                   ('waiting', 0, None, None, None, None),
                   ('writing', 1, None, None, None, None)])])]}