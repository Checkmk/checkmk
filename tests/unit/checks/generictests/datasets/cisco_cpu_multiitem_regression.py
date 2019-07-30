# yapf: disable


checkname = 'cisco_cpu_multiitem'


info = [[[u'0', u'24']],
        []]


discovery = {'': [(u'0', {})]}


checks = {'': [(u'0',
                {'levels': (80.0, 90.0)},
                [(0,
                    'Utilization in the last 5 minutes: 24.0%',
                  [('util', 24.0, 80.0, 90.0, 0, 100)])])]}
