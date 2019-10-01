# -*- encoding: utf-8
# yapf: disable


checkname = 'juniper_screenos_mem'


info = [[u'157756272', u'541531248']]


discovery = {'': [(None, 'juniper_mem_default_levels')]}


checks = {'': [(None,
                (80.0, 90.0),
                [(0,
                  'Used: 150.45 MB/666.89 MB (23%)',
                  [('usage', 157755392, 559429222.4, 629357875.2, 0, 699286528)])])]}