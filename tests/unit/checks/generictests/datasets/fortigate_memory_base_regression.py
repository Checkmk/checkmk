# -*- encoding: utf-8
# yapf: disable


checkname = 'fortigate_memory_base'


info = [[u'19', u'1887424']]


discovery = {'': [(None, 'fortigate_memory_base_default_levels')]}


checks = {'': [(None,
                (70, 80),
                [(0,
                  '19% (warn/crit at 70%/80%)',
                  [('mem_used', 367217213, 1352905523, 1546177740, 0, 1932722176)])])]}