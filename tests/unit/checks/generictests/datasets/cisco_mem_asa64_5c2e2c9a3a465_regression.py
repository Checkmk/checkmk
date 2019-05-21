# -*- encoding: utf-8
# yapf: disable


checkname = u'cisco_mem_asa64'


info = [[u'System memory', u'', u'1686331208']]


discovery = {'': [(u'System memory', {})]}


checks = {'': [(u'System memory',
                {'levels': (80.0, 90.0)},
                [(0,
                  '0.0% (0.00 B) of 1.57 GB used',
                  [('mem_used', 0.0, 80.0, 90.0, 0, 100)])])]}