# -*- encoding: utf-8
# yapf: disable


checkname = 'tsm_scratch'


info = [[u'defaultinstance', u'296', u'DD4200.CB'],
        [u'defaultinstance', u'128', u'DD4200.GOLD'],
        [u'ANR2034E',
         u'SELECT:',
         u'No',
         u'match',
         u'found',
         u'using',
         u'this',
         u'criteria.']]


discovery = {'': [(u'defaultinstance / DD4200.CB', 'tsm_scratch_default_levels'),
                  (u'defaultinstance / DD4200.GOLD', 'tsm_scratch_default_levels')]}


checks = {'': [(u'defaultinstance / DD4200.CB',
                (5, 7),
                [(0, 'Found 296 tapes', [('tapes_free', 296, 7, 5, None, None)])]),
               (u'defaultinstance / DD4200.GOLD',
                (5, 7),
                [(0, 'Found 128 tapes', [('tapes_free', 128, 7, 5, None, None)])])]}
