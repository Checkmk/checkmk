# -*- encoding: utf-8
# yapf: disable


checkname = 'juniper_trpz_flash'


info = [[u'51439616', u'62900224']]


discovery = {'': [(None, 'juniper_trpz_flash_default_levels')]}


checks = {'': [(None,
                (90.0, 95.0),
                [(0,
                  'Used: 49.06 MB of 59.99 MB ',
                  [('used', 51439616.0, 56610201.6, 59755212.8, 0, 62900224.0)])])]}