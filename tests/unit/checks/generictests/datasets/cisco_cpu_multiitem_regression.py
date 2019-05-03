# yapf: disable


checkname = 'cisco_cpu_multiitem'


info = [[[u'0', u'24']],
        []]


discovery = {'': [(u'0', {})]}


checks = {'': [(u'0',
                {'levels': (80.0, 90.0)},
                [(0,
                  '24.0% utilization in the last 5 minutes',
                  [('util', 24.0, 80.0, 90.0, 0, 100)])])]}
