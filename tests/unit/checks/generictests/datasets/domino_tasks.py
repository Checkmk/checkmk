# -*- encoding: utf-8
# yapf: disable


checkname = 'domino_tasks'


info = [[u'Node', u'Directory Indexer'],
        [u'Node', u'DAOS Manager'],
        [u'Node', u'DAOS Manager'],
        [u'Node', u'Event Monitor']]


discovery = {'': [('DAOS Manager',
                   {'cgroup': (None, False),
                    'cpu_rescale_max': None,
                    'levels': (1, 3, 6, 20),
                    'match_groups': (),
                    'process': 'DAOS Manager',
                    'user': None})]}


checks = {'': [('DAOS Manager',
                {'cgroup': (None, False),
                 'cpu_rescale_max': None,
                 'levels': (1, 3, 6, 20),
                 'match_groups': (),
                 'process': 'DAOS Manager',
                 'user': None},
                [(1,
                  u'2 Taskses: (ok from 3 to 6) [running on Node]',
                  [('count', 2, 7, 21, 0, None)]),
                 (0, '0.0% CPU', [('pcpu', 0.0, None, None, None, None)])])]}


mock_host_conf = {'': {'cpu_rescale_max': None,
                       'descr': 'DAOS Manager',
                       'levels': (1, 3, 6, 20),
                       'match': 'DAOS Manager'}}