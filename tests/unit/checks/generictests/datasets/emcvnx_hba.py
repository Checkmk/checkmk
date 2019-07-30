# -*- encoding: utf-8
# yapf: disable


checkname = 'emcvnx_hba'


parsed = {u'SP A Port 0': {u'Blocks Read': 0, u'Blocks Written': 0},
          u'SP B Port 0': {},
          u'SP B Port 3': {}}


discovery = {'': [(u'SP A Port 0', None)]}


checks = {'': [(u'SP A Port 0',
                {},
                [(0,
                  'Read: 0 Blocks/s, Write: 0 Blocks/s',
                  [('read_blocks', 0, None, None, None, None),
                   ('write_blocks', 0, None, None, None, None)])])]}