

checkname = 'nfsmounts'


info = [['/path/to/share', 'ok', '1611668', '794767', '712899', '32768']]


parsed = {'/path/to/share': {'data': ['1611668', '794767', '712899', '32768'],
                             'state': 'ok'}}


discovery = {'': [('/path/to/share', {})]}


checks = {'': [('/path/to/share',
                'default',
                [(0, '55.8% used (27.43 GB of 49.18 GB)', [])])]}