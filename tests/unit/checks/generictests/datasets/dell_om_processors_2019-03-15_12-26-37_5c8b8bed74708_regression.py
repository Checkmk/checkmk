# -*- encoding: utf-8
# yapf: disable


checkname = u'dell_om_processors'


info = [[u'1', u'5', u'Intel', u'3', u'129'], [u'2', u'3', u'Intel', u'3', u'128']]


discovery = {'': [(u'1', None), (u'2', None)]}


checks = {'': [(u'1',
                {},
                [(3,
                  u'[Intel] CPU status: BIOS Disabled, CPU reading: unknown[129]',
                  [])]),
               (u'2',
                {},
                [(0, u'[Intel] CPU status: Enabled, CPU reading: Present', [])])]}